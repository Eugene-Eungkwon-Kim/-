"""
PHASE 2.1.2 - AVM 자동 재학습 오케스트레이터 (AUTO-LOOP)

주간 자동 실행되는 엔드투엔드 파이프라인:
  1) 최신 데이터 수집 (실패 시 기존 데이터로 폴백)
  2) 6개 모델 재학습 및 평가
  3) 최고 성능 모델 선택 + 회귀(regression) 가드
  4) 모델 승격(promotion) 및 SHA256 서명
  5) 실행 로그/메트릭 기록

Cron 등록 예시 (매주 목요일 10:00):
  0 10 * * 4 cd /home/user/-/avm_project && python scripts/auto_retraining.py >> logs/cron_auto_retraining.log 2>&1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.avm_injection_engine import AVMModelInjectionEngine  # noqa: E402

PROJECT_ROOT = Path(__file__).parent.parent
MODEL_DIR = PROJECT_ROOT / "models"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOGS_DIR = PROJECT_ROOT / "logs"
REGISTRY_FILE = MODEL_DIR / "model_registry.json"

# 신규 모델이 기존 챔피언 대비 이 값 이상 R²가 하락하면 승격 거부
REGRESSION_TOLERANCE = 0.02


def _log(msg: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{stamp}] {msg}", flush=True)


def sha256_of(path: Path) -> str:
    """파일의 SHA256 해시 계산 (모델 무결성 검증용)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_registry() -> dict:
    """모델 레지스트리 로드 (없으면 빈 레지스트리)."""
    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"champion": None, "history": []}


def save_registry(registry: dict) -> None:
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


def run_retraining(dry_run: bool = False) -> dict:
    """자동 재학습 파이프라인 실행. 실행 요약 dict 반환."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    started = datetime.now()
    _log("=" * 70)
    _log("🔄 AVM 자동 재학습 (AUTO-LOOP) 시작")
    _log("=" * 70)

    registry = load_registry()
    prev_champion = registry.get("champion")
    prev_r2 = prev_champion["test_r2"] if prev_champion else None
    if prev_champion:
        _log(f"기존 챔피언: {prev_champion['name']} (R²={prev_r2:.4f})")
    else:
        _log("기존 챔피언 없음 (최초 학습)")

    # --- Step 1-6: 데이터 로드 → 학습 → 평가 → 저장 ---
    engine = AVMModelInjectionEngine()
    df = engine.load_all_training_data()
    X, y, feature_names = engine.prepare_features(df)
    X_train, X_test, y_train, y_test = engine.split_data(X, y)
    engine.X_train, engine.X_test = X_train, X_test
    engine.y_train, engine.y_test = y_train, y_test
    engine.train_models(X_train, y_train)
    results = engine.evaluate_models(X_train, X_test, y_train, y_test)

    # --- Step 7: 최고 성능 모델 선택 ---
    best_name, best_res = max(results.items(), key=lambda kv: kv[1]["test_r2"])
    new_r2 = best_res["test_r2"]
    _log(f"신규 최고 모델: {best_name} (R²={new_r2:.4f})")

    # --- 회귀 가드: 성능 급락 시 승격 거부 ---
    promote = True
    reason = "최초 학습" if prev_r2 is None else "성능 동등/개선"
    if prev_r2 is not None and new_r2 < prev_r2 - REGRESSION_TOLERANCE:
        promote = False
        reason = (
            f"성능 회귀 감지 (신규 {new_r2:.4f} < 기존 {prev_r2:.4f} "
            f"- 허용오차 {REGRESSION_TOLERANCE})"
        )
        _log(f"⛔ 승격 거부: {reason}")
    else:
        _log(f"✅ 승격 승인: {reason}")

    summary = {
        "timestamp": started.isoformat(),
        "duration_sec": (datetime.now() - started).total_seconds(),
        "dry_run": dry_run,
        "best_model": best_name,
        "new_r2": new_r2,
        "previous_r2": prev_r2,
        "promoted": promote and not dry_run,
        "promotion_reason": reason,
        "all_results": {k: v["test_r2"] for k, v in results.items()},
        "feature_count": len(feature_names),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
    }

    if dry_run:
        _log("🧪 DRY-RUN 모드: 모델 저장/승격 생략")
        _write_summary(summary, started)
        return summary

    # 모델 저장
    engine.save_models()

    if promote:
        champion_path = MODEL_DIR / f"{best_name}_model.joblib"
        prod_path = MODEL_DIR / "production_model.joblib"
        if champion_path.exists():
            shutil.copyfile(champion_path, prod_path)
            digest = sha256_of(prod_path)
            registry["champion"] = {
                "name": best_name,
                "test_r2": new_r2,
                "test_rmse": best_res["test_rmse"],
                "sha256": digest,
                "promoted_at": datetime.now().isoformat(),
                "model_file": "production_model.joblib",
            }
            registry["history"].append(registry["champion"])
            save_registry(registry)
            _log(f"🏆 프로덕션 승격: {best_name} → production_model.joblib")
            _log(f"   SHA256: {digest[:16]}...")
            summary["sha256"] = digest

    _write_summary(summary, started)
    _log("=" * 70)
    _log(f"✅ 자동 재학습 완료 ({summary['duration_sec']:.2f}초)")
    _log("=" * 70)
    return summary


def _write_summary(summary: dict, started: datetime) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fname = OUTPUT_DIR / f"auto_retraining_{started.strftime('%Y%m%d_%H%M%S')}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    _log(f"📋 실행 요약 저장: {fname.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="AVM 자동 재학습 오케스트레이터")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="모델 저장/승격 없이 파이프라인만 검증",
    )
    args = parser.parse_args()
    try:
        summary = run_retraining(dry_run=args.dry_run)
        return 0 if summary else 1
    except Exception as exc:  # noqa: BLE001 - 자동화 진입점에서 모든 실패를 로깅
        _log(f"❌ 자동 재학습 실패: {exc}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
