"""
Router - Endpoints HTTP do módulo Pipeline.
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.modules.pipeline.schemas import (
    PipelineCreate, PipelineUpdate, PipelineResponse, PipelineWithStages,
    StageCreate, StageUpdate, StageResponse, StageReorder,
    DealCreate, DealUpdate, DealResponse, DealMove, DealLost,
    KanbanView,
)
from app.modules.pipeline.service import PipelineService, StageService, DealService
from app.modules.tenants.dependencies import CurrentTenant
from app.modules.users.models import User

router = APIRouter()


# ==================== PIPELINES ====================

@router.get("/", response_model=list[PipelineResponse], summary="Listar pipelines")
def list_pipelines(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
    is_active: bool | None = None,
):
    return PipelineService.list_all(db, tenant.id, is_active=is_active)


@router.post("/", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED, summary="Criar pipeline")
def create_pipeline(
    data: PipelineCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
):
    return PipelineService.create(db, data=data, tenant_id=tenant.id)


@router.get("/{pipeline_id}", response_model=PipelineWithStages, summary="Detalhe do pipeline")
def get_pipeline(
    pipeline_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
):
    return PipelineService.get_with_stages(db, pipeline_id, tenant.id)


@router.get("/{pipeline_id}/kanban", response_model=KanbanView, summary="Visão Kanban")
def get_kanban(
    pipeline_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
):
    return DealService.get_kanban(db, pipeline_id, tenant.id)


@router.patch("/{pipeline_id}", response_model=PipelineResponse, summary="Atualizar pipeline")
def update_pipeline(
    pipeline_id: uuid.UUID,
    data: PipelineUpdate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
):
    return PipelineService.update(db, pipeline_id=pipeline_id, tenant_id=tenant.id, data=data)


@router.delete("/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deletar pipeline")
def delete_pipeline(
    pipeline_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
):
    PipelineService.delete(db, pipeline_id=pipeline_id, tenant_id=tenant.id)
    return None


# ==================== STAGES ====================

@router.get("/{pipeline_id}/stages", response_model=list[StageResponse], summary="Listar stages")
def list_stages(
    pipeline_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
):
    PipelineService.get_or_404(db, pipeline_id, tenant.id)
    return StageService.list_by_pipeline(db, pipeline_id)


@router.post("/{pipeline_id}/stages", response_model=StageResponse, status_code=status.HTTP_201_CREATED, summary="Criar stage")
def create_stage(
    pipeline_id: uuid.UUID,
    data: StageCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
):
    return StageService.create(db, data=data, pipeline_id=pipeline_id, tenant_id=tenant.id)


@router.put("/{pipeline_id}/stages/reorder", response_model=list[StageResponse], summary="Reordenar stages")
def reorder_stages(
    pipeline_id: uuid.UUID,
    data: StageReorder,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
):
    return StageService.reorder(db, pipeline_id=pipeline_id, tenant_id=tenant.id, stage_ids=data.stage_ids)


@router.patch("/stages/{stage_id}", response_model=StageResponse, summary="Atualizar stage")
def update_stage(
    stage_id: uuid.UUID,
    data: StageUpdate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
):
    return StageService.update(db, stage_id=stage_id, data=data)


@router.delete("/stages/{stage_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deletar stage")
def delete_stage(
    stage_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
):
    StageService.delete(db, stage_id=stage_id)
    return None


# ==================== DEALS ====================

@router.post("/{pipeline_id}/deals", response_model=DealResponse, status_code=status.HTTP_201_CREATED, summary="Criar deal")
def create_deal(
    pipeline_id: uuid.UUID,
    data: DealCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
    current_user: User = Depends(get_current_user),
):
    return DealService.create(
        db,
        data=data,
        pipeline_id=pipeline_id,
        tenant_id=tenant.id,
        created_by=current_user,
    )


@router.get("/deals/{deal_id}", response_model=DealResponse, summary="Detalhe do deal")
def get_deal(
    deal_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
):
    return DealService.get_or_404(db, deal_id, tenant.id)


@router.patch("/deals/{deal_id}", response_model=DealResponse, summary="Atualizar deal")
def update_deal(
    deal_id: uuid.UUID,
    data: DealUpdate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
):
    return DealService.update(db, deal_id=deal_id, tenant_id=tenant.id, data=data)


@router.put("/deals/{deal_id}/move", response_model=DealResponse, summary="Mover deal")
def move_deal(
    deal_id: uuid.UUID,
    data: DealMove,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
):
    return DealService.move(
        db,
        deal_id=deal_id,
        tenant_id=tenant.id,
        stage_id=data.stage_id,
        position=data.position,
    )


@router.post("/deals/{deal_id}/won", response_model=DealResponse, summary="Marcar como ganho")
def mark_deal_won(
    deal_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
):
    return DealService.mark_won(db, deal_id=deal_id, tenant_id=tenant.id)


@router.post("/deals/{deal_id}/lost", response_model=DealResponse, summary="Marcar como perdido")
def mark_deal_lost(
    deal_id: uuid.UUID,
    data: DealLost,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
):
    return DealService.mark_lost(db, deal_id=deal_id, tenant_id=tenant.id, reason=data.reason)


@router.delete("/deals/{deal_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deletar deal")
def delete_deal(
    deal_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
):
    DealService.delete(db, deal_id=deal_id, tenant_id=tenant.id)
    return None