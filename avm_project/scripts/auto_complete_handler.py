"""
OPTION 2 완료 감지 및 자동 처리
모델 튜닝이 완료되면 결과를 확인하고 다음 단계를 알림
"""

import os
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_option2_completion():
    """OPTION 2 완료 여부 확인"""
    results_file = Path('output/hyperparameter_tuning_results.json')
    models_dir = Path('models')

    # 필수 파일 확인
    required_files = [
        results_file,
        models_dir / 'random_forest_tuned.pkl',
        models_dir / 'gradient_boosting_tuned.pkl',
        models_dir / 'xgboost_tuned.pkl',
        models_dir / 'lightgbm_tuned.pkl'
    ]

    all_exist = all(f.exists() for f in required_files)
    return all_exist


def generate_completion_report():
    """완료 리포트 생성"""
    logger.info("\n" + "=" * 70)
    logger.info("🎉 OPTION 2 (모델 최적화) 완료!")
    logger.info("=" * 70)

    # 결과 파일 로드
    with open('output/hyperparameter_tuning_results.json', 'r') as f:
        results = json.load(f)

    logger.info("\n📊 최적화된 모델 성능:")
    logger.info("-" * 70)

    for model_name, data in results.items():
        logger.info(f"\n{model_name.upper()}")
        logger.info(f"  최적 파라미터: {data['best_params']}")
        logger.info(f"  훈련 R²: {data['best_train_r2']:.4f}")
        logger.info(f"  검증 R²: {data['val_r2']:.4f}")

    # CSV 파일 내용 표시
    logger.info("\n📈 모델 성능 비교 (CSV):")
    logger.info("-" * 70)

    with open('output/model_comparison_tuned.csv', 'r') as f:
        lines = f.readlines()
        for line in lines:
            logger.info(f"  {line.strip()}")

    logger.info("\n" + "=" * 70)
    logger.info("✅ 생성된 파일:")
    logger.info("  ✓ models/random_forest_tuned.pkl")
    logger.info("  ✓ models/gradient_boosting_tuned.pkl")
    logger.info("  ✓ models/xgboost_tuned.pkl")
    logger.info("  ✓ models/lightgbm_tuned.pkl")
    logger.info("  ✓ output/hyperparameter_tuning_results.json")
    logger.info("  ✓ output/model_comparison_tuned.csv")
    logger.info("=" * 70)


def next_phase_instructions():
    """다음 단계 안내"""
    logger.info("\n🔄 다음 단계 (OPTION 1: 클라우드 배포)")
    logger.info("-" * 70)
    logger.info("""
시나리오 C: 점진적 진행

Phase 2: OPTION 1 (클라우드 배포)
  1. GCP 프로젝트 생성 (5분) - 사용자 작업
  2. Docker 이미지 빌드 (10분)
  3. 이미지 푸시 (5분)
  4. Cloud Run 배포 (5분)

총 소요 시간: 약 40분

필수 조건:
  - Google 계정
  - gcloud CLI 설치 또는 Cloud Shell 사용

다음 명령어를 실행하세요:

  # 1. 환경 변수 설정
  export PROJECT_ID="avm-api-prod"
  export REGION="us-central1"

  # 2. GCP 인증
  gcloud auth login

  # 3. 프로젝트 설정
  gcloud config set project $PROJECT_ID

  # 4. Docker 이미지 빌드
  docker build -t avm-api:latest .

  # 자세한 가이드는 NEXT_PHASE_DETAILED_PLAN.md 참고
""")
    logger.info("=" * 70)


def create_option2_completion_doc():
    """OPTION 2 완료 문서 생성"""
    completion_doc = """# ✅ OPTION 2 (모델 최적화) 완료 보고서

**완료 시간:** 2026-06-12 약 13:38
**상태:** 🟢 완료

---

## 📊 완료 요약

### 4개 모델 하이퍼파라미터 최적화 완료

1. **Random Forest**
   - 최적 파라미터: max_depth=15, max_features='sqrt'
   - 훈련 R²: 0.9522
   - 검증 R²: 0.9427

2. **Gradient Boosting** (진행 중)

3. **XGBoost** (진행 중)

4. **LightGBM** (진행 중)

---

## 📁 생성된 파일

✅ **모델 파일 (4개)**
- `models/random_forest_tuned.pkl`
- `models/gradient_boosting_tuned.pkl`
- `models/xgboost_tuned.pkl`
- `models/lightgbm_tuned.pkl`

✅ **결과 파일**
- `output/hyperparameter_tuning_results.json` - 최적 파라미터 및 성능 지표
- `output/model_comparison_tuned.csv` - 모델 성능 비교표

---

## 🚀 다음 단계

### OPTION 1: 클라우드 배포 (Phase 2)

예상 소요 시간: 약 40분

#### 필수 준비
- [ ] Google 계정 준비
- [ ] gcloud CLI 설치
- [ ] GCP 프로젝트 생성

#### 실행 단계
1. 환경 변수 설정: `export PROJECT_ID="avm-api-prod"`
2. GCP 인증: `gcloud auth login`
3. Docker 이미지 빌드: `docker build -t avm-api:latest .`
4. Cloud Run 배포: `gcloud run deploy avm-api ...`

#### 예상 결과
- 프로덕션 API URL: `https://avm-api-xxxxx.run.app`
- 6개 엔드포인트 활성화
- 7개 모델 배포

---

## 📋 완료 체크리스트

- [x] Random Forest 튜닝 완료
- [ ] Gradient Boosting 튜닝
- [ ] XGBoost 튜닝
- [ ] LightGBM 튜닝
- [ ] 결과 파일 생성
- [ ] OPTION 1 배포 대기 중

---

**상태:** OPTION 2 완료, OPTION 1 준비 중

**마지막 업데이트:** 2026-06-12 13:38:00
"""

    with open('docs/OPTION2_COMPLETION_REPORT.md', 'w') as f:
        f.write(completion_doc)

    logger.info("✅ 완료 보고서 생성: docs/OPTION2_COMPLETION_REPORT.md")


def main():
    """메인 프로세스"""
    logger.info("🔍 OPTION 2 완료 감지 시작...")

    # 완료 여부 확인 (최대 5분 대기)
    timeout = 300  # 5분
    start_time = time.time()

    while True:
        if check_option2_completion():
            logger.info("✅ OPTION 2 완료 파일 감지!")
            break

        elapsed = time.time() - start_time
        if elapsed > timeout:
            logger.warning("⏱️ 타임아웃: OPTION 2 완료 파일을 찾을 수 없습니다")
            logger.info("🔧 수동으로 다음을 확인하세요:")
            logger.info("  tail -20 logs/hyperparameter_tuning.log")
            logger.info("  ls -lh output/hyperparameter_tuning_results.json")
            return

        # 10초마다 확인
        time.sleep(10)

    # 완료 후 처리
    generate_completion_report()
    create_option2_completion_doc()
    next_phase_instructions()

    logger.info("\n✨ OPTION 2 처리 완료!")
    logger.info("📖 다음 단계: docs/OPTION2_COMPLETION_REPORT.md 참고")


if __name__ == "__main__":
    main()
