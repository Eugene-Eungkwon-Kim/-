"""RAG 결과에 대한 신뢰도 점수 산정.

유사 사례 수·평균 유사도와 모델 정확도(MAPE)를 결합해 0~100점 신뢰도와
근거 문장을 만든다. 외부 서비스(DB, Milvus, OpenAI)에 의존하지 않아
그것들이 전부 죽어도 항상 응답한다 — routes_rag.py 가 RAG 처리 실패 시
`similar_cases=[]` 로 이 클래스를 호출하는 것도 그 전제 위에 설계되어
있다.
"""

from typing import Any, Dict, List


class ConfidenceScorer:
    def score(
        self,
        hammer_rate: float,
        similar_cases: List[Dict[str, Any]],
        mape: float,
        comparables_count: int,
    ) -> Dict[str, Any]:
        reasons: List[str] = []
        points = 100

        if comparables_count == 0:
            points -= 40
            reasons.append("유사 사례를 찾지 못함")
        elif comparables_count < 3:
            points -= 20
            reasons.append(f"유사 사례가 {comparables_count}건으로 적음")
        else:
            reasons.append(f"유사 사례 {comparables_count}건 확보")

        avg_similarity = (
            sum(c.get("similarity", 0.0) for c in similar_cases) / len(similar_cases)
            if similar_cases else 0.0
        )
        if similar_cases and avg_similarity < 0.5:
            points -= 20
            reasons.append(f"평균 유사도 {avg_similarity:.0%}로 낮음")
        elif similar_cases and avg_similarity >= 0.8:
            reasons.append(f"평균 유사도 {avg_similarity:.0%}로 높음")

        if mape > 15:
            points -= 20
            reasons.append(f"모델 오차율(MAPE) {mape}%로 높음")
        elif mape <= 10:
            reasons.append(f"모델 오차율(MAPE) {mape}%로 양호")

        if not (0.5 <= hammer_rate <= 1.3):
            points -= 10
            reasons.append(f"낙찰가율 {hammer_rate:.2f}이 통상 범위를 벗어남")

        score = max(0, min(100, points))
        return {"score": score, "level": self._level(score), "reasons": reasons}

    @staticmethod
    def _level(score: int) -> str:
        if score >= 85:
            return "매우높음"
        if score >= 70:
            return "높음"
        if score >= 50:
            return "중간"
        if score >= 30:
            return "낮음"
        return "매우낮음"
