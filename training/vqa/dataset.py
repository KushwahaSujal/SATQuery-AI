import os
import json
import re
from typing import Dict, List, Tuple, Optional
import torch
from torch.utils.data import Dataset
from PIL import Image
import torchvision.transforms as T
from training.vqa.model import CDVQA_ANSWER_CLASSES, ANSWER2IDX


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
    """Tokenize a CDVQA question into sequence of word IDs."""
    words = re.findall(r'\w+', question_text.lower())
    ids = [WORD2IDX.get(w, 1) for w in words][:max_len]
    if len(ids) < max_len:
        ids += [0] * (max_len - len(ids))
    return torch.tensor(ids, dtype=torch.long)


class CDVQADataset(Dataset):
    """
    Official CDVQA Dataset loader for paired bi-temporal aerial imagery.
    """
    def __init__(
        self,
        annotations_dir: str,
        split: str,  # 'Train', 'Val', 'Test', 'Test2'
        images_root: str,
        transform: Optional[T.Compose] = None,
        max_samples: Optional[int] = None
    ):
        super().__init__()
        self.split = split
        self.images_root = images_root

        if transform is None:
            self.transform = T.Compose([
                T.Resize((256, 256)),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
        else:
            self.transform = transform

        # Load official annotations
        images_file = os.path.join(annotations_dir, f"{split}_images.json")
        questions_file = os.path.join(annotations_dir, f"{split}_questions.json")
        answers_file = os.path.join(annotations_dir, f"{split}_answers.json")

        with open(images_file, 'r') as f:
            imgs_data = json.load(f)
        with open(questions_file, 'r') as f:
            qs_data = json.load(f)
        with open(answers_file, 'r') as f:
            ans_data = json.load(f)

        # Image id to filename
        self.img_id_to_file: Dict[int, str] = {}
        for img in imgs_data['images']:
            self.img_id_to_file[img['id']] = img['file_name']

        # Question id to question item
        self.questions: Dict[int, dict] = {}
        for q in qs_data['questions']:
            self.questions[q['id']] = q

        # Answer list
        raw_answers = ans_data['answers']
        if max_samples is not None:
            raw_answers = raw_answers[:max_samples]

        self.samples: List[dict] = []
        for ans in raw_answers:
            qid = ans['question_id']
            if qid in self.questions:
                q_item = self.questions[qid]
                img_id = q_item['img_id']
                file_name = self.img_id_to_file.get(img_id)
                if file_name and ans['answer'] in ANSWER2IDX:
                    self.samples.append({
                        'answer_id': ans['id'],
                        'question_id': qid,
                        'question': q_item['question'],
                        'question_type': q_item['type'],
                        'answer': ans['answer'],
                        'label': ANSWER2IDX[ans['answer']],
                        'file_name': file_name
                    })

    def __len__(self) -> int:
        return len(self.samples)

    def _resolve_image_paths(self, file_name: str) -> Tuple[str, str]:
        # Search possible image locations in images_root:
        # e.g. images_root/im1/02180.png and images_root/im2/02180.png
        # or images_root/SECOND_train_set/im1/02180.png
        possible_pairs = [
            (os.path.join(self.images_root, 'im1', file_name), os.path.join(self.images_root, 'im2', file_name)),
            (os.path.join(self.images_root, 'train', 'im1', file_name), os.path.join(self.images_root, 'train', 'im2', file_name)),
            (os.path.join(self.images_root, 'test', 'im1', file_name), os.path.join(self.images_root, 'test', 'im2', file_name)),
            (os.path.join(self.images_root, 'SECOND_train_set', 'im1', file_name), os.path.join(self.images_root, 'SECOND_train_set', 'im2', file_name)),
            (os.path.join(self.images_root, 'SECOND_total_test', 'im1', file_name), os.path.join(self.images_root, 'SECOND_total_test', 'im2', file_name)),
        ]
        for p1, p2 in possible_pairs:
            if os.path.exists(p1) and os.path.exists(p2):
                return p1, p2
        # Default fallback
        return os.path.join(self.images_root, 'im1', file_name), os.path.join(self.images_root, 'im2', file_name)

    def __getitem__(self, idx: int) -> dict:
        item = self.samples[idx]
        p1, p2 = self._resolve_image_paths(item['file_name'])

        try:
            img1 = Image.open(p1).convert('RGB')
            img2 = Image.open(p2).convert('RGB')
        except Exception:
            # Blank RGB fallback if file temporarily missing
            img1 = Image.new('RGB', (256, 256), color=(128, 128, 128))
            img2 = Image.new('RGB', (256, 256), color=(128, 128, 128))

        t1 = self.transform(img1)
        t2 = self.transform(img2)
        q_tokens = tokenize_question(item['question'])

        return {
            'img1': t1,
            'img2': t2,
            'question_tokens': q_tokens,
            'label': torch.tensor(item['label'], dtype=torch.long),
            'question_type': item['question_type'],
            'question_text': item['question'],
            'answer_text': item['answer'],
            'file_name': item['file_name']
        }
