"""
Phase 13.5 - KR 자동화 엔진: 주간 재학습 → 검증 → 배포 결정 → 알림

기존 파이프라인 스크립트(generate_kr_realistic_data.py, train_kr_model.py,
phase13_model_validator.py, phase13_model_converter.py)를 순서대로 실행하고,
검증 리포트를 기준으로 모델 레지스트리에 등록/활성화 여부를 결정한다.

실행:
    python scripts/phase13_automation_engine.py
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from phase13_model_registry import ModelMetadata, ModelRegistry

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

TARGET_R2 = 0.84
TARGET_MAPE = 0.105
SUBPROCESS_TIMEOUT_SEC = 300
MAX_STDERR_CHARS = 2000
DEFAULT_DATA_ROWS = 10000


@dataclass
class StepResult:
    """단일 파이프라인 단계 실행 결과."""
    name: str
    success: bool
    elapsed_sec: float
    error: str = ""


class NotificationLogger:
    """구조화된 알림을 JSON Lines 파일에 기록한다.

    실제 Slack/이메일 자격증명이 없는 샌드박스 환경이므로, 외부 서비스를
    호출하는 척하는 가짜 스텁 대신 실제로 동작하는 로컬 알림 로그를 남긴다.
    운영 환경에서는 이 로거를 실제 웹훅 클라이언트로 교체하면 된다.
    """

    def __init__(self, log_path: str = 'output/automation_alerts.jsonl') -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def notify(self, level: str, message: str, context: Dict[str, Any] = None) -> None:
        """알림 기록 (level: info/warning/critical)."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            'context': context or {},
        }
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        log_fn = {'critical': log.error, 'warning': log.warning}.get(level, log.info)
        log_fn(f"[{level.upper()}] {message}")


def run_step(name: str, command: List[str]) -> StepResult:
    """서브프로세스로 파이프라인 단계 실행."""
    log.info(f"\n▶ {name}")
    t0 = time.time()
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_SEC)
        elapsed = time.time() - t0
        if result.returncode != 0:
            return StepResult(name, False, elapsed, result.stderr[-MAX_STDERR_CHARS:])
        return StepResult(name, True, elapsed)
    except subprocess.TimeoutExpired:
        return StepResult(name, False, time.time() - t0, f"timeout ({SUBPROCESS_TIMEOUT_SEC}s 초과)")


def run_pipeline(data_rows: int = DEFAULT_DATA_ROWS) -> List[StepResult]:
    """데이터 생성 → 학습 → 검증 → 변환 전체 파이프라인 실행."""
    py = sys.executable
    steps = [
        ("데이터 생성", [py, 'scripts/generate_kr_realistic_data.py',
                     '--rows', str(data_rows), '--output', 'data/raw/KR_data.csv']),
        ("모델 학습", [py, 'scripts/train_kr_model.py', '--data', 'data/raw/KR_data.csv']),
        ("모델 검증", [py, 'scripts/phase13_model_validator.py', '--data', 'data/raw/KR_data.csv']),
        ("ONNX 변환", [py, 'scripts/phase13_model_converter.py']),
    ]

    results = []
    for name, command in steps:
        result = run_step(name, command)
        results.append(result)
        status = "✅" if result.success else "❌"
        log.info(f"  {status} {name} ({result.elapsed_sec:.1f}s)")
        if not result.success:
            log.error(f"  중단: {result.error}")
            break

    return results


def load_validation_report(report_path: str = 'output/kr_validation_report.json') -> Dict[str, Any]:
    """검증 리포트 로드."""
    with open(report_path, encoding='utf-8') as f:
        return json.load(f)


def decide_deployment(report: Dict[str, Any], notifier: NotificationLogger) -> Dict[str, Any]:
    """검증 리포트를 기준으로 배포(활성화) 여부 결정."""
    best_model = report['best_model']
    best_result = report['models'][best_model]
    test_r2 = best_result['test_r2']
    test_mape = best_result['test_mape']
    should_deploy = test_r2 >= TARGET_R2 and test_mape <= TARGET_MAPE

    decision = {
        'best_model': best_model,
        'test_r2': test_r2,
        'test_mape': test_mape,
        'should_deploy': should_deploy,
    }

    if should_deploy:
        notifier.notify('info', f"주간 재학습 성공: {best_model} R²={test_r2:.4f}", decision)
    else:
        notifier.notify(
            'warning',
            f"목표 미달({best_model}): R²={test_r2:.4f}(목표>{TARGET_R2}), "
            f"MAPE={test_mape*100:.1f}%(목표<{TARGET_MAPE*100:.1f}%) - 기존 모델 유지",
            decision,
        )

    return decision


def register_and_apply_decision(decision: Dict[str, Any], registry: ModelRegistry) -> str:
    """모델 등록 + 배포 결정에 따라 active/held 상태 반영.

    phase13_model_validator.py는 승자 알고리즘과 무관하게 항상
    best_model_KR.pkl/.onnx로 정규화해 저장하므로(단, best_model 필드 자체는
    'gradient_boosting'처럼 _KR 접미사 없는 알고리즘 이름), 파일 경로는
    best_model_KR.*을 직접 참조한다.
    """
    version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    pkl_path = Path("output/trained_models/best_model_KR.pkl")
    metadata = ModelMetadata(
        version=version,
        country='KR',
        algorithm=decision['best_model'],
        r2_score=decision['test_r2'],
        mape=decision['test_mape'],
        training_date=datetime.now().isoformat(),
        model_size_mb=pkl_path.stat().st_size / 1024 / 1024,
        ir_size_mb=0.0,
        status='active' if decision['should_deploy'] else 'held',
    )
    return registry.register_model(
        metadata, str(pkl_path), "output/models_ir/best_model_KR.onnx",
    )


def save_run_summary(
    step_results: List[StepResult], decision: Dict[str, Any], model_id: str,
    output_path: str = 'output/automation_run_summary.json',
) -> None:
    """이번 실행 전체 요약 저장."""
    summary = {
        'timestamp': datetime.now().isoformat(),
        'steps': [{'name': r.name, 'success': r.success, 'elapsed_sec': round(r.elapsed_sec, 2)} for r in step_results],
        'pipeline_success': all(r.success for r in step_results),
        'decision': decision,
        'model_id': model_id,
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    log.info(f"\n✅ 실행 요약 저장: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description='Phase 13.5 KR 자동화 엔진')
    parser.add_argument('--rows', type=int, default=DEFAULT_DATA_ROWS)
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("Phase 13.5 자동화 파이프라인 시작")
    log.info("=" * 60)

    notifier = NotificationLogger()
    step_results = run_pipeline(args.rows)

    if not all(r.success for r in step_results):
        notifier.notify('critical', "파이프라인 실패 - 재학습 중단됨", {'steps': [r.name for r in step_results]})
        save_run_summary(step_results, {}, '')
        sys.exit(1)

    report = load_validation_report()
    decision = decide_deployment(report, notifier)
    registry = ModelRegistry()
    model_id = register_and_apply_decision(decision, registry)
    save_run_summary(step_results, decision, model_id)

    log.info("\n" + "=" * 60)
    log.info(f"완료: {model_id} ({'배포됨' if decision['should_deploy'] else '보류'})")
    log.info("=" * 60)


if __name__ == '__main__':
    main()
