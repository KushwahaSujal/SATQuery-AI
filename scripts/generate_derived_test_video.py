"""
SatQuery AI — Generate Derived Software Pipeline Test Video
PROVENANCE LABEL: DERIVED_TEST_VIDEO / SYNTHETIC_TEST_VIDEO
Generated from real satellite imagery for automated unit/integration pipeline testing.
NOT labeled as real video footage.
"""
from pathlib import Path
import cv2
import numpy as np
from PIL import Image


def generate_derived_test_video(
    source_image_path: str = "datasets/samples/real_pair/real_image_a.png",
    output_path: str = "datasets/samples/video/derived_patrol.mp4",
    fps: float = 10.0,
    duration_sec: float = 5.0
):
    src_p = Path(source_image_path)
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    if not src_p.exists():
        raise FileNotFoundError(f"Source image not found at {src_p}")

    img = Image.open(src_p).convert("RGB")
    w, h = img.size

    # Crop size
    crop_w, crop_h = 512, 512
    crop_w = min(crop_w, w)
    crop_h = min(crop_h, h)

    total_frames = int(fps * duration_sec)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_p), fourcc, fps, (crop_w, crop_h))

    # Panning across the satellite image with a vehicle region visible in middle frames
    for i in range(total_frames):
        t = i / float(total_frames)
        # Pan coordinates
        x_offset = int((w - crop_w) * t * 0.5) if w > crop_w else 0
        y_offset = int((h - crop_h) * t * 0.5) if h > crop_h else 0

        crop = img.crop((x_offset, y_offset, x_offset + crop_w, y_offset + crop_h))
        frame_bgr = cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2BGR)

        # Draw provenance watermark
        cv2.putText(
            frame_bgr,
            "PROVENANCE: DERIVED_TEST_VIDEO",
            (15, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2,
            cv2.LINE_AA
        )
        writer.write(frame_bgr)

    writer.release()
    print(f"[DERIVED_TEST_VIDEO] Generated {out_p}: {crop_w}x{crop_h}, {fps} fps, {total_frames} frames ({duration_sec}s)")


if __name__ == "__main__":
    generate_derived_test_video()
