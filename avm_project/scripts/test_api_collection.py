"""
AVM 프로젝트 - Data.go.kr API 테스트 및 데이터 수집 시작
Test Korean Real Estate Data Collection with API Key
"""

import sys
sys.path.insert(0, '/home/user/-')

from avm_project.scripts.data_collection_handler import KoreanRealEstateDataCollector
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API 키 설정
API_KEY = '9+Sz4Yn+RoH4bEhkrqfzS+AJz9ldaehP57wEhL3sEKmDMZW5t7UnTs7rPOA3BNcczF8AI/OX0YJ51PmPAAEZFw=='

def main():
    print("\n" + "="*70)
    print("AVM 프로젝트 - 한국 부동산 데이터 수집 시작")
    print("="*70)

    # 수집기 초기화
    collector = KoreanRealEstateDataCollector(
        api_key=API_KEY,
        output_dir='avm_project/data/raw'
    )

    print("\n✅ API 키 설정 완료")
    print(f"API 키 확인: {API_KEY[:20]}...***")

    # 데이터 수집 가이드 생성
    print("\n📋 데이터 수집 가이드 생성 중...")
    guide_path = collector.generate_data_collection_guide()
    print(f"✅ 가이드 생성 완료: {guide_path}")

    # 부동산 실거래 데이터 수집 테스트 (2024년 6월 데이터)
    print("\n📊 부동산 실거래 데이터 수집 시작...")
    print("   (월별로 처리됨 - 시간이 소요될 수 있습니다)")

    try:
        df = collector.collect_real_estate_transaction_data(
            start_date='202406',
            end_date='202406'  # 2024년 6월만 테스트
        )

        if len(df) > 0:
            print(f"\n✅ 부동산 실거래 데이터 수집 완료!")
            print(f"   - 수집 건수: {len(df)}개")
            print(f"   - 컬럼 수: {len(df.columns)}개")
            print(f"   - 저장 위치: avm_project/data/raw/")

            # 데이터 미리보기
            print("\n📈 데이터 샘플 (처음 5개 행):")
            print(df.head().to_string())

            print("\n📋 컬럼 목록:")
            for i, col in enumerate(df.columns, 1):
                print(f"   {i}. {col}")

        else:
            print("⚠️ 데이터가 수집되지 않았습니다.")
            print("   - API 키 확인")
            print("   - API 요청 제한 확인")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print("\n📝 트러블슈팅:")
        print("   1. API 키 확인")
        print("   2. 네트워크 연결 확인")
        print("   3. Data.go.kr API 상태 확인")

    print("\n" + "="*70)
    print("다음 단계:")
    print("="*70)
    print("""
1. 생성된 가이드 검토
   위치: avm_project/docs/KOREAN_REAL_ESTATE_DATA_COLLECTION.md

2. 추가 데이터 수집
   - 전월세 데이터
   - 공시지가 데이터
   - 기타 통계

3. 자동 루프 설정
   - 매주 목요일 10:00 자동 실행
   - Cron job 또는 스케줄러 설정

4. Phase 2 모델 개발 준비
   - 수집된 데이터로 모델 학습
   - 예측 모델 구축
    """)

if __name__ == '__main__':
    main()
