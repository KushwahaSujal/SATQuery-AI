"""Download Qwen3-VL-4B-Instruct, quantize to 4-bit NF4 and save it pre-quantized (Q-021). Needs a CUDA GPU."""
import argparse
import subprocess
from pathlib import Path

import torch
from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig

ap = argparse.ArgumentParser()
ap.add_argument("--model-id", default="Qwen/Qwen3-VL-4B-Instruct")
ap.add_argument("--out", default="checkpoints/scene_vlm_qwen3vl4b_nf4")
args = ap.parse_args()

quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16,
                           bnb_4bit_use_double_quant=True)
model = AutoModelForImageTextToText.from_pretrained(args.model_id, quantization_config=quant, device_map={"": 0},
                                                    dtype=torch.float16)
AutoProcessor.from_pretrained(args.model_id).save_pretrained(args.out)
model.save_pretrained(args.out)
print(subprocess.run(["du", "-sh", args.out], capture_output=True, text=True).stdout.strip())
