"""Phase 13.5 자동화 엔진 & 드리프트 감지 단위 테스트"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from phase13_automation_engine import (
    NotificationLogger,
    decide_deployment,
    register_and_apply_decision,
)
from phase13_drift_detector import detect_drift, summarize_drift
from phase13_model_registry import ModelRegistry


@pytest.fixture
def tmp_notifier(tmp_path):
    return NotificationLogger(log_path=str(tmp_path / "alerts.jsonl"))


class TestDecideDeployment:
    def test_deploys_when_targets_met(self, tmp_notifier):
        report = {
            'best_model': 'lightgbm',
            'models': {'lightgbm': {'test_r2': 0.90, 'test_mape': 0.08}},
        }
        decision = decide_deployment(report, tmp_notifier)
        assert decision['should_deploy'] is True

    def test_holds_when_r2_below_target(self, tmp_notifier):
        report = {
            'best_model': 'gradient_boosting',
            'models': {'gradient_boosting': {'test_r2': 0.80, 'test_mape': 0.08}},
        }
        decision = decide_deployment(report, tmp_notifier)
        assert decision['should_deploy'] is False

    def test_holds_when_mape_above_target(self, tmp_notifier):
        """실제 KR 파이프라인 현재 상태: R²=0.95(높음)이지만 MAPE=11.3%(목표 초과)로 보류."""
        report = {
            'best_model': 'gradient_boosting',
            'models': {'gradient_boosting': {'test_r2': 0.956, 'test_mape': 0.113}},
        }
        decision = decide_deployment(report, tmp_notifier)
        assert decision['should_deploy'] is False

    def test_writes_alert_log_entry(self, tmp_path, tmp_notifier):
        report = {
            'best_model': 'xgboost',
            'models': {'xgboost': {'test_r2': 0.90, 'test_mape': 0.08}},
        }
        decide_deployment(report, tmp_notifier)
        lines = (tmp_path / "alerts.jsonl").read_text().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry['level'] == 'info'


class TestRegisterAndApplyDecision:
    def test_uses_best_model_kr_canonical_path(self, tmp_path, monkeypatch):
        """best_model 필드는 '_KR' 접미사가 없는 알고리즘 이름이지만,
        실제 파일 경로는 항상 best_model_KR.pkl을 참조해야 한다
        (과거 버그: decision['best_model']을 그대로 파일명에 써서
        'gradient_boosting.pkl'을 찾다 FileNotFoundError 발생)."""
        models_dir = tmp_path / "output" / "trained_models"
        models_dir.mkdir(parents=True)
        (models_dir / "best_model_KR.pkl").write_bytes(b"x" * 1024)
        monkeypatch.chdir(tmp_path)

        registry = ModelRegistry(registry_dir=str(tmp_path / "registry"))
        decision = {'best_model': 'gradient_boosting', 'test_r2': 0.95, 'test_mape': 0.11, 'should_deploy': False}
        model_id = register_and_apply_decision(decision, registry)  # 과거엔 FileNotFoundError로 여기서 실패했다

        assert model_id.startswith("KR_gradient_boosting_v")
        entries = registry.list_models('KR')
        assert entries[0]['status'] == 'held'

    def test_active_status_when_deployed(self, tmp_path, monkeypatch):
        models_dir = tmp_path / "output" / "trained_models"
        models_dir.mkdir(parents=True)
        (models_dir / "best_model_KR.pkl").write_bytes(b"x" * 1024)
        monkeypatch.chdir(tmp_path)

        registry = ModelRegistry(registry_dir=str(tmp_path / "registry"))
        decision = {'best_model': 'lightgbm', 'test_r2': 0.90, 'test_mape': 0.08, 'should_deploy': True}
        register_and_apply_decision(decision, registry)

        entries = registry.list_models('KR')
        assert entries[0]['status'] == 'active'


class TestDriftDetector:
    def test_no_drift_for_identical_distributions(self):
        rng = np.random.RandomState(42)
        reference = pd.DataFrame({'area_sqm': rng.normal(80, 10, 500)})
        current = pd.DataFrame({'area_sqm': rng.normal(80, 10, 500)})
        results = detect_drift(reference, current, ['area_sqm'])
        assert results['area_sqm'].is_drifted is False

    def test_detects_drift_for_shifted_distribution(self):
        rng = np.random.RandomState(42)
        reference = pd.DataFrame({'area_sqm': rng.normal(80, 10, 500)})
        current = pd.DataFrame({'area_sqm': rng.normal(150, 10, 500)})  # 큰 평균 이동
        results = detect_drift(reference, current, ['area_sqm'])
        assert results['area_sqm'].is_drifted is True
        assert results['area_sqm'].severity == 'high'

    def test_skips_missing_features(self):
        reference = pd.DataFrame({'area_sqm': [1, 2, 3]})
        current = pd.DataFrame({'area_sqm': [1, 2, 3]})
        results = detect_drift(reference, current, ['area_sqm', 'nonexistent'])
        assert 'nonexistent' not in results
        assert 'area_sqm' in results

    def test_summarize_drift_counts_correctly(self):
        rng = np.random.RandomState(1)
        reference = pd.DataFrame({
            'a': rng.normal(0, 1, 300),
            'b': rng.normal(0, 1, 300),
        })
        current = pd.DataFrame({
            'a': rng.normal(0, 1, 300),  # 드리프트 없음
            'b': rng.normal(10, 1, 300),  # 큰 드리프트
        })
        results = detect_drift(reference, current, ['a', 'b'])
        summary = summarize_drift(results)
        assert summary['drifted_count'] == 1
        assert 'b' in summary['drifted_features']
        assert summary['has_high_severity'] is True
