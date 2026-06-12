"""
Week 2 성능 테스트 & 검증 스크립트

목표:
  - p95 latency: < 100ms (현재 142ms)
  - Hit rate: 95% (현재 85%)
  - 동시성: 2000 rps (현재 1600)
  - 부하 테스트: 1000 concurrent 요청
"""

import time
import logging
import statistics
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
import random

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class PerformanceTestMetrics:
    """성능 테스트 메트릭"""

    def __init__(self):
        self.response_times: List[float] = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.errors = 0
        self.start_time = None
        self.end_time = None

    def add_response_time(self, latency_ms: float, is_cache_hit: bool = False):
        """응답 시간 기록"""
        self.response_times.append(latency_ms)
        if is_cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    def add_error(self):
        """오류 기록"""
        self.errors += 1

    def calculate_statistics(self) -> dict:
        """통계 계산"""
        if not self.response_times:
            return {}

        sorted_times = sorted(self.response_times)
        n = len(sorted_times)

        return {
            "total_requests": n,
            "success_rate": ((n - self.errors) / n * 100) if n > 0 else 0,
            "cache_hit_rate": (
                self.cache_hits / (self.cache_hits + self.cache_misses) * 100
                if (self.cache_hits + self.cache_misses) > 0
                else 0
            ),
            "mean_latency_ms": statistics.mean(sorted_times),
            "median_latency_ms": statistics.median(sorted_times),
            "stdev_latency_ms": statistics.stdev(sorted_times) if len(sorted_times) > 1 else 0,
            "min_latency_ms": sorted_times[0],
            "max_latency_ms": sorted_times[-1],
            "p50_latency_ms": sorted_times[n // 2],
            "p95_latency_ms": sorted_times[int(n * 0.95)],
            "p99_latency_ms": sorted_times[int(n * 0.99)],
            "throughput_rps": (n / (self.end_time - self.start_time))
            if (self.end_time and self.start_time)
            else 0,
            "errors": self.errors,
        }


class PerformanceTestRunner:
    """성능 테스트 실행기"""

    # 성능 목표
    TARGET_P95_LATENCY_MS = 100
    TARGET_HIT_RATE = 95
    TARGET_RPS = 2000
    TARGET_SUCCESS_RATE = 99.5

    def __init__(self, num_workers: int = 10, num_requests: int = 1000):
        self.num_workers = num_workers
        self.num_requests = num_requests
        self.metrics = PerformanceTestMetrics()

    def simulate_avm_request(self, request_id: int) -> Tuple[float, bool]:
        """
        AVM 요청 시뮬레이션

        Returns:
            (latency_ms, is_cache_hit)
        """
        try:
            # 캐시 히트 확률: 85% (목표: 95%)
            is_cache_hit = random.random() < 0.85

            # 레이턴시 시뮬레이션
            if is_cache_hit:
                # 캐시 히트: 5-15ms
                latency = random.uniform(5, 15)
            else:
                # 캐시 미스: 50-200ms (DB 쿼리 + AVM 계산)
                latency = random.uniform(50, 200)

            # 5% 확률로 느린 요청
            if random.random() < 0.05:
                latency *= 2

            return latency, is_cache_hit

        except Exception as e:
            logger.error(f"요청 {request_id} 오류: {str(e)}")
            return None, False

    def run_concurrent_load_test(self) -> dict:
        """동시 부하 테스트"""

        logger.info(f"""
🚀 ===== 성능 테스트 시작 =====
Workers: {self.num_workers}
Total Requests: {self.num_requests}
================================
        """)

        self.metrics.start_time = time.time()

        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = [
                executor.submit(self.simulate_avm_request, i)
                for i in range(self.num_requests)
            ]

            completed = 0
            for future in as_completed(futures):
                try:
                    latency, is_cache_hit = future.result()
                    if latency is not None:
                        self.metrics.add_response_time(latency, is_cache_hit)
                    else:
                        self.metrics.add_error()
                except Exception as e:
                    logger.error(f"요청 처리 오류: {str(e)}")
                    self.metrics.add_error()

                completed += 1
                if completed % 100 == 0:
                    logger.info(f"진행: {completed}/{self.num_requests}")

        self.metrics.end_time = time.time()

        return self.metrics.calculate_statistics()

    def print_results(self, stats: dict):
        """결과 출력"""

        logger.info(f"""
📊 ===== 성능 테스트 결과 =====
총 요청: {stats.get('total_requests', 0)}개
성공률: {stats.get('success_rate', 0):.2f}%
캐시 히트율: {stats.get('cache_hit_rate', 0):.2f}%

레이턴시 (ms):
  평균: {stats.get('mean_latency_ms', 0):.2f}
  중앙값: {stats.get('median_latency_ms', 0):.2f}
  표준편차: {stats.get('stdev_latency_ms', 0):.2f}
  최소: {stats.get('min_latency_ms', 0):.2f}
  최대: {stats.get('max_latency_ms', 0):.2f}

백분위수:
  P50: {stats.get('p50_latency_ms', 0):.2f}ms
  P95: {stats.get('p95_latency_ms', 0):.2f}ms ⭐ (목표: < {self.TARGET_P95_LATENCY_MS}ms)
  P99: {stats.get('p99_latency_ms', 0):.2f}ms

처리량: {stats.get('throughput_rps', 0):.2f} rps (목표: {self.TARGET_RPS} rps)
오류: {stats.get('errors', 0)}개
================================
        """)

    def check_goals(self, stats: dict) -> Dict[str, bool]:
        """목표 달성 여부 확인"""

        goals = {
            "p95_latency": stats.get("p95_latency_ms", 0) < self.TARGET_P95_LATENCY_MS,
            "hit_rate": stats.get("cache_hit_rate", 0) >= self.TARGET_HIT_RATE,
            "throughput": stats.get("throughput_rps", 0) >= self.TARGET_RPS,
            "success_rate": stats.get("success_rate", 0) >= self.TARGET_SUCCESS_RATE,
        }

        logger.info(f"""
✅ ===== 목표 달성 현황 =====
P95 레이턴시: {stats.get('p95_latency_ms', 0):.2f}ms < {self.TARGET_P95_LATENCY_MS}ms ✓ {
    "✅" if goals["p95_latency"] else "❌"}
캐시 히트율: {stats.get('cache_hit_rate', 0):.2f}% ≥ {self.TARGET_HIT_RATE}% {
    "✅" if goals["hit_rate"] else "❌"}
처리량: {stats.get('throughput_rps', 0):.2f} rps ≥ {self.TARGET_RPS} rps {
    "✅" if goals["throughput"] else "❌"}
성공률: {stats.get('success_rate', 0):.2f}% ≥ {self.TARGET_SUCCESS_RATE}% {
    "✅" if goals["success_rate"] else "❌"}
============================
        """)

        return goals

    def save_results(self, stats: dict, goals: dict, filename: str = None):
        """결과 저장"""

        if filename is None:
            filename = f"performance_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        result = {
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "num_workers": self.num_workers,
                "num_requests": self.num_requests,
            },
            "metrics": stats,
            "goals": {
                "p95_latency": goals.get("p95_latency"),
                "hit_rate": goals.get("hit_rate"),
                "throughput": goals.get("throughput"),
                "success_rate": goals.get("success_rate"),
            },
            "summary": {
                "all_goals_met": all(goals.values()),
                "goals_met": sum(goals.values()),
                "total_goals": len(goals),
            },
        }

        with open(filename, "w") as f:
            json.dump(result, f, indent=2)

        logger.info(f"✅ 결과 저장: {filename}")


def main():
    """메인 테스트 함수"""

    # 테스트 1: 기본 부하 테스트 (500 요청, 10 workers)
    logger.info("=" * 60)
    logger.info("테스트 1: 기본 부하 테스트")
    logger.info("=" * 60)

    test1 = PerformanceTestRunner(num_workers=10, num_requests=500)
    stats1 = test1.run_concurrent_load_test()
    test1.print_results(stats1)
    goals1 = test1.check_goals(stats1)
    test1.save_results(stats1, goals1, "test1_basic_load.json")

    # 테스트 2: 고부하 테스트 (1000 요청, 50 workers - 높은 동시성)
    logger.info("=" * 60)
    logger.info("테스트 2: 고부하 테스트 (높은 동시성)")
    logger.info("=" * 60)

    test2 = PerformanceTestRunner(num_workers=50, num_requests=1000)
    stats2 = test2.run_concurrent_load_test()
    test2.print_results(stats2)
    goals2 = test2.check_goals(stats2)
    test2.save_results(stats2, goals2, "test2_high_concurrency.json")

    # 테스트 3: 극한 테스트 (2000 요청, 100 workers)
    logger.info("=" * 60)
    logger.info("테스트 3: 극한 테스트")
    logger.info("=" * 60)

    test3 = PerformanceTestRunner(num_workers=100, num_requests=2000)
    stats3 = test3.run_concurrent_load_test()
    test3.print_results(stats3)
    goals3 = test3.check_goals(stats3)
    test3.save_results(stats3, goals3, "test3_extreme_load.json")

    # 최종 평가
    all_passed = all(
        [
            all(goals1.values()),
            all(goals2.values()),
            all(goals3.values()),
        ]
    )

    logger.info(f"""
🎯 ===== 최종 평가 =====
테스트 1 (기본): {'✅ PASS' if all(goals1.values()) else '❌ FAIL'}
테스트 2 (고부하): {'✅ PASS' if all(goals2.values()) else '❌ FAIL'}
테스트 3 (극한): {'✅ PASS' if all(goals3.values()) else '❌ FAIL'}

전체 결과: {'✅ 모든 목표 달성' if all_passed else '⚠️ 일부 목표 미달'}
========================
    """)


if __name__ == "__main__":
    main()
