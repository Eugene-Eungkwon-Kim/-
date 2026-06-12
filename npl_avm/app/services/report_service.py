import logging
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from app.db.models import Property, Appraisal, Auction, Deal
from app.models.report_models import (
    ReportTemplate,
    ReportExecution,
    ReportResult,
)

logger = logging.getLogger(__name__)


class ReportService:
    """리포트 서비스"""

    @staticmethod
    def create_template(
        db: Session,
        name: str,
        description: Optional[str] = None,
        filters: Optional[Dict] = None,
        grouping: Optional[str] = None,
        aggregations: Optional[List[Dict]] = None,
        schedule: Optional[str] = None,
        notify_slack: bool = False,
        notify_email: bool = False,
        webhook_url: Optional[str] = None,
    ) -> ReportTemplate:
        """리포트 템플릿 생성"""
        template = ReportTemplate(
            name=name,
            description=description,
            filters=filters or {},
            grouping=grouping,
            aggregations=aggregations or [],
            schedule=schedule,
            notify_slack=notify_slack,
            notify_email=notify_email,
            webhook_url=webhook_url,
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        logger.info(f"리포트 템플릿 생성: {name} (ID: {template.id})")
        return template

    @staticmethod
    def get_template(db: Session, template_id: int) -> Optional[ReportTemplate]:
        """리포트 템플릿 조회"""
        return db.query(ReportTemplate).filter(ReportTemplate.id == template_id).first()

    @staticmethod
    def list_templates(
        db: Session,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[ReportTemplate], int]:
        """리포트 템플릿 목록 조회"""
        query = db.query(ReportTemplate)
        total = query.count()
        templates = query.order_by(ReportTemplate.created_at.desc()).offset(offset).limit(limit).all()
        return templates, total

    @staticmethod
    def update_template(
        db: Session,
        template_id: int,
        **kwargs
    ) -> Optional[ReportTemplate]:
        """리포트 템플릿 수정"""
        template = ReportService.get_template(db, template_id)
        if not template:
            return None

        for key, value in kwargs.items():
            if hasattr(template, key):
                setattr(template, key, value)

        template.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(template)
        logger.info(f"리포트 템플릿 수정: {template.name} (ID: {template.id})")
        return template

    @staticmethod
    def delete_template(db: Session, template_id: int) -> bool:
        """리포트 템플릿 삭제"""
        template = ReportService.get_template(db, template_id)
        if not template:
            return False

        db.delete(template)
        db.commit()
        logger.info(f"리포트 템플릿 삭제: {template.name} (ID: {template.id})")
        return True

    @staticmethod
    def execute_template(
        db: Session,
        template_id: int,
    ) -> Optional[Dict[str, Any]]:
        """리포트 템플릿 실행"""
        template = ReportService.get_template(db, template_id)
        if not template:
            return None

        start_time = datetime.utcnow()
        execution = ReportExecution(
            template_id=template_id,
            status="running",
        )
        db.add(execution)
        db.commit()

        try:
            # 데이터 조회
            query = db.query(Property, Appraisal, Auction, Deal)
            query = query.outerjoin(
                Appraisal, Appraisal.property_id == Property.id
            )
            query = query.outerjoin(
                Deal, Deal.id == Appraisal.deal_id
            )
            query = query.outerjoin(
                Auction, Auction.id == Deal.auction_id
            )

            # 필터 적용
            if template.filters:
                for field, conditions in template.filters.items():
                    operator = conditions.get("operator", "eq")
                    value = conditions.get("value")

                    if hasattr(Property, field):
                        column = getattr(Property, field)
                        if operator == "eq":
                            query = query.filter(column == value)
                        elif operator == "in":
                            query = query.filter(column.in_(value))
                        elif operator == "between":
                            query = query.filter(
                                column.between(value[0], value[1])
                            )

            results = query.all()

            # 결과 데이터 변환
            data = []
            for prop, appraisal, auction, deal in results:
                data.append({
                    "property_id": prop.id,
                    "address": f"{prop.address_sido} {prop.address_sigungu}",
                    "property_type": prop.property_type,
                    "building_area": prop.building_area,
                    "appraisal_value": appraisal.appraisal_value if appraisal else None,
                    "hammer_price": auction.hammer_price if auction else None,
                    "hammer_rate": auction.hammer_rate if auction else None,
                })

            # 그룹핑 및 집계
            if template.grouping and data:
                data = ReportService._apply_grouping_and_aggregation(
                    data,
                    template.grouping,
                    template.aggregations,
                )

            # 실행 기록 저장
            execution_time_ms = (
                datetime.utcnow() - start_time
            ).total_seconds() * 1000

            execution.status = "success"
            execution.rows_processed = len(results)
            execution.execution_time_ms = execution_time_ms

            # 결과 저장
            report_result = ReportResult(
                template_id=template_id,
                execution_id=execution.id,
                data=data,
            )
            db.add(report_result)
            db.commit()

            logger.info(
                f"리포트 실행 완료: {template.name}, "
                f"행: {len(results)}, "
                f"시간: {execution_time_ms:.0f}ms"
            )

            return {
                "template_id": template_id,
                "execution_id": execution.id,
                "status": "success",
                "rows_processed": len(results),
                "execution_time_ms": execution_time_ms,
                "data": data,
            }

        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            db.commit()

            logger.error(f"리포트 실행 실패: {template.name}, {str(e)}")
            raise

    @staticmethod
    def _apply_grouping_and_aggregation(
        data: List[Dict[str, Any]],
        grouping_field: str,
        aggregations: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """그룹핑 및 집계 적용"""
        from itertools import groupby

        # 그룹핑 필드로 정렬
        sorted_data = sorted(data, key=lambda x: x.get(grouping_field))

        result = []
        for group_key, group_items in groupby(
            sorted_data,
            key=lambda x: x.get(grouping_field)
        ):
            group_list = list(group_items)
            group_result = {grouping_field: group_key}

            # 집계 함수 적용
            for agg in aggregations:
                field = agg.get("field")
                func = agg.get("func")  # "sum", "avg", "count", "min", "max"

                values = [item.get(field) for item in group_list if item.get(field)]

                if func == "sum":
                    group_result[f"{field}_sum"] = sum(values)
                elif func == "avg":
                    group_result[f"{field}_avg"] = sum(values) / len(values) if values else 0
                elif func == "count":
                    group_result[f"{field}_count"] = len(values)
                elif func == "min":
                    group_result[f"{field}_min"] = min(values) if values else None
                elif func == "max":
                    group_result[f"{field}_max"] = max(values) if values else None

            result.append(group_result)

        return result

    @staticmethod
    def get_execution_history(
        db: Session,
        template_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[ReportExecution]:
        """실행 히스토리 조회"""
        query = db.query(ReportExecution)

        if template_id:
            query = query.filter(ReportExecution.template_id == template_id)

        return (
            query.order_by(ReportExecution.executed_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_execution_result(
        db: Session,
        execution_id: int,
    ) -> Optional[ReportResult]:
        """실행 결과 조회"""
        return (
            db.query(ReportResult)
            .filter(ReportResult.execution_id == execution_id)
            .first()
        )


report_service = ReportService()
