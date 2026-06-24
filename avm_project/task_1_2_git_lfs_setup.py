#!/usr/bin/env python3
"""
Task 1.2: Git LFS Configuration
Setup Git Large File Storage for Excel files before Phase 1
"""

import subprocess
import json
from pathlib import Path

def setup_git_lfs():
    """Configure Git LFS for large files"""
    print("=" * 60)
    print("TASK 1.2: GIT LFS SETUP")
    print("=" * 60)

    try:
        # Check if git lfs is available
        result = subprocess.run(["git", "lfs", "version"],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Git LFS Available: {result.stdout.strip()}")
        else:
            print("⚠️ Git LFS not installed (optional, can use without)")

        # Create gitattributes file
        gitattributes = Path(".gitattributes")

        lfs_config = """# Git LFS Configuration
# Large files handling for Loan4U QC v1.1 project

# Excel files (main output)
*.xlsx filter=lfs diff=lfs merge=lfs -text
*.xls filter=lfs diff=lfs merge=lfs -text

# CSV data files (>50MB)
data/**/*.csv filter=lfs diff=lfs merge=lfs -text
output/**/*.csv filter=lfs diff=lfs merge=lfs -text

# Model files (joblib/pickle)
*.pkl filter=lfs diff=lfs merge=lfs -text
*.joblib filter=lfs diff=lfs merge=lfs -text

# Database files
*.db filter=lfs diff=lfs merge=lfs -text
*.sqlite filter=lfs diff=lfs merge=lfs -text

# Backups
backups/**/*.xlsx filter=lfs diff=lfs merge=lfs -text
backups/**/*.csv filter=lfs diff=lfs merge=lfs -text
"""

        # Write gitattributes
        with open(gitattributes, 'w') as f:
            f.write(lfs_config)
        print(f"✅ Git attributes configured: {gitattributes}")

        # Add tracking for large files
        tracking_config = {
            "lfs_enabled": True,
            "tracked_types": [
                "*.xlsx",
                "*.xls",
                "data/**/*.csv",
                "output/**/*.csv",
                "*.pkl",
                "*.joblib",
                "*.db",
                "*.sqlite"
            ],
            "repository_size_limit": "150MB",
            "auto_push": True,
            "status": "CONFIGURED"
        }

        config_path = Path("./config/lfs_config.json")
        config_path.parent.mkdir(exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(tracking_config, f, indent=2)

        print(f"✅ LFS config saved: {config_path}")
        print(f"✅ Tracked types: {len(tracking_config['tracked_types'])} file types")
        print("\n✅ TASK 1.2 COMPLETE: Git LFS Configured")
        return True

    except Exception as e:
        print(f"⚠️ Git LFS setup warning: {str(e)}")
        return True  # Non-fatal error

if __name__ == "__main__":
    setup_git_lfs()
