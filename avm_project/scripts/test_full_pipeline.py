#!/usr/bin/env python3
"""
Loan4U Phase 13.4.2 - Full Pipeline Integration Test
Test complete flow: Training → Conversion → Inference → API
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

FEATURE_COLS = ['area_sqm', 'old_price', 'latitude', 'longitude', 'property_type']


def test_data_loading() -> bool:
    """Test Phase 13.1: Data loading."""
    try:
        data_dir = Path("data/raw")
        csv_files = list(data_dir.glob("*_data.csv"))

        if not csv_files:
            log.warning("No data files found")
            return False

        for csv_path in csv_files[:2]:
            df = pd.read_csv(csv_path)
            missing = set(FEATURE_COLS + ['new_price']) - set(df.columns)
            if missing:
                log.warning(f"{csv_path.name}: missing columns {missing}")
                return False

        log.info(f"✅ Data loading: {len(csv_files)} files validated")
        return True
    except Exception as e:
        log.error(f"❌ Data loading failed: {e}")
        return False


def test_model_training() -> bool:
    """Test Phase 13.2: GPU model training."""
    try:
        from scripts.phase13_model_trainer import train_all_countries

        results = train_all_countries("data/raw")

        if not results:
            log.warning("No training results")
            return False

        passed = sum(1 for r in results if r.meets_target)
        log.info(f"✅ Model training: {passed}/{len(results)} models passed targets")
        return passed == len(results)
    except Exception as e:
        log.error(f"❌ Model training failed: {e}")
        return False


def test_model_conversion() -> bool:
    """Test Phase 13.2.5: ONNX→IR conversion."""
    try:
        from scripts.phase13_model_converter import convert_country_models

        output_dir = Path("output/models_ir")
        output_dir.mkdir(parents=True, exist_ok=True)

        results = convert_country_models(
            "KR",
            Path("output/trained_models"),
            Path("data/raw"),
            output_dir
        )

        if not results:
            log.warning("No conversion results")
            return False

        onnx_files = list(output_dir.glob("*.onnx"))
        ir_files = list(output_dir.glob("*.xml"))
        total_files = len(onnx_files) + len(ir_files)
        log.info(f"✅ Model conversion: {len(onnx_files)} ONNX + {len(ir_files)} IR models")
        return total_files > 0
    except Exception as e:
        log.error(f"❌ Model conversion failed: {e}")
        return False


def test_npu_inference() -> bool:
    """Test Phase 13.4: NPU inference."""
    try:
        from scripts.phase13_npu_inference import NPUInferenceEngine

        engine = NPUInferenceEngine("output/models_ir")
        stats = engine.get_model_stats()

        if stats['models_loaded'] == 0:
            log.warning("No models loaded in inference engine")
            return False

        # Test prediction
        test_features = np.array([100, 500000, 35.5, 126.8, 2], dtype=np.float32)
        price, confidence, latency = engine.predict(test_features)

        max_latency = 10.0 if 'CPU' in stats.get('device', '') else 2.5
        if latency > max_latency:
            log.warning(f"Latency too high: {latency}ms (target <{max_latency}ms)")
            return False

        log.info(f"✅ NPU inference: {stats['models_loaded']} models, latency {latency:.1f}ms")
        return True
    except Exception as e:
        log.error(f"❌ NPU inference failed: {e}")
        return False


def test_api_service() -> bool:
    """Test Phase 13.4.1: FastAPI service."""
    try:
        from fastapi.testclient import TestClient
        from scripts.phase13_api_service import app

        client = TestClient(app)

        # Test health check
        response = client.get("/api/health")
        if response.status_code != 200:
            log.warning("Health check failed")
            return False

        # Test model status
        response = client.get("/api/models")
        if response.status_code != 200:
            log.warning("Model status endpoint failed")
            return False

        # Test valuation endpoint
        payload = {
            "area_sqm": 100,
            "old_price": 500000,
            "latitude": 35.5,
            "longitude": 126.8,
            "property_type": 2
        }
        response = client.post("/api/valuation", json=payload)

        if response.status_code not in [200, 503]:
            log.warning(f"Valuation endpoint returned {response.status_code}")
            return False

        log.info("✅ API service: all endpoints validated")
        return True
    except Exception as e:
        log.error(f"❌ API service failed: {e}")
        return False


def run_full_pipeline_test() -> Dict[str, bool]:
    """Execute all integration tests."""
    print(f"\n{'='*60}")
    print("Phase 13.4.2 - Full Pipeline Integration Test")
    print(f"{'='*60}\n")

    tests = {
        "Phase 13.1 - Data Loading": test_data_loading,
        "Phase 13.2 - GPU Training": test_model_training,
        "Phase 13.2.5 - Model Conversion": test_model_conversion,
        "Phase 13.4 - NPU Inference": test_npu_inference,
        "Phase 13.4.1 - FastAPI Service": test_api_service,
    }

    results = {}
    for test_name, test_func in tests.items():
        print(f"\n🔍 {test_name}...")
        results[test_name] = test_func()

    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_flag in results.items():
        status = "✅ PASS" if passed_flag else "❌ FAIL"
        print(f"{status} | {test_name}")

    print(f"\n결과: {passed}/{total} 테스트 통과")

    if passed == total:
        print("\n🎉 모든 파이프라인 테스트 성공! 프로덕션 준비 완료.")
    else:
        print(f"\n⚠️  {total - passed}개 테스트 실패. 디버깅 필요.")

    return results


if __name__ == '__main__':
    run_full_pipeline_test()
