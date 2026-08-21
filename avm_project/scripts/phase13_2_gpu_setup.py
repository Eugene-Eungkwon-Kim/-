"""Phase 13.2.1 - GPU 환경 설정 검증 및 벤치마크

RTX 5050 GPU 환경 확인, XGBoost/LightGBM GPU 활성화 검증,
성능 벤치마크 수행 (CPU vs GPU).

실행:
    python scripts/phase13_2_gpu_setup.py --benchmark --report
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

import numpy as np
import torch

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

import logging

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')


def check_cuda() -> Dict[str, bool]:
    """CUDA 환경 검증."""
    return {
        'torch_cuda_available': torch.cuda.is_available(),
        'device_count': torch.cuda.device_count() if torch.cuda.is_available() else 0,
        'cuda_version': torch.version.cuda if hasattr(torch.version, 'cuda') else None,
    }


def check_gpu_device() -> Dict[str, str]:
    """GPU 장치 정보 확인."""
    if not torch.cuda.is_available():
        return {'status': 'not_available'}

    device_name = torch.cuda.get_device_name(0)
    device_props = torch.cuda.get_device_properties(0)

    return {
        'device_name': device_name,
        'device_id': 0,
        'compute_capability': f"{device_props.major}.{device_props.minor}",
        'total_memory_gb': device_props.total_memory / 1e9,
        'is_rtx_5050': 'RTX 5050' in device_name or '5050' in device_name,
    }


def check_xgboost_gpu() -> Dict[str, bool]:
    """XGBoost GPU 지원 확인."""
    if not XGBOOST_AVAILABLE:
        return {'available': False, 'reason': 'xgboost not installed'}

    try:
        # tree_method='gpu_hist' 테스트
        model = xgb.XGBRegressor(tree_method='gpu_hist', n_estimators=1, gpu_id=0)
        X = np.random.randn(10, 5).astype(np.float32)
        y = np.random.randn(10).astype(np.float32)
        model.fit(X, y, verbose=0)
        return {
            'available': True,
            'tree_method_gpu_hist': True,
            'version': xgb.__version__,
        }
    except Exception as e:
        return {
            'available': False,
            'reason': str(e),
            'version': xgb.__version__ if XGBOOST_AVAILABLE else None,
        }


def check_lightgbm_gpu() -> Dict[str, bool]:
    """LightGBM GPU 지원 확인."""
    if not LIGHTGBM_AVAILABLE:
        return {'available': False, 'reason': 'lightgbm not installed'}

    try:
        # device_type='gpu' 테스트
        model = lgb.LGBMRegressor(device_type='gpu', n_estimators=1)
        X = np.random.randn(10, 5).astype(np.float32)
        y = np.random.randn(10).astype(np.float32)
        model.fit(X, y, verbose=0)
        return {
            'available': True,
            'device_type_gpu': True,
            'version': lgb.__version__,
        }
    except Exception as e:
        return {
            'available': False,
            'reason': str(e),
            'version': lgb.__version__ if LIGHTGBM_AVAILABLE else None,
        }


def benchmark_xgboost_cpu_vs_gpu(
    n_rows: int = 1000,
    n_features: int = 5,
    n_runs: int = 3,
) -> Dict[str, float]:
    """XGBoost CPU vs GPU 성능 비교."""
    if not XGBOOST_AVAILABLE:
        return {'status': 'xgboost_not_available'}

    X = np.random.randn(n_rows, n_features).astype(np.float32)
    y = np.random.randn(n_rows).astype(np.float32)

    # CPU 벤치마크
    cpu_times = []
    for _ in range(n_runs):
        model = xgb.XGBRegressor(tree_method='hist', n_estimators=100, gpu_id=-1)
        start = time.time()
        model.fit(X, y, verbose=0)
        cpu_times.append(time.time() - start)

    # GPU 벤치마크 (사용 가능한 경우)
    gpu_times = []
    try:
        for _ in range(n_runs):
            model = xgb.XGBRegressor(tree_method='gpu_hist', n_estimators=100, gpu_id=0)
            start = time.time()
            model.fit(X, y, verbose=0)
            gpu_times.append(time.time() - start)
    except Exception as e:
        log.warning(f"GPU 벤치마크 실패: {e}")
        gpu_times = []

    return {
        'cpu_avg_seconds': np.mean(cpu_times),
        'gpu_avg_seconds': np.mean(gpu_times) if gpu_times else None,
        'speedup': np.mean(cpu_times) / np.mean(gpu_times) if gpu_times else None,
        'n_rows': n_rows,
        'n_features': n_features,
        'n_runs': n_runs,
    }


def generate_setup_report(
    cuda_info: Dict,
    device_info: Dict,
    xgb_info: Dict,
    lgb_info: Dict,
    benchmark: Dict,
) -> str:
    """GPU 설정 보고서 생성."""
    timestamp = datetime.now().isoformat()

    report = f"""# GPU 환경 설정 검증 보고서

**생성 시각**: {timestamp}

## 1. CUDA 환경

"""

    for key, value in cuda_info.items():
        report += f"- {key}: {value}\n"

    report += "\n## 2. GPU 장치 정보\n\n"

    for key, value in device_info.items():
        report += f"- {key}: {value}\n"

    report += "\n## 3. XGBoost GPU 지원\n\n"

    for key, value in xgb_info.items():
        report += f"- {key}: {value}\n"

    report += "\n## 4. LightGBM GPU 지원\n\n"

    for key, value in lgb_info.items():
        report += f"- {key}: {value}\n"

    report += "\n## 5. 성능 벤치마크 (XGBoost)\n\n"

    for key, value in benchmark.items():
        if isinstance(value, float):
            report += f"- {key}: {value:.2f}\n"
        else:
            report += f"- {key}: {value}\n"

    report += "\n## 6. 권장사항\n\n"

    all_pass = (
        cuda_info.get('torch_cuda_available') and
        device_info.get('is_rtx_5050', False) and
        xgb_info.get('available') and
        lgb_info.get('available')
    )

    if all_pass:
        report += """✅ **모든 조건 충족**: GPU 훈련 준비 완료
- Phase 13.2.2 모델 훈련 시작 가능
- 예상 가속률: 7배 (CPU 35분 → GPU 5분)
"""
    else:
        report += "⚠️ **확인 필요**: GPU 훈련 준비 미완료\n"
        if not cuda_info.get('torch_cuda_available'):
            report += "- CUDA 설치 필요\n"
        if not device_info.get('is_rtx_5050'):
            report += "- RTX 5050 미확인 (다른 GPU 사용 중)\n"
        if not xgb_info.get('available'):
            report += "- XGBoost GPU 활성화 필요 (`pip install xgboost[gpu]`)\n"
        if not lgb_info.get('available'):
            report += "- LightGBM GPU 활성화 필요 (`pip install lightgbm[gpu]`)\n"

    return report


def main() -> None:
    """메인 실행 함수."""
    log.info("=" * 60)
    log.info("Phase 13.2.1: GPU 환경 설정 검증")
    log.info("=" * 60)

    # 1. 환경 검증
    log.info("\n1. CUDA 환경 확인...")
    cuda_info = check_cuda()
    log.info(f"  결과: {cuda_info}")

    log.info("\n2. GPU 장치 확인...")
    device_info = check_gpu_device()
    log.info(f"  결과: {device_info}")

    log.info("\n3. XGBoost GPU 확인...")
    xgb_info = check_xgboost_gpu()
    log.info(f"  결과: {xgb_info}")

    log.info("\n4. LightGBM GPU 확인...")
    lgb_info = check_lightgbm_gpu()
    log.info(f"  결과: {lgb_info}")

    # 2. 성능 벤치마크
    log.info("\n5. XGBoost 성능 벤치마크 (CPU vs GPU)...")
    benchmark = benchmark_xgboost_cpu_vs_gpu(n_rows=1000, n_features=5, n_runs=3)
    log.info(f"  결과: {benchmark}")

    # 3. 보고서 생성
    log.info("\n6. 보고서 생성...")
    report = generate_setup_report(cuda_info, device_info, xgb_info, lgb_info, benchmark)

    # 저장
    report_path = Path("GPU_SETUP_REPORT.md")
    report_path.write_text(report)
    log.info(f"  저장: {report_path}")

    # 결과 출력
    print("\n" + report)

    # JSON 저장 (프로그래밍 기반 검증용)
    json_path = Path("gpu_setup_results.json")
    results = {
        'timestamp': datetime.now().isoformat(),
        'cuda': cuda_info,
        'device': device_info,
        'xgboost': xgb_info,
        'lightgbm': lgb_info,
        'benchmark': {k: v for k, v in benchmark.items() if not isinstance(v, np.ndarray)},
    }
    json_path.write_text(json.dumps(results, indent=2))
    log.info(f"  JSON 저장: {json_path}")

    log.info("\n✅ GPU 환경 설정 검증 완료")


if __name__ == '__main__':
    main()
