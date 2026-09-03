import os
import sys
import time
import json
import argparse
from collections import defaultdict
from typing import Dict, Any, List

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import torchvision.transforms as T

# Add satquery-ai root to path
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from backend.app.models.cdvqa_model import (
    CDVQAModel,
    CDVQA_ANSWER_CLASSES,
    IDX2ANSWER,
    WORD2IDX,
    tokenize_question
)
from training.vqa.dataset import CDVQADataset


class CachedCDVQADataset(Dataset):
    """
    In-memory cached dataset leveraging precomputed ResNet-18 visual representations
    for the frozen visual backbone, dramatically accelerating CPU training while
    maintaining mathematical equivalence to full forward passes.
    """
    def __init__(self, raw_dataset: CDVQADataset, feature_cache: Dict[str, tuple]):
        self.samples = raw_dataset.samples
        self.feature_cache = feature_cache

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> dict:
        item = self.samples[idx]
        f1, f2 = self.feature_cache[item['file_name']]
        q_tokens = tokenize_question(item['question'])

        return {
            'f1': f1,
            'f2': f2,
            'question_tokens': q_tokens,
            'label': torch.tensor(item['label'], dtype=torch.long),
            'question_type': item['question_type']
        }


def extract_features_for_unique_images(
    dataset: CDVQADataset,
    backbone: nn.Module,
    device: torch.device,
    desc: str = "Train"
) -> Dict[str, tuple]:
    print(f"[{desc}] Pre-extracting frozen ResNet-18 features for unique image pairs...")
    unique_files = sorted(list(set(s['file_name'] for s in dataset.samples)))
    print(f"[{desc}] Unique image pairs to extract: {len(unique_files):,}")

    transform = T.Compose([
        T.Resize((256, 256)),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    cache = {}
    t0 = time.time()

    backbone.eval()
    with torch.no_grad():
        for idx, fname in enumerate(unique_files):
            p1, p2 = dataset._resolve_image_paths(fname)
            im1 = Image.open(p1).convert('RGB')
            im2 = Image.open(p2).convert('RGB')

            t1 = transform(im1).unsqueeze(0).to(device)
            t2 = transform(im2).unsqueeze(0).to(device)

            feat1 = backbone(t1).squeeze(0).cpu()  # (512, 8, 8)
            feat2 = backbone(t2).squeeze(0).cpu()  # (512, 8, 8)

            cache[fname] = (feat1, feat2)

            if (idx + 1) % 200 == 0 or (idx + 1) == len(unique_files):
                pct = ((idx + 1) / len(unique_files)) * 100
                dt = time.time() - t0
                print(f"[{desc}] Feature extraction: {idx+1}/{len(unique_files)} ({pct:.1f}%) in {dt:.1f}s", flush=True)

    print(f"[{desc}] Feature cache ready with {len(cache):,} items in {time.time()-t0:.1f}s.")
    return cache


def evaluate_cached(
    model: CDVQAModel,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device
) -> Dict[str, Any]:
    model.eval()
    total_loss = 0.0
    total_samples = 0
    correct_samples = 0

    type_total = defaultdict(int)
    type_correct = defaultdict(int)

    with torch.no_grad():
        for batch in dataloader:
            f1 = batch['f1'].to(device)
            f2 = batch['f2'].to(device)
            q_tokens = batch['question_tokens'].to(device)
            labels = batch['label'].to(device)
            q_types = batch['question_type']

            outputs = model.forward_features(f1, f2, q_tokens)
            logits = outputs['logits']
            loss = criterion(logits, labels)

            preds = torch.argmax(logits, dim=-1)
            batch_size = labels.size(0)

            total_loss += loss.item() * batch_size
            total_samples += batch_size
            correct = (preds == labels).sum().item()
            correct_samples += correct

            for t, p, l in zip(q_types, preds.cpu().tolist(), labels.cpu().tolist()):
                type_total[t] += 1
                if p == l:
                    type_correct[t] += 1

    avg_loss = total_loss / total_samples if total_samples > 0 else 0.0
    overall_acc = correct_samples / total_samples if total_samples > 0 else 0.0

    type_accuracies = {}
    for t in type_total:
        type_accuracies[t] = type_correct[t] / type_total[t] if type_total[t] > 0 else 0.0

    avg_acc = sum(type_accuracies.values()) / len(type_accuracies) if type_accuracies else 0.0

    return {
        'loss': avg_loss,
        'overall_accuracy': overall_acc,
        'average_accuracy': avg_acc,
        'type_accuracies': type_accuracies,
        'total_evaluated': total_samples
    }


def train_cdvqa(args: argparse.Namespace):
    device = torch.device('cuda' if torch.cuda.is_available() and not args.cpu else 'cpu')
    print(f"[CDVQA Training] Using device: {device}")

    os.makedirs(os.path.dirname(args.save_path), exist_ok=True)
    os.makedirs(os.path.dirname(args.metrics_path), exist_ok=True)

    # 1. Datasets
    print("[CDVQA Training] Loading official Train and Val annotations...")
    train_raw = CDVQADataset(
        annotations_dir=args.annotations_dir,
        split='Train',
        images_root=args.images_root,
        max_samples=args.max_train_samples
    )
    val_raw = CDVQADataset(
        annotations_dir=args.annotations_dir,
        split='Val',
        images_root=args.images_root,
        max_samples=args.max_val_samples
    )

    print(f"[CDVQA Training] Train dataset: {len(train_raw):,} question-answer samples")
    print(f"[CDVQA Training] Val dataset:   {len(val_raw):,} question-answer samples")

    # 2. Build CDVQAModel
    print("[CDVQA Training] Instantiating official Siamese ResNet-18 + CEM Model...")
    model = CDVQAModel(
        num_classes=len(CDVQA_ANSWER_CLASSES),
        vocab_size=len(WORD2IDX),
        feature_dim=512,
        freeze_backbone=True,
        pretrained=True
    ).to(device)

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"[CDVQA Training] Trainable parameters: {trainable_params:,} / {total_params:,}")

    # 3. Pre-extract features for unique images using the frozen backbone
    train_cache = extract_features_for_unique_images(train_raw, model.backbone, device, "Train")
    val_cache = extract_features_for_unique_images(val_raw, model.backbone, device, "Val")

    train_cached_ds = CachedCDVQADataset(train_raw, train_cache)
    val_cached_ds = CachedCDVQADataset(val_raw, val_cache)

    train_loader = DataLoader(train_cached_ds, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_cached_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    # 4. Optimizer, Scheduler, Loss
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=args.lr,
        weight_decay=1e-4
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    # 5. Training Loop
    best_val_acc = 0.0
    best_epoch = 0
    history = []
    start_time = time.time()

    print(f"\n[CDVQA Training] Starting training for {args.epochs} epochs (Batch Size={args.batch_size}, LR={args.lr})...\n")

    for epoch in range(1, args.epochs + 1):
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        epoch_t0 = time.time()

        for step, batch in enumerate(train_loader):
            f1 = batch['f1'].to(device)
            f2 = batch['f2'].to(device)
            q_tokens = batch['question_tokens'].to(device)
            labels = batch['label'].to(device)

            optimizer.zero_grad()
            outputs = model.forward_features(f1, f2, q_tokens)
            logits = outputs['logits']
            loss = criterion(logits, labels)

            loss.backward()
            optimizer.step()

            batch_size = labels.size(0)
            train_loss += loss.item() * batch_size
            train_total += batch_size
            preds = torch.argmax(logits, dim=-1)
            train_correct += (preds == labels).sum().item()

            if (step + 1) % args.log_interval == 0 or (step + 1) == len(train_loader):
                curr_loss = train_loss / train_total
                curr_acc = train_correct / train_total
                print(f"Epoch [{epoch:02d}/{args.epochs:02d}] Step [{step+1:04d}/{len(train_loader):04d}] "
                      f"Loss: {curr_loss:.4f} Acc: {curr_acc*100:.2f}%", flush=True)

        scheduler.step()
        epoch_duration = time.time() - epoch_t0

        # Validate on official Val split
        val_metrics = evaluate_cached(model, val_loader, criterion, device)
        val_loss = val_metrics['loss']
        val_oa = val_metrics['overall_accuracy']
        val_aa = val_metrics['average_accuracy']

        print(f"--> Epoch {epoch:02d} Results: Val Loss: {val_loss:.4f} | Val OA: {val_oa*100:.2f}% | "
              f"Val AA: {val_aa*100:.2f}% | Epoch Time: {epoch_duration:.1f}s", flush=True)

        epoch_record = {
            'epoch': epoch,
            'train_loss': train_loss / train_total if train_total > 0 else 0.0,
            'train_accuracy': train_correct / train_total if train_total > 0 else 0.0,
            'val_loss': val_loss,
            'val_overall_accuracy': val_oa,
            'val_average_accuracy': val_aa,
            'val_type_accuracies': val_metrics['type_accuracies'],
            'lr': optimizer.param_groups[0]['lr'],
            'duration_seconds': epoch_duration
        }
        history.append(epoch_record)

        # Checkpoint selection strictly on validation accuracy
        if val_oa > best_val_acc:
            best_val_acc = val_oa
            best_epoch = epoch
            print(f"*** Saving new best model to {args.save_path} (Val OA: {val_oa*100:.2f}%) ***", flush=True)
            checkpoint_payload = {
                'epoch': epoch,
                'state_dict': model.state_dict(),
                'val_overall_accuracy': val_oa,
                'val_average_accuracy': val_aa,
                'classes': CDVQA_ANSWER_CLASSES,
                'word2idx': WORD2IDX,
                'feature_dim': 512,
                'architecture': 'Siamese_ResNet18_CEM'
            }
            torch.save(checkpoint_payload, args.save_path)

    total_duration = time.time() - start_time
    print(f"\n[CDVQA Training Complete] Best Val OA: {best_val_acc*100:.2f}% achieved at Epoch {best_epoch}. "
          f"Total training duration: {total_duration/60:.2f} mins.")

    # Save training metrics
    metrics_payload = {
        'training_completed': True,
        'total_duration_seconds': total_duration,
        'best_epoch': best_epoch,
        'best_val_overall_accuracy': best_val_acc,
        'history': history
    }
    with open(args.metrics_path, 'w') as f:
        json.dump(metrics_payload, f, indent=2)
    print(f"Training metrics saved to: {args.metrics_path}")

    # Save config
    config_payload = vars(args)
    config_path = os.path.join(os.path.dirname(args.metrics_path), "cdvqa_training_config.json")
    with open(config_path, 'w') as f:
        json.dump(config_payload, f, indent=2)
    print(f"Training config saved to: {config_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Official CDVQA Siamese ResNet-18 + CEM Baseline")
    parser.add_argument("--annotations_dir", type=str, default="datasets/cdvqa/annotations")
    parser.add_argument("--images_root", type=str, default="datasets/cdvqa/SECOND")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch_size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--save_path", type=str, default="checkpoints/cdvqa/cdvqa_satquery.pt")
    parser.add_argument("--metrics_path", type=str, default="results/cdvqa_training_metrics.json")
    parser.add_argument("--max_train_samples", type=int, default=None)
    parser.add_argument("--max_val_samples", type=int, default=None)
    parser.add_argument("--log_interval", type=int, default=100)
    parser.add_argument("--cpu", action="store_true", default=False)
    args = parser.parse_args()
    train_cdvqa(args)
