"""backend/main.py 의 /dashboard/*, /models*, /settings, /retraining/* 검증.

이 엔드포인트들은 전부 고정 예시값(R²=0.8450 등)을 돌려주고 있었다.
retraining_monitor.RetrainingMonitor(logs/retrain_history.jsonl 를 읽음)와
ml_models.ModelManager(models/*.joblib 를 로드함)는 이미 실제로 동작하는
채로 있었지만 웹소켓 브로드캐스트 루프만 그 둘을 썼다 — REST 엔드포인트는
아무도 호출한 적이 없었다. 이 테스트는 REST가 그 실제 소스를 정확히
반영하는지, 그리고 데이터가 없을 때 가짜 숫자 대신 정직한 빈 상태를
돌려주는지 검증한다.
"""

import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


@pytest.fixture
def client_and_headers(monkeypatch, tmp_path):
    """monitor/history_manager/model_manager를 임시 경로로 격리하고,
    인증된 TestClient를 돌려준다."""
    import backend.main as bm

    history_file = tmp_path / "retrain_history.jsonl"
    config_file = tmp_path / "schedule_config.json"
    monkeypatch.setattr(bm.monitor, "history_file", history_file)
    monkeypatch.setattr(bm.monitor, "config_file", config_file)
    monkeypatch.setattr(bm.history_manager, "history_file", history_file)
    monkeypatch.setattr(bm, "SCHEDULE_CONFIG_FILE", config_file)
    monkeypatch.setattr(bm.model_manager, "models", {})
    monkeypatch.setattr(bm.model_manager, "model_metadata", {})

    from fastapi.testclient import TestClient

    client = TestClient(bm.app)
    r = client.post("/auth/login", params={"email": "admin@avm.com", "password": "demo123"})
    token = r.json()["access_token"]
    return client, {"Authorization": f"Bearer {token}"}, history_file, config_file, bm


def _write_history(path: Path, *records: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


class TestDashboardNoData:
    def test_summary_reports_no_data_instead_of_fake_numbers(self, client_and_headers):
        client, headers, _, _, _ = client_and_headers
        body = client.get("/dashboard/summary", headers=headers).json()
        assert body == {
            "status": "no_data", "ensemble_r2": None, "ensemble_rmse": None,
            "ensemble_mae": None, "last_updated": None, "previous_r2": None, "change_rate": None,
        }

    def test_trend_is_empty_list(self, client_and_headers):
        client, headers, _, _, _ = client_and_headers
        assert client.get("/dashboard/trend", headers=headers).json() == {"data": []}

    def test_recent_trainings_is_empty_list(self, client_and_headers):
        client, headers, _, _, _ = client_and_headers
        assert client.get("/dashboard/recent-trainings", headers=headers).json() == {"data": []}

    def test_statistics_reports_zero_not_fake_score(self, client_and_headers):
        client, headers, _, _, _ = client_and_headers
        body = client.get("/dashboard/statistics", headers=headers).json()
        assert body == {"highest_r2": None, "average_r2": None, "improvement": None, "training_count": 0}


class TestDashboardWithHistory:
    def test_summary_reflects_latest_jsonl_record(self, client_and_headers):
        client, headers, history_file, _, _ = client_and_headers
        _write_history(
            history_file,
            {"timestamp": "2026-08-01T10:00:00", "status": "success",
             "ensemble": {"r2": 0.90, "rmse": 5.0e7, "mae": 4.0e7}},
            {"timestamp": "2026-09-01T10:00:00", "status": "success",
             "ensemble": {"r2": 0.92, "rmse": 4.8e7, "mae": 3.9e7}},
        )

        body = client.get("/dashboard/summary", headers=headers).json()

        assert body["ensemble_r2"] == 0.92
        assert body["status"] == "success"
        assert body["previous_r2"] == 0.90
        assert body["change_rate"] == pytest.approx(2.22, abs=0.01)

    def test_recent_trainings_newest_first(self, client_and_headers):
        client, headers, history_file, _, _ = client_and_headers
        _write_history(
            history_file,
            {"timestamp": "2026-08-01T10:00:00", "status": "success", "ensemble": {"r2": 0.90}},
            {"timestamp": "2026-09-01T10:00:00", "status": "warning", "ensemble": {"r2": 0.85},
             "duration_minutes": 14},
        )

        data = client.get("/dashboard/recent-trainings", headers=headers).json()["data"]

        assert data[0]["date"] == "2026-09-01T10:00:00"
        assert data[0]["status"] == "warning"
        assert data[0]["duration"] == "14분"
        assert data[1]["duration"] is None

    def test_statistics_computed_from_history(self, client_and_headers):
        client, headers, history_file, _, _ = client_and_headers
        _write_history(
            history_file,
            {"timestamp": "t1", "status": "success", "ensemble": {"r2": 0.80}},
            {"timestamp": "t2", "status": "failed", "ensemble": {"r2": 0.70}},
        )

        body = client.get("/dashboard/statistics", headers=headers).json()

        assert body["training_count"] == 2
        assert body["highest_r2"] == 0.80
        assert body["improvement"] == "50.0%"  # 1/2 성공


class TestModelsEndpoints:
    def test_list_models_reflects_model_manager_state(self, client_and_headers):
        client, headers, _, _, bm = client_and_headers
        bm.model_manager.model_metadata["xgboost_latest"] = {
            "type": "xgboost", "display_name": "XGBoost", "version": "20260901_000000",
            "file": "xgboost_real_2024.joblib", "loaded_at": "2026-09-01T00:00:00",
        }

        data = client.get("/models", headers=headers).json()["data"]

        assert data == [{
            "id": "xgboost_latest", "name": "XGBoost", "type": "xgboost",
            "version": "20260901_000000", "loaded": True, "file": "xgboost_real_2024.joblib",
        }]

    def test_get_model_details_404_for_unknown_id(self, client_and_headers):
        client, headers, _, _, _ = client_and_headers
        r = client.get("/models/does_not_exist", headers=headers)
        assert r.status_code == 404

    def test_get_model_details_combines_metadata_and_performance(self, client_and_headers):
        client, headers, history_file, _, bm = client_and_headers
        bm.model_manager.model_metadata["xgboost_latest"] = {
            "type": "xgboost", "display_name": "XGBoost", "version": "v1",
            "file": "xgboost.joblib", "loaded_at": "2026-09-01T00:00:00", "is_real_data": True,
        }
        _write_history(history_file, {
            "timestamp": "t1", "status": "success",
            "models": {"xgboost": {"r2": 0.91, "mae": 4.0e7, "rmse": 5.0e7, "mape": 0.08}},
        })

        body = client.get("/models/xgboost_latest", headers=headers).json()

        assert body["name"] == "XGBoost"
        assert body["is_real_data"] is True
        assert body["r2"] == 0.91
        assert body["mape"] == 0.08

    def test_feature_importance_uses_real_model_attribute(self, client_and_headers):
        from sklearn.ensemble import GradientBoostingRegressor
        import numpy as np

        client, headers, _, config_file, bm = client_and_headers
        config_file.write_text(json.dumps({"feature_columns": ["면적", "지역", "건축년도"]}))

        model = GradientBoostingRegressor(n_estimators=5, random_state=0)
        X = np.random.RandomState(0).rand(20, 3)
        y = X[:, 0] * 100
        model.fit(X, y)
        bm.model_manager.models["gb_latest"] = model

        data = client.get("/models/gb_latest/feature-importance", headers=headers).json()["data"]

        assert len(data) == 3
        assert {d["name"] for d in data} == {"면적", "지역", "건축년도"}
        assert pytest.approx(sum(d["importance"] for d in data), abs=0.5) == 100.0

    def test_feature_importance_falls_back_to_generic_names_on_mismatch(self, client_and_headers):
        from sklearn.ensemble import GradientBoostingRegressor
        import numpy as np

        client, headers, _, config_file, bm = client_and_headers
        config_file.write_text(json.dumps({"feature_columns": ["딱_한개"]}))  # 개수 안 맞음

        model = GradientBoostingRegressor(n_estimators=5, random_state=0)
        X = np.random.RandomState(0).rand(20, 3)
        model.fit(X, X[:, 0])
        bm.model_manager.models["gb_latest"] = model

        data = client.get("/models/gb_latest/feature-importance", headers=headers).json()["data"]

        assert {d["name"] for d in data} == {"feature_0", "feature_1", "feature_2"}

    def test_feature_importance_message_for_unsupported_model(self, client_and_headers):
        from sklearn.linear_model import LinearRegression

        client, headers, _, _, bm = client_and_headers
        bm.model_manager.models["linear_latest"] = LinearRegression()

        body = client.get("/models/linear_latest/feature-importance", headers=headers).json()

        assert body["data"] == []
        assert "message" in body


class TestSettingsRoundTrip:
    def test_get_settings_defaults_when_no_config_file(self, client_and_headers):
        client, headers, _, _, _ = client_and_headers
        body = client.get("/settings", headers=headers).json()
        assert body["performance_threshold"] == 0.95
        assert body["email_alert"] is False

    def test_put_then_get_persists_to_schedule_config_file(self, client_and_headers):
        client, headers, _, config_file, _ = client_and_headers

        r = client.put("/settings", headers=headers, json={
            "performance_threshold": 0.88, "email_alert": True,
            "email_address": "ops@example.com", "slack_alert": True,
        })
        assert r.status_code == 200
        assert r.json()["settings"]["performance_threshold"] == 0.88

        # 실제로 파일에 쓰였는지, 그리고 재조회 시 반영되는지 둘 다 확인
        on_disk = json.loads(config_file.read_text())
        assert on_disk["performance_threshold"] == 0.88
        assert on_disk["alert_config"]["email_address"] == "ops@example.com"

        refetched = client.get("/settings", headers=headers).json()
        assert refetched["performance_threshold"] == 0.88
        assert refetched["slack_alert"] is True

    def test_put_preserves_fields_it_does_not_touch(self, client_and_headers):
        client, headers, _, config_file, _ = client_and_headers
        config_file.write_text(json.dumps({
            "performance_threshold": 0.95,
            "model_config": {"xgboost": {"n_estimators": 300}},
        }))

        client.put("/settings", headers=headers, json={"performance_threshold": 0.80})

        on_disk = json.loads(config_file.read_text())
        assert on_disk["model_config"] == {"xgboost": {"n_estimators": 300}}


class TestRetrainingEndpoints:
    def test_status_no_data(self, client_and_headers):
        client, headers, _, _, _ = client_and_headers
        body = client.get("/retraining/status", headers=headers).json()
        assert body["status"] == "no_data"
        assert body["last_training"] is None

    def test_status_and_history_reflect_jsonl(self, client_and_headers):
        client, headers, history_file, _, _ = client_and_headers
        _write_history(history_file, {
            "timestamp": "2026-09-01T00:00:00", "status": "success",
            "ensemble": {"r2": 0.9}, "duration_minutes": 20,
        })

        status = client.get("/retraining/status", headers=headers).json()
        assert status["status"] == "success"
        assert status["last_training"] == "2026-09-01T00:00:00"

        history = client.get("/retraining/history", headers=headers).json()["data"]
        assert history == [{
            "date": "2026-09-01T00:00:00", "status": "success", "r2": 0.9, "duration_minutes": 20,
        }]


class TestAuthRequired:
    @pytest.mark.parametrize("path", [
        "/dashboard/summary", "/models", "/settings", "/retraining/status",
    ])
    def test_requires_auth(self, client_and_headers, path):
        client, _, _, _, _ = client_and_headers
        assert client.get(path).status_code == 401
