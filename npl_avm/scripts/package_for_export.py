#!/usr/bin/env python3
# coding: utf-8

import os
import sys
import zipfile
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path("D:/NPL전례/avm_project")
EXPORT_DIR = Path("D:/NPL전례")


def create_package(exclude_patterns=None):
    if exclude_patterns is None:
        exclude_patterns = [
            "__pycache__",
            ".pytest_cache",
            ".git",
            "*.pyc",
            "*.log",
            ".env.local",
            "venv",
            "env",
            ".DS_Store",
        ]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = EXPORT_DIR / f"npl_avm_project_{timestamp}.zip"

    print("\n" + "="*70)
    print("NPL AVM Project Packaging")
    print("="*70)

    print(f"\nSource: {PROJECT_ROOT}")
    print(f"Target: {zip_path}")

    if not PROJECT_ROOT.exists():
        print(f"\nERROR: Project path not found: {PROJECT_ROOT}")
        return None

    total_files = 0
    total_size_mb = 0

    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:

            for root, dirs, files in os.walk(PROJECT_ROOT):
                dirs[:] = [d for d in dirs if not any(
                    exc in d for exc in exclude_patterns
                )]

                for file in files:
                    if any(file.endswith(exc.replace('*', '')) for exc in exclude_patterns if '*' in exc):
                        continue

                    file_path = Path(root) / file
                    arcname = file_path.relative_to(PROJECT_ROOT.parent)

                    try:
                        zf.write(file_path, arcname)
                        file_size = file_path.stat().st_size / (1024 * 1024)
                        total_size_mb += file_size
                        total_files += 1

                        if file.endswith(('.db', '.sqlite')):
                            print(f"  [DB] {file} ({file_size:.2f} MB)")
                        elif file.endswith('.py') and 'scripts' in str(file_path):
                            print(f"  [SCRIPT] {file}")

                    except Exception as e:
                        print(f"  WARNING: {file} skipped - {e}")

        zip_size_mb = zip_path.stat().st_size / (1024 * 1024)

        print(f"\n{'='*70}")
        print("Completed!")
        print(f"{'='*70}")
        print(f"\nZip file: {zip_path.name}")
        print(f"Total files: {total_files:,}")
        print(f"Original size: {total_size_mb:.2f} MB")
        print(f"Compressed size: {zip_size_mb:.2f} MB")
        print(f"Compression ratio: {(1 - zip_size_mb/total_size_mb)*100:.1f}%")

        print(f"\nDownload path:")
        print(f"  {zip_path}")

        return zip_path

    except Exception as e:
        print(f"\nERROR: Packaging failed - {e}")
        import traceback
        traceback.print_exc()
        return None


def list_contents(zip_path):
    print(f"\n{'='*70}")
    print("Package Contents (Top 30)")
    print(f"{'='*70}\n")

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            files = zf.namelist()

            for f in files[:30]:
                size_kb = zf.getinfo(f).file_size / 1024
                marker = "[DIR]" if f.endswith('/') else "[FILE]"
                print(f"{marker} {f:60} {size_kb:>10.1f} KB")

            if len(files) > 30:
                print(f"\n... Plus {len(files)-30} more files")

    except Exception as e:
        print(f"ERROR: {e}")


def main():
    zip_path = create_package()

    if zip_path:
        list_contents(zip_path)

        print(f"\n{'='*70}")
        print("Usage Scenarios")
        print(f"{'='*70}")
        print("""
1. Local Development
   - Download and extract zip file
   - python -m pip install -r requirements.txt
   - python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

2. Cloud Deployment (AWS/GCP/Azure)
   - Upload and extract
   - Build Docker image
   - Migrate database to PostgreSQL

3. Team Sharing
   - Upload to Codex or collaboration platform
   - Share project snapshot across team
        """)

        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
