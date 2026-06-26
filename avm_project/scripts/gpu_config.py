#!/usr/bin/env python3
"""
Loan4U GPU Configuration - RTX 5050 Targeting
Ensures ML training uses RTX 5050 (8GB GDDR7), not Intel iGPU.
"""

import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


log = logging.getLogger(__name__)


@dataclass
class GPUDevice:
    """Detected GPU device info"""
    index: int
    name: str
    total_memory_mb: int
    is_discrete: bool


def detect_gpus() -> List[GPUDevice]:
    """Detect available GPUs via nvidia-smi (RTX) and report."""
    devices: List[GPUDevice] = []
    try:
        import subprocess
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=index,name,memory.total', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(',')]
            idx, name, mem = int(parts[0]), parts[1], int(parts[2])
            devices.append(GPUDevice(idx, name, mem, is_discrete='RTX' in name or 'GTX' in name))
    except (FileNotFoundError, Exception) as e:
        log.warning(f"nvidia-smi unavailable: {e}")
    return devices


def select_training_device() -> Tuple[Optional[int], str]:
    """Select best GPU for training (prefer RTX discrete with most VRAM)."""
    devices = detect_gpus()
    if not devices:
        return None, "No NVIDIA GPU detected (CPU fallback)"

    discrete = [d for d in devices if d.is_discrete]
    if discrete:
        best = max(discrete, key=lambda d: d.total_memory_mb)
        return best.index, f"{best.name} ({best.total_memory_mb}MB VRAM)"

    best = max(devices, key=lambda d: d.total_memory_mb)
    return best.index, f"{best.name} ({best.total_memory_mb}MB)"


def configure_xgboost_gpu(device_id: int) -> Dict[str, object]:
    """Return XGBoost GPU params targeting RTX 5050."""
    return {
        'tree_method': 'hist',
        'device': f'cuda:{device_id}',
        'max_bin': 256,
    }


def configure_lightgbm_gpu(device_id: int) -> Dict[str, object]:
    """Return LightGBM GPU params targeting RTX 5050."""
    return {
        'device_type': 'gpu',
        'gpu_device_id': device_id,
        'gpu_use_dp': False,
    }


def configure_torch_memory(device_id: int, fraction: float = 0.85) -> bool:
    """Limit PyTorch to fraction of RTX 5050's 8GB (default 85% = ~6.8GB)."""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.set_per_process_memory_fraction(fraction, device_id)
            os.environ['CUDA_VISIBLE_DEVICES'] = str(device_id)
            log.info(f"PyTorch limited to {fraction:.0%} of GPU {device_id}")
            return True
    except (ImportError, Exception) as e:
        log.warning(f"PyTorch GPU config skipped: {e}")
    return False


def print_gpu_report() -> None:
    """Print detected GPUs and recommended training device."""
    devices = detect_gpus()
    print("=" * 50)
    print("GPU Detection Report")
    print("=" * 50)

    if not devices:
        print("⚠ No NVIDIA GPU detected")
        print("  → Intel iGPU is NOT suitable for XGBoost/LightGBM GPU training")
        print("  → CPU fallback will be used")
        return

    for d in devices:
        marker = "✓ DISCRETE" if d.is_discrete else "  integrated"
        print(f"  GPU {d.index}: {d.name} - {d.total_memory_mb}MB [{marker}]")

    device_id, desc = select_training_device()
    print(f"\n→ Selected for training: GPU {device_id} - {desc}")
    print(f"→ XGBoost will use: device='cuda:{device_id}'")
    print(f"→ This avoids the Intel iGPU (2GB shared) entirely")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    print_gpu_report()
