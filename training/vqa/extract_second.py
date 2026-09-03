import os
import sys
import zipfile
import subprocess
import shutil

def extract_second_dataset(
    zip_path: str = "D:\\satquery_data\\second_dataset.zip",
    extract_target: str = "D:\\satquery_data\\SECOND",
    link_target: str = "datasets/cdvqa/SECOND"
):
    print("=" * 60)
    print("EXTRACTING SECOND DATASET FOR CDVQA")
    print("=" * 60)

    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"Source archive not found: {zip_path}")

    os.makedirs(extract_target, exist_ok=True)
    temp_dir = os.path.join(os.path.dirname(zip_path), "temp_extract")
    os.makedirs(temp_dir, exist_ok=True)

    print(f"Opening {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        members = zf.namelist()
        print(f"Archive contents: {members}")
        for member in members:
            if member.endswith('.zip') or member.endswith('.rar'):
                print(f"Extracting inner archive {member} to {temp_dir}...")
                zf.extract(member, temp_dir)

    train_rar = os.path.join(temp_dir, "SECOND_train_set.rar")
    test_zip = os.path.join(temp_dir, "SECOND_total_test.zip")

    # Destination directories
    out_im1 = os.path.join(extract_target, "im1")
    out_im2 = os.path.join(extract_target, "im2")
    os.makedirs(out_im1, exist_ok=True)
    os.makedirs(out_im2, exist_ok=True)

    # 1. Extract SECOND_total_test.zip
    if os.path.exists(test_zip):
        print(f"Extracting {test_zip} using tar/bsdtar...")
        res = subprocess.run(["tar", "-xf", test_zip, "-C", temp_dir], capture_output=True, text=True)
        print("Test extraction result:", res.returncode)
        if res.returncode != 0:
            # Fallback to python zipfile
            print("Fallback to zipfile for test_zip...")
            with zipfile.ZipFile(test_zip, 'r') as tz:
                tz.extractall(temp_dir)

    # 2. Extract SECOND_train_set.rar using bsdtar
    if os.path.exists(train_rar):
        print(f"Extracting {train_rar} using tar/bsdtar...")
        res = subprocess.run(["tar", "-xf", train_rar, "-C", temp_dir], capture_output=True, text=True)
        print("Train extraction result:", res.returncode)

    # 3. Find and gather im1 and im2 files into extract_target/im1 and im2
    print("Consolidating im1 and im2 image files...")
    count_im1 = 0
    count_im2 = 0

    for root, dirs, files in os.walk(temp_dir):
        base = os.path.basename(root).lower()
        if base == "im1":
            for f in files:
                if f.endswith('.png') or f.endswith('.jpg'):
                    src = os.path.join(root, f)
                    dst = os.path.join(out_im1, f)
                    if not os.path.exists(dst):
                        shutil.move(src, dst)
                        count_im1 += 1
        elif base == "im2":
            for f in files:
                if f.endswith('.png') or f.endswith('.jpg'):
                    src = os.path.join(root, f)
                    dst = os.path.join(out_im2, f)
                    if not os.path.exists(dst):
                        shutil.move(src, dst)
                        count_im2 += 1

    print(f"Consolidated images: im1={len(os.listdir(out_im1))}, im2={len(os.listdir(out_im2))}")

    # 4. Clean up temporary archives and temp_dir to save disk space
    print("Cleaning up temporary extraction folders to preserve disk space...")
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        print("Notice:", e)

    # 5. Create symlink / directory junction or link from datasets/cdvqa/SECOND -> D:\satquery_data\SECOND
    link_abs = os.path.abspath(link_target)
    if not os.path.exists(link_abs):
        os.makedirs(os.path.dirname(link_abs), exist_ok=True)
        try:
            print(f"Creating directory junction from {extract_target} to {link_abs}...")
            subprocess.run(["cmd", "/c", "mklink", "/J", link_abs, extract_target], check=True)
            print("Junction created successfully.")
        except Exception as e:
            print(f"Junction failed: {e}. Copying directory structure or using direct path.")

    print("SECOND dataset extraction and preparation completed.")


if __name__ == "__main__":
    extract_second_dataset()
