"""
Repository - Queries do banco de dados.
"""
import uuid
from typing import Sequence
from datetime import datetime, timezone

from sqlalchemy import select, func, and_, update
from sqlalchemy.orm import Session, selectinload

from app.modules.pipeline.models import Pipeline, Stage, Deal
from app.modules.pipeline.schemas import (
    PipelineCreate, PipelineUpdate,
    StageCreate, StageUpdate,
    DealCreate, DealUpdate,
)


class PipelineRepository:
    
    @staticmethod
    def get_by_id(db: Session, pipeline_id: uuid.UUID) -> Pipeline | None:
        return db.get(Pipeline, pipeline_id)
    
    @staticmethod
    def get_by_id_with_stages(db: Session, pipeline_id: uuid.UUID) -> Pipeline | None:
        stmt = (
            select(Pipeline)
            .options(selectinload(Pipeline.stages))
            .where(Pipeline.id == pipeline_id)
        )
        return db.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_by_id_and_tenant(
        db: Session,
        pipeline_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Pipeline | None:
        stmt = select(Pipeline).where(
            and_(Pipeline.id == pipeline_id, Pipeline.tenant_id == tenant_id)
        )
        return db.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_default(db: Session, tenant_id: uuid.UUID) -> Pipeline | None:
        stmt = select(Pipeline).where(
            and_(Pipeline.tenant_id == tenant_id, Pipeline.is_default == True)
        )
        return db.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_all(
        db: Session,
        tenant_id: uuid.UUID,
        *,
        is_active: bool | None = None,
    ) -> Sequence[Pipeline]:
        stmt = (
            select(Pipeline)
            .where(Pipeline.tenant_id == tenant_id)
            .order_by(Pipeline.created_at)
        )
        
        if is_active is not None:
            stmt = stmt.where(Pipeline.is_active == is_active)
        
        return db.execute(stmt).scalars().all()
    
    @staticmethod
    def create(
        db: Session,
        *,
        data: PipelineCreate,
        tenant_id: uuid.UUID,
    ) -> Pipeline:
        pipeline = Pipeline(
            **data.model_dump(),
            tenant_id=tenant_id,
        )
        
        db.add(pipeline)
        db.commit()
        db.refresh(pipeline)
        
        return pipeline
    
    @staticmethod
    def update(db: Session, *, pipeline: Pipeline, data: PipelineUpdate) -> Pipeline:
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(pipeline, field, value)
        
        db.commit()
        db.refresh(pipeline)
        
        return pipeline
    
    @staticmethod
    def delete(db: Session, *, pipeline: Pipeline) -> None:
        db.delete(pipeline)
        db.commit()
    
    @staticmethod
    def unset_default(db: Session, tenant_id: uuid.UUID) -> None:
        """Remove flag de default de todos os pipelines do tenant."""
        stmt = (
            update(Pipeline)
            .where(Pipeline.tenant_id == tenant_id)
            .values(is_default=False)
        )
        db.execute(stmt)
        db.commit()


class StageRepository:
    
    @staticmethod
    def get_by_id(db: Session, stage_id: uuid.UUID) -> Stage | None:
        return db.get(Stage, stage_id)
    
    @staticmethod
    def get_by_pipeline(db: Session, pipeline_id: uuid.UUID) -> Sequence[Stage]:
        stmt = (
            select(Stage)
            .where(Stage.pipeline_id == pipeline_id)
            .order_by(Stage.position)
        )
        return db.execute(stmt).scalars().all()
    
    @staticmethod
    def get_max_position(db: Session, pipeline_id: uuid.UUID) -> int:
        stmt = select(func.max(Stage.position)).where(Stage.pipeline_id == pipeline_id)
        result = db.execute(stmt).scalar_one_or_none()
        return result or 0
    
    @staticmethod
    def count_deals(db: Session, stage_id: uuid.UUID) -> int:
        stmt = select(func.count(Deal.id)).where(Deal.stage_id == stage_id)
        return db.execute(stmt).scalar_one()
    
    @staticmethod
    def create(
        db: Session,
        *,
        data: StageCreate,
        pipeline_id: uuid.UUID,
    ) -> Stage:
        stage = Stage(
            **data.model_dump(),
            pipeline_id=pipeline_id,
        )
        
        db.add(stage)
        db.commit()
        db.refresh(stage)
        
        return stage
    
    @staticmethod
    def update(db: Session, *, stage: Stage, data: StageUpdate) -> Stage:
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(stage, field, value)
        
        db.commit()
        db.refresh(stage)
        
        return stage
    
    @staticmethod
    def reorder(db: Session, pipeline_id: uuid.UUID, stage_ids: list[uuid.UUID]) -> None:
        """Reordena stages pela lista de IDs."""
        for position, stage_id in enumerate(stage_ids):
            stmt = (
                update(Stage)
                .where(and_(Stage.id == stage_id, Stage.pipeline_id == pipeline_id))
                .values(position=position)
            )
            db.execute(stmt)
        db.commit()
    
    @staticmethod
    def delete(db: Session, *, stage: Stage) -> None:
        db.delete(stage)
        db.commit()


class DealRepository:
    
    @staticmethod
    def get_by_id(db: Session, deal_id: uuid.UUID) -> Deal | None:
        return db.get(Deal, deal_id)
    
    @staticmethod
    def get_by_id_and_tenant(
        db: Session,
        deal_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Deal | None:
        stmt = select(Deal).where(
            and_(Deal.id == deal_id, Deal.tenant_id == tenant_id)
        )
        return db.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_by_pipeline(
        db: Session,
        pipeline_id: uuid.UUID,
        *,
        include_closed: bool = False,
    ) -> Sequence[Deal]:
        stmt = (
            select(Deal)
            .where(Deal.pipeline_id == pipeline_id)
            .order_by(Deal.position)
        )
        
        if not include_closed:
            stmt = stmt.where(and_(Deal.is_won == False, Deal.is_lost == False))
        
        return db.execute(stmt).scalars().all()
    
    @staticmethod
    def get_by_stage(db: Session, stage_id: uuid.UUID) -> Sequence[Deal]:
        stmt = (
            select(Deal)
            .where(Deal.stage_id == stage_id)
            .order_by(Deal.position)
        )
        return db.execute(stmt).scalars().all()
    
    @staticmethod
    def get_by_lead(db: Session, lead_id: uuid.UUID) -> Sequence[Deal]:
        stmt = select(Deal).where(Deal.lead_id == lead_id)
        return db.execute(stmt).scalars().all()
    
    @staticmethod
    def create(
        db: Session,
        *,
        data: DealCreate,
        tenant_id: uuid.UUID,
        pipeline_id: uuid.UUID,
        created_by_id: uuid.UUID | None = None,
    ) -> Deal:
        deal = Deal(
            **data.model_dump(),
            tenant_id=tenant_id,
            pipeline_id=pipeline_id,
            created_by_id=created_by_id,
        )
        
        db.add(deal)
        db.commit()
        db.refresh(deal)
        
        return deal
    
    @staticmethod
    def update(db: Session, *, deal: Deal, data: DealUpdate) -> Deal:
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(deal, field, value)
        
        db.commit()
        db.refresh(deal)
        
        return deal
    
    @staticmethod
    def move(db: Session, *, deal: Deal, stage_id: uuid.UUID, position: int) -> Deal:
        deal.stage_id = stage_id
        deal.position = position
        db.commit()
        db.refresh(deal)
        return deal
    
    @staticmethod
    def mark_won(db: Session, *, deal: Deal) -> Deal:
        deal.is_won = True
        deal.is_lost = False
        deal.won_at = datetime.now(timezone.utc)
        deal.probability = 100
        db.commit()
        db.refresh(deal)
        return deal
    
    @staticmethod
    def mark_lost(db: Session, *, deal: Deal, reason: str | None = None) -> Deal:
        deal.is_lost = True
        deal.is_won = False
        deal.lost_at = datetime.now(timezone.utc)
        deal.lost_reason = reason
        deal.probability = 0
        db.commit()
        db.refresh(deal)
        return deal
    
    @staticmethod
    def delete(db: Session, *, deal: Deal) -> None:
        db.delete(deal)
        db.commit()
    
    @staticmethod
    def get_stats(db: Session, pipeline_id: uuid.UUID) -> dict:
        """Estatísticas do pipeline."""
        # Total e valor
        stmt_total = select(
            func.count(Deal.id),
            func.coalesce(func.sum(Deal.value), 0),
        ).where(
            and_(Deal.pipeline_id == pipeline_id, Deal.is_won == False, Deal.is_lost == False)
        )
        total, total_value = db.execute(stmt_total).one()
        
        # Valor ponderado
        stmt_weighted = select(
            func.coalesce(func.sum(Deal.value * Deal.probability / 100), 0)
        ).where(
            and_(Deal.pipeline_id == pipeline_id, Deal.is_won == False, Deal.is_lost == False)
        )
        weighted = db.execute(stmt_weighted).scalar_one()
        
        # Ganhos
        stmt_won = select(
            func.count(Deal.id),
            func.coalesce(func.sum(Deal.value), 0),
        ).where(
            and_(Deal.pipeline_id == pipeline_id, Deal.is_won == True)
        )
        won_count, won_value = db.execute(stmt_won).one()
        
        return {
            "total_deals": total,
            "total_value": float(total_value),
            "weighted_value": float(weighted),
            "won_count": won_count,
            "won_value": float(won_value),
        }