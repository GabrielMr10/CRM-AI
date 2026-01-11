"""
Service - Lógica de negócio.
"""
import uuid

from sqlalchemy.orm import Session

from app.modules.pipeline.models import Pipeline, Stage, Deal
from app.modules.pipeline.schemas import (
    PipelineCreate, PipelineUpdate, PipelineResponse, PipelineWithStages,
    StageCreate, StageUpdate, StageResponse,
    DealCreate, DealUpdate, DealResponse, DealListResponse,
    KanbanView, KanbanStage,
)
from app.modules.pipeline.repository import PipelineRepository, StageRepository, DealRepository
from app.modules.pipeline.exceptions import (
    PipelineNotFoundError,
    StageNotFoundError,
    DealNotFoundError,
    CannotDeleteDefaultPipelineError,
    CannotDeleteStageWithDealsError,
)
from app.modules.users.models import User


class PipelineService:
    
    @staticmethod
    def get_or_404(db: Session, pipeline_id: uuid.UUID, tenant_id: uuid.UUID) -> Pipeline:
        pipeline = PipelineRepository.get_by_id_and_tenant(db, pipeline_id, tenant_id)
        if not pipeline:
            raise PipelineNotFoundError(str(pipeline_id))
        return pipeline
    
    @staticmethod
    def list_all(db: Session, tenant_id: uuid.UUID, is_active: bool | None = None) -> list[PipelineResponse]:
        pipelines = PipelineRepository.get_all(db, tenant_id, is_active=is_active)
        return [PipelineResponse.model_validate(p) for p in pipelines]
    
    @staticmethod
    def get_with_stages(db: Session, pipeline_id: uuid.UUID, tenant_id: uuid.UUID) -> PipelineWithStages:
        pipeline = PipelineService.get_or_404(db, pipeline_id, tenant_id)
        stages = StageRepository.get_by_pipeline(db, pipeline_id)
        
        return PipelineWithStages(
            **PipelineResponse.model_validate(pipeline).model_dump(),
            stages=[StageResponse.model_validate(s) for s in stages],
        )
    
    @staticmethod
    def create(db: Session, *, data: PipelineCreate, tenant_id: uuid.UUID) -> Pipeline:
        # Se for default, remove flag dos outros
        if data.is_default:
            PipelineRepository.unset_default(db, tenant_id)
        
        pipeline = PipelineRepository.create(db, data=data, tenant_id=tenant_id)
        
        # Criar stages padrão
        default_stages = [
            StageCreate(name="Novo", position=0, color="#3B82F6", auto_probability=10),
            StageCreate(name="Em contato", position=1, color="#F59E0B", auto_probability=30),
            StageCreate(name="Proposta", position=2, color="#8B5CF6", auto_probability=60),
            StageCreate(name="Negociação", position=3, color="#EC4899", auto_probability=80),
            StageCreate(name="Fechado", position=4, color="#10B981", is_won=True, auto_probability=100),
            StageCreate(name="Perdido", position=5, color="#EF4444", is_lost=True, auto_probability=0),
        ]
        
        for stage_data in default_stages:
            StageRepository.create(db, data=stage_data, pipeline_id=pipeline.id)
        
        return pipeline
    
    @staticmethod
    def create_default_pipeline(db: Session, tenant_id: uuid.UUID) -> Pipeline:
        """Cria pipeline padrão para novo tenant."""
        data = PipelineCreate(
            name="Pipeline Principal",
            description="Pipeline padrão de vendas",
            is_default=True,
        )
        return PipelineService.create(db, data=data, tenant_id=tenant_id)
    
    @staticmethod
    def update(
        db: Session,
        *,
        pipeline_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: PipelineUpdate,
    ) -> Pipeline:
        pipeline = PipelineService.get_or_404(db, pipeline_id, tenant_id)
        
        if data.is_default:
            PipelineRepository.unset_default(db, tenant_id)
        
        return PipelineRepository.update(db, pipeline=pipeline, data=data)
    
    @staticmethod
    def delete(db: Session, *, pipeline_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        pipeline = PipelineService.get_or_404(db, pipeline_id, tenant_id)
        
        if pipeline.is_default:
            raise CannotDeleteDefaultPipelineError()
        
        PipelineRepository.delete(db, pipeline=pipeline)


class StageService:
    
    @staticmethod
    def get_or_404(db: Session, stage_id: uuid.UUID) -> Stage:
        stage = StageRepository.get_by_id(db, stage_id)
        if not stage:
            raise StageNotFoundError(str(stage_id))
        return stage
    
    @staticmethod
    def list_by_pipeline(db: Session, pipeline_id: uuid.UUID) -> list[StageResponse]:
        stages = StageRepository.get_by_pipeline(db, pipeline_id)
        return [StageResponse.model_validate(s) for s in stages]
    
    @staticmethod
    def create(
        db: Session,
        *,
        data: StageCreate,
        pipeline_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Stage:
        # Verificar se pipeline pertence ao tenant
        PipelineService.get_or_404(db, pipeline_id, tenant_id)
        
        # Posição automática se não informada
        if data.position == 0:
            data.position = StageRepository.get_max_position(db, pipeline_id) + 1
        
        return StageRepository.create(db, data=data, pipeline_id=pipeline_id)
    
    @staticmethod
    def update(
        db: Session,
        *,
        stage_id: uuid.UUID,
        data: StageUpdate,
    ) -> Stage:
        stage = StageService.get_or_404(db, stage_id)
        return StageRepository.update(db, stage=stage, data=data)
    
    @staticmethod
    def reorder(
        db: Session,
        *,
        pipeline_id: uuid.UUID,
        tenant_id: uuid.UUID,
        stage_ids: list[uuid.UUID],
    ) -> list[StageResponse]:
        PipelineService.get_or_404(db, pipeline_id, tenant_id)
        StageRepository.reorder(db, pipeline_id, stage_ids)
        return StageService.list_by_pipeline(db, pipeline_id)
    
    @staticmethod
    def delete(db: Session, *, stage_id: uuid.UUID) -> None:
        stage = StageService.get_or_404(db, stage_id)
        
        # Verificar se tem deals
        deals_count = StageRepository.count_deals(db, stage_id)
        if deals_count > 0:
            raise CannotDeleteStageWithDealsError()
        
        StageRepository.delete(db, stage=stage)


class DealService:
    
    @staticmethod
    def get_or_404(db: Session, deal_id: uuid.UUID, tenant_id: uuid.UUID) -> Deal:
        deal = DealRepository.get_by_id_and_tenant(db, deal_id, tenant_id)
        if not deal:
            raise DealNotFoundError(str(deal_id))
        return deal
    
    @staticmethod
    def create(
        db: Session,
        *,
        data: DealCreate,
        pipeline_id: uuid.UUID,
        tenant_id: uuid.UUID,
        created_by: User | None = None,
    ) -> Deal:
        # Verificar se stage pertence ao pipeline
        stage = StageService.get_or_404(db, data.stage_id)
        if stage.pipeline_id != pipeline_id:
            raise StageNotFoundError(str(data.stage_id))
        
        # Auto-probability do stage
        if data.probability == 0 and stage.auto_probability:
            data.probability = stage.auto_probability
        
        return DealRepository.create(
            db,
            data=data,
            tenant_id=tenant_id,
            pipeline_id=pipeline_id,
            created_by_id=created_by.id if created_by else None,
        )
    
    @staticmethod
    def update(
        db: Session,
        *,
        deal_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: DealUpdate,
    ) -> Deal:
        deal = DealService.get_or_404(db, deal_id, tenant_id)
        return DealRepository.update(db, deal=deal, data=data)
    
    @staticmethod
    def move(
        db: Session,
        *,
        deal_id: uuid.UUID,
        tenant_id: uuid.UUID,
        stage_id: uuid.UUID,
        position: int = 0,
    ) -> Deal:
        deal = DealService.get_or_404(db, deal_id, tenant_id)
        stage = StageService.get_or_404(db, stage_id)
        
        # Auto-atualizar probabilidade
        if stage.auto_probability is not None:
            deal.probability = stage.auto_probability
        
        # Auto-marcar como won/lost
        if stage.is_won:
            return DealRepository.mark_won(db, deal=deal)
        elif stage.is_lost:
            return DealRepository.mark_lost(db, deal=deal)
        
        return DealRepository.move(db, deal=deal, stage_id=stage_id, position=position)
    
    @staticmethod
    def mark_won(db: Session, *, deal_id: uuid.UUID, tenant_id: uuid.UUID) -> Deal:
        deal = DealService.get_or_404(db, deal_id, tenant_id)
        return DealRepository.mark_won(db, deal=deal)
    
    @staticmethod
    def mark_lost(
        db: Session,
        *,
        deal_id: uuid.UUID,
        tenant_id: uuid.UUID,
        reason: str | None = None,
    ) -> Deal:
        deal = DealService.get_or_404(db, deal_id, tenant_id)
        return DealRepository.mark_lost(db, deal=deal, reason=reason)
    
    @staticmethod
    def delete(db: Session, *, deal_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        deal = DealService.get_or_404(db, deal_id, tenant_id)
        DealRepository.delete(db, deal=deal)
    
    @staticmethod
    def get_kanban(db: Session, pipeline_id: uuid.UUID, tenant_id: uuid.UUID) -> KanbanView:
        """Monta visão Kanban completa."""
        pipeline = PipelineService.get_or_404(db, pipeline_id, tenant_id)
        stages = StageRepository.get_by_pipeline(db, pipeline_id)
        
        kanban_stages = []
        total_deals = 0
        total_value = 0.0
        weighted_value = 0.0
        
        for stage in stages:
            deals = DealRepository.get_by_stage(db, stage.id)
            stage_value = sum(d.value for d in deals)
            stage_weighted = sum(d.weighted_value for d in deals)
            
            kanban_stages.append(KanbanStage(
                id=stage.id,
                name=stage.name,
                position=stage.position,
                color=stage.color,
                is_won=stage.is_won,
                is_lost=stage.is_lost,
                deals=[DealResponse.model_validate(d) for d in deals],
                deals_count=len(deals),
                deals_value=stage_value,
            ))
            
            if not stage.is_won and not stage.is_lost:
                total_deals += len(deals)
                total_value += stage_value
                weighted_value += stage_weighted
        
        return KanbanView(
            pipeline=PipelineResponse.model_validate(pipeline),
            stages=kanban_stages,
            total_deals=total_deals,
            total_value=total_value,
            weighted_value=weighted_value,
        )