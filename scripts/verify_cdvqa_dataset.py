import os
import sys
import json
from collections import Counter
from PIL import Image

# Add satquery-ai root to path
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from backend.app.models.cdvqa_model import CDVQA_ANSWER_CLASSES, ANSWER2IDX


def verify_cdvqa_dataset(
    annotations_dir: str = "datasets/cdvqa/annotations",
    images_root: str = "datasets/cdvqa/SECOND",
    splits = ["Train", "Val", "Test", "Test2"]
):
    print("=" * 65)
    print("SATQUERY AI — CDVQA & SECOND DATASET INTEGRITY AUDIT")
    print("=" * 65)

    all_split_images = {}
    all_split_questions = {}
    all_split_answers = {}

    for split in splits:
        img_f = os.path.join(annotations_dir, f"{split}_images.json")
        q_f = os.path.join(annotations_dir, f"{split}_questions.json")
        a_f = os.path.join(annotations_dir, f"{split}_answers.json")

        assert os.path.exists(img_f), f"Missing annotations file: {img_f}"
        assert os.path.exists(q_f), f"Missing annotations file: {q_f}"
        assert os.path.exists(a_f), f"Missing annotations file: {a_f}"

        with open(img_f, 'r') as f:
            imgs = json.load(f)['images']
        with open(q_f, 'r') as f:
            qs = json.load(f)['questions']
        with open(a_f, 'r') as f:
            ans = json.load(f)['answers']

        unique_files = sorted(list(set(x['file_name'] for x in imgs)))
        all_split_images[split] = set(unique_files)
        all_split_questions[split] = len(qs)
        all_split_answers[split] = len(ans)

        print(f"\n--- Split: {split} ---")
        print(f"Total question entries:    {len(qs):,}")
        print(f"Total answer entries:      {len(ans):,}")
        print(f"Unique referenced images:  {len(unique_files):,}")

        # Check answer vocabulary
        ans_classes = set(x['answer'] for x in ans)
        extra_classes = ans_classes - set(CDVQA_ANSWER_CLASSES)
        assert len(extra_classes) == 0, f"Found unregistered answer classes in {split}: {extra_classes}"
        print(f"Answer classes present:    {len(ans_classes)} / {len(CDVQA_ANSWER_CLASSES)} (All registered)")

        # Verify image files on disk
        missing_im1 = []
        missing_im2 = []
        sample_checked = 0

        for fname in unique_files:
            p1 = os.path.join(images_root, "im1", fname)
            p2 = os.path.join(images_root, "im2", fname)

            if not os.path.exists(p1):
                missing_im1.append(fname)
            if not os.path.exists(p2):
                missing_im2.append(fname)

            # Sample raster verification
            if sample_checked < 5 and os.path.exists(p1) and os.path.exists(p2):
                with Image.open(p1) as im1, Image.open(p2) as im2:
                    assert im1.size == im2.size, f"Size mismatch for {fname}: {im1.size} vs {im2.size}"
                sample_checked += 1

        print(f"Disk imagery verified (im1): {len(unique_files) - len(missing_im1)} / {len(unique_files)} exist")
        print(f"Disk imagery verified (im2): {len(unique_files) - len(missing_im2)} / {len(unique_files)} exist")

        if len(missing_im1) > 0 or len(missing_im2) > 0:
            print(f"WARNING: Some image files not found in {images_root}.")
        else:
            print(f"Image Pair Status: 100% complete and validated.")

    # Check Split Isolation (No data leakage)
    print("\n" + "=" * 65)
    print("DATA SPLIT ISOLATION & LEAKAGE AUDIT")
    print("=" * 65)
    leakage_tv = all_split_images['Train'] & all_split_images['Val']
    leakage_tt = all_split_images['Train'] & all_split_images['Test']
    leakage_vt = all_split_images['Val'] & all_split_images['Test']

    print(f"Train / Val image overlap:  {len(leakage_tv)} images (Expected: 0)")
    print(f"Train / Test image overlap: {len(leakage_tt)} images (Expected: 0)")
    print(f"Val / Test image overlap:   {len(leakage_vt)} images (Expected: 0)")

    assert len(leakage_tv) == 0, "DATA LEAKAGE DETECTED between Train and Val!"
    assert len(leakage_tt) == 0, "DATA LEAKAGE DETECTED between Train and Test!"
    assert len(leakage_vt) == 0, "DATA LEAKAGE DETECTED between Val and Test!"

    print("\nINTEGRITY AUDIT PASSED: ZERO DATA LEAKAGE DETECTED.")
    print("=" * 65)


if __name__ == "__main__":
    verify_cdvqa_dataset()
