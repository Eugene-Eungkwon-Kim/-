"""
메인 파이프라인 오케스트레이션
전체 ETL 워크플로우 관리: 다운로드 → 마이그레이션 → 디버깅 → 인덱싱 → 클렌징
"""

import subprocess
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

SCRIPTS_DIR = Path(__file__).parent
TIMESTAMP = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


class PipelineOrchestrator:
    def __init__(self):
        self.scripts = [
            ('download_data.py', '📥 데이터 다운로드'),
            ('migrate_data.py', '🚚 데이터 마이그레이션'),
            ('debug_data.py', '🔍 데이터 검증'),
            ('index_data.py', '📑 데이터 인덱싱'),
            ('cleanse_data.py', '🧹 데이터 클렌징'),
        ]
        self.results = {}
        self.start_time = None

    def run_script(self, script_name, description):
        """개별 스크립트 실행"""
        script_path = SCRIPTS_DIR / script_name

        if not script_path.exists():
            logger.error(f"❌ 스크립트 없음: {script_path}")
            return False

        logger.info("\n" + "="*70)
        logger.info(f"{description} - {script_name}")
        logger.info("="*70)

        try:
            start = time.time()
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=600  # 10분 타임아웃
            )

            elapsed = time.time() - start

            if result.returncode == 0:
                logger.info(f"✅ {description} 완료 ({elapsed:.1f}초)")
                self.results[script_name] = {
                    'status': 'success',
                    'time': elapsed
                }
                return True
            else:
                logger.error(f"❌ {description} 실패")
                logger.error(f"stdout: {result.stdout}")
                logger.error(f"stderr: {result.stderr}")
                self.results[script_name] = {
                    'status': 'failed',
                    'error': result.stderr
                }
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"⏱️ {description} 타임아웃 (10분 초과)")
            self.results[script_name] = {'status': 'timeout'}
            return False
        except Exception as e:
            logger.error(f"❌ {description} 오류: {str(e)}")
            self.results[script_name] = {'status': 'error', 'error': str(e)}
            return False

    def generate_summary(self):
        """파이프라인 실행 요약 생성"""
        logger.info("\n" + "="*70)
        logger.info("🎯 파이프라인 실행 요약")
        logger.info("="*70)

        total_time = sum(r.get('time', 0) for r in self.results.values() if r.get('status') == 'success')
        successful = sum(1 for r in self.results.values() if r.get('status') == 'success')
        failed = sum(1 for r in self.results.values() if r.get('status') != 'success')

        summary_content = f"""# 🎯 ETL 파이프라인 실행 보고서

**실행일시:** {TIMESTAMP}
**상태:** {'✅ 완료' if failed == 0 else '⚠️ 일부 실패'}

---

## 📊 실행 결과

### 처리 단계

"""

        for script, result in self.results.items():
            status = result.get('status')
            time_str = f"{result.get('time', 0):.1f}초" if status == 'success' else ''

            status_icon = {
                'success': '✅',
                'failed': '❌',
                'timeout': '⏱️',
                'error': '❌'
            }.get(status, '❓')

            summary_content += f"- {status_icon} {script}: {status} {time_str}\n"

        summary_content += f"""

### 통계

- **실행된 단계:** {len(self.results)}
- **성공:** {successful}
- **실패:** {failed}
- **총 소요시간:** {total_time:.1f}초

---

## 🎯 다음 단계

### 성공한 경우 ✅
1. Cleansed_Data 폴더에서 정제된 데이터 확인
2. 모델 학습 데이터로 사용 가능
3. FastAPI 서버에 데이터 로드

### 실패한 경우 ⚠️
1. 오류 메시지 확인: logs/pipeline.log
2. 개별 스크립트 재실행
3. D-드라이브 경로 및 API 키 확인

---

**상태:** {'파이프라인 정상 완료' if failed == 0 else '파이프라인 부분 실패 - 로그 확인 필요'}
"""

        summary_path = Path('docs') / f"ETL_PIPELINE_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        summary_path.parent.mkdir(parents=True, exist_ok=True)

        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary_content)

        logger.info(f"📝 보고서 생성: {summary_path}")
        logger.info(f"\n✅ 총 소요시간: {total_time:.1f}초")
        logger.info(f"✅ 성공: {successful}/{len(self.results)}")

    def run(self):
        """전체 파이프라인 실행"""
        self.start_time = time.time()

        logger.info("\n" + "="*70)
        logger.info("🚀 AVM 데이터 ETL 파이프라인 시작")
        logger.info("="*70)
        logger.info(f"시작시간: {TIMESTAMP}")
        logger.info(f"스크립트 경로: {SCRIPTS_DIR}")

        # 순차 실행
        for script_name, description in self.scripts:
            success = self.run_script(script_name, description)

            if not success:
                logger.warning(f"⚠️ {description} 실패 - 파이프라인 중단")
                # 실패해도 계속 진행하려면 주석 처리
                # break

            # 단계 간 딜레이
            time.sleep(2)

        # 요약 생성
        self.generate_summary()

        logger.info("\n" + "="*70)
        logger.info("🎊 파이프라인 완료!")
        logger.info("="*70)


if __name__ == "__main__":
    Path('logs').mkdir(exist_ok=True)
    orchestrator = PipelineOrchestrator()
    orchestrator.run()
