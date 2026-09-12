import re
from typing import Dict, List, Optional
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models


CDVQA_ANSWER_CLASSES: List[str] = [
    "no",
    "yes",
    "NVG_surface",
    "0",
    "0_to_10",
    "buildings",
    "low_vegetation",
    "trees",
    "10_to_20",
    "water",
    "80_to_90",
    "20_to_30",
    "90_to_100",
    "70_to_80",
    "30_to_40",
    "60_to_70",
    "40_to_50",
    "playgrounds",
    "50_to_60"
]

ANSWER2IDX: Dict[str, int] = {ans: idx for idx, ans in enumerate(CDVQA_ANSWER_CLASSES)}
IDX2ANSWER: Dict[int, str] = {idx: ans for idx, ans in enumerate(CDVQA_ANSWER_CLASSES)}

VOCAB_WORDS = [
    '<PAD>', '<UNK>',
    'area', 'areas', 'buildings', 'change', 'changed', 'decrease', 'decreased',
    'did', 'event', 'first', 'ground', 'has', 'have', 'how', 'image', 'imagery',
    'in', 'increase', 'increased', 'is', 'largest', 'low', 'mainly', 'much',
    'non', 'not', 'of', 'percentage', 'playgrounds', 'post', 'pre', 'proportion',
    'ratio', 'regions', 'second', 'smallest', 'surface', 'the', 'to', 'trees',
    'type', 'unchanged', 'vegetated', 'vegetation', 'water', 'what'
]

WORD2IDX: Dict[str, int] = {w: i for i, w in enumerate(VOCAB_WORDS)}


def tokenize_question(question_text: str, max_len: int = 24) -> torch.Tensor:
    """Tokenize a CDVQA natural language question into sequence of word IDs."""
    words = re.findall(r'\w+', question_text.lower())
    ids = [WORD2IDX.get(w, 1) for w in words][:max_len]
    if len(ids) < max_len:
        ids += [0] * (max_len - len(ids))
    return torch.tensor(ids, dtype=torch.long)


class ChangeEnhancingModule(nn.Module):
    """
    Change Enhancing Module (CEM) from Yuan et al. (IEEE TGRS 2022).
    Uses cross-attention between pre-change F1 (query) and post-change F2 (key)
    to predict a spatial change enhancing map M_ce, scaled by learnable theta.
    """
    def __init__(self, channels: int = 512):
        super().__init__()
        self.fq = nn.Conv2d(channels, channels, kernel_size=1, bias=False)
        self.fk = nn.Conv2d(channels, channels, kernel_size=1, bias=False)
        self.fc = nn.Conv2d(channels, 1, kernel_size=1, bias=True)
        self.theta = nn.Parameter(torch.zeros(1))

    def forward(self, f1: torch.Tensor, f2: torch.Tensor):
        q = self.fq(f1)
        k = self.fk(f2)
        fs = q * k
        mce = F.relu(self.fc(fs))
        weight = 1.0 + self.theta * mce
        fc1 = weight * f1
        fc2 = weight * f2
        return fc1, fc2, mce


class TextQuestionEncoder(nn.Module):
    """
    Official CDVQA Question Encoder (Yuan et al., IEEE TGRS 2022).
    - Architecture: Word Embedding (embed_dim=512) -> Recurrent GRU (hidden_size=512)
    - Embedding Dimension L: 512
    - Output: Final GRU hidden state V_q in R^(B x 512)
    - Tokenizer / Vocabulary: Closed 46-word CDVQA vocabulary + PAD (0) + UNK (1) = 48 tokens
    - Sequence Handling: Tokenized with r'\\w+', max_len=24, zero-padded
    """
    def __init__(
        self,
        vocab_size: int = len(VOCAB_WORDS),
        embed_dim: int = 512,
        hidden_dim: int = 512,
        output_dim: int = 512
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.gru = nn.GRU(embed_dim, hidden_dim, batch_first=True)
        if hidden_dim != output_dim:
            self.proj = nn.Linear(hidden_dim, output_dim)
        else:
            self.proj = nn.Identity()

    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        # input_ids: (B, seq_len)
        embeds = self.embedding(input_ids)  # (B, seq_len, embed_dim)
        _, h_n = self.gru(embeds)  # h_n: (1, B, hidden_dim)
        h = h_n.squeeze(0)  # (B, hidden_dim)
        out = self.proj(h)  # (B, output_dim)
        return out


class CDVQAModel(nn.Module):
    """
    Official Siamese ResNet-18 + Change Enhancing Module (CEM) architecture
    for Change Detection Meets Visual Question Answering (CDVQA).
    """
    def __init__(
        self,
        num_classes: int = 19,
        vocab_size: int = len(VOCAB_WORDS),
        feature_dim: int = 512,
        freeze_backbone: bool = True,
        pretrained: bool = True
    ):
        super().__init__()
        self.num_classes = num_classes
        self.feature_dim = feature_dim

        # 1. Shared Siamese ResNet-18 visual encoder
        weights = models.ResNet18_Weights.DEFAULT if pretrained else None
        resnet = models.resnet18(weights=weights)
        self.backbone = nn.Sequential(
            resnet.conv1,
            resnet.bn1,
            resnet.relu,
            resnet.maxpool,
            resnet.layer1,
            resnet.layer2,
            resnet.layer3,
            resnet.layer4
        )
        if freeze_backbone:
            for p in self.backbone.parameters():
                p.requires_grad = False

        # 2. Change Enhancing Module (CEM)
        self.cem = ChangeEnhancingModule(channels=512)

        # 3. Multi-temporal Fusion
        self.temporal_pool = nn.AdaptiveAvgPool2d((1, 1))
        self.visual_proj = nn.Linear(512 * 2, feature_dim)

        # 4. Question Encoder (embed_dim=512, hidden_dim=512, L=512)
        self.question_encoder = TextQuestionEncoder(
            vocab_size=vocab_size,
            embed_dim=feature_dim,
            hidden_dim=feature_dim,
            output_dim=feature_dim
        )

        # 5. Classifier (2L -> 256 -> num_classes)
        self.classifier = nn.Sequential(
            nn.Linear(feature_dim * 2, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.5),
            nn.Linear(256, num_classes)
        )

    def forward_features(
        self,
        f1: torch.Tensor,
        f2: torch.Tensor,
        question_tokens: torch.Tensor
    ) -> Dict[str, torch.Tensor]:
        fc1, fc2, mce = self.cem(f1, f2)
        fv = torch.cat([fc1, fc2], dim=1)
        fv_pooled = self.temporal_pool(fv).flatten(1)
        fvt = F.relu(self.visual_proj(fv_pooled))
        vq = self.question_encoder(question_tokens)
        fm = torch.cat([fvt, vq], dim=1)
        logits = self.classifier(fm)
        return {
            "logits": logits,
            "change_map": mce
        }

    def forward(
        self,
        img1: torch.Tensor,
        img2: torch.Tensor,
        question_tokens: torch.Tensor
    ) -> Dict[str, torch.Tensor]:
        f1 = self.backbone(img1)
        f2 = self.backbone(img2)
        return self.forward_features(f1, f2, question_tokens)
