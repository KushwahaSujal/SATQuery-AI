import os
import sys
import time
import json
import torch
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt

# Add satquery-ai root to path
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from backend.app.models.cdvqa import CDVQAAdapter
from backend.app.schemas.models import ModelResult


def run_cdvqa_smoke_test(
    checkpoint_path: str = "checkpoints/cdvqa/cdvqa_satquery.pt",
    image1_path: str = "datasets/samples/real_pair/real_image_a.png",
    image2_path: str = "datasets/samples/real_pair/real_image_b.png",
    question: str = "What changed between these two images?",
    output_json: str = "results/cdvqa_smoke_test.json",
    output_png: str = "results/cdvqa_smoke_test.png"
):
    print("=" * 60)
    print("SATQUERY AI — CDVQA REAL SMOKE TEST")
    print("=" * 60)

    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"CDVQA checkpoint not found at {checkpoint_path}")
    if not os.path.exists(image1_path):
        raise FileNotFoundError(f"Image 1 not found at {image1_path}")
    if not os.path.exists(image2_path):
        raise FileNotFoundError(f"Image 2 not found at {image2_path}")

    # 1. Load Images
    img1 = Image.open(image1_path).convert("RGB")
    img2 = Image.open(image2_path).convert("RGB")
    print(f"Loaded Image 1: {img1.size} from {image1_path}")
    print(f"Loaded Image 2: {img2.size} from {image2_path}")
    print(f"Question: '{question}'")

    # 2. Instantiate and Load Adapter
    adapter = CDVQAAdapter(checkpoint_path=checkpoint_path)
    adapter.load_model()
    print("CDVQAAdapter successfully initialized and model loaded.")

    # 3. Run Inference
    t0 = time.time()
    result: ModelResult = adapter.predict({
        "image1": img1,
        "image2": img2,
        "query": question
    })
    inference_time_ms = (time.time() - t0) * 1000.0

    # 4. Print and Validate Output
    print("-" * 60)
    print(f"Model Name:       {result.model_name}")
    print(f"Task:             {result.task}")
    print(f"Predicted Answer: {result.answer}")
    print(f"Confidence:       {result.confidence:.4f}" if result.confidence is not None else "Confidence:       None")
    print(f"Inference Time:   {inference_time_ms:.2f} ms")
    print("-" * 60)

    assert result.answer is not None and len(result.answer) > 0, "Predicted answer must be non-empty"
    assert result.task == "change_vqa", "Task must be 'change_vqa'"

    # 5. Save Results JSON
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    smoke_record = {
        "status": "SUCCESS",
        "model_name": result.model_name,
        "checkpoint_path": checkpoint_path,
        "task": result.task,
        "question": question,
        "answer": result.answer,
        "confidence": result.confidence,
        "inference_time_ms": inference_time_ms,
        "metadata": result.metadata,
        "image1_size": list(img1.size),
        "image2_size": list(img2.size),
        "timestamp": time.time()
    }
    with open(output_json, "w") as f:
        json.dump(smoke_record, f, indent=2)
    print(f"Smoke test JSON result saved to: {output_json}")

    # 6. Save Visual Explanation Plot
    os.makedirs(os.path.dirname(output_png), exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes[0].imshow(img1)
    axes[0].set_title("Pre-Change (T1)")
    axes[0].axis("off")

    axes[1].imshow(img2)
    axes[1].set_title("Post-Change (T2)")
    axes[1].axis("off")

    change_map = result.metadata.get("change_map")
    if change_map is not None and isinstance(change_map, list):
        cmap_arr = np.array(change_map)
        im = axes[2].imshow(cmap_arr, cmap="hot")
        axes[2].set_title(f"CEM Change Map\nAns: {result.answer} ({result.confidence*100:.1f}%)")
        plt.colorbar(im, ax=axes[2])
    else:
        # Diff preview
        diff = np.abs(np.array(img1, dtype=float) - np.array(img2, dtype=float)).mean(axis=-1)
        axes[2].imshow(diff, cmap="magma")
        axes[2].set_title(f"Visual Diff\nAns: {result.answer}")
    axes[2].axis("off")

    plt.suptitle(f"CDVQA: \"{question}\" -> \"{result.answer}\"", fontsize=13, weight="bold")
    plt.tight_layout()
    plt.savefig(output_png, dpi=150)
    plt.close()
    print(f"Visual explanation saved to: {output_png}")
    print("CDVQA SMOKE TEST PASSED SUCCESSFULLY.")


if __name__ == "__main__":
    run_cdvqa_smoke_test()
