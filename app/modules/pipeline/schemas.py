"""
Schemas Pydantic para Pipeline.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


# ==================== PIPELINE ====================

class PipelineBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None


class PipelineCreate(PipelineBase):
    is_default: bool = False
    settings: dict[str, Any] = Field(default_factory=dict)


class PipelineUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    settings: dict[str, Any] | None = None


class PipelineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    is_default: bool
    settings: dict[str, Any]
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ==================== STAGE ====================

class StageBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#6B7280", max_length=20)


class StageCreate(StageBase):
    position: int = 0
    is_won: bool = False
    is_lost: bool = False
    auto_probability: int | None = Field(None, ge=0, le=100)


class StageUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    color: str | None = Field(None, max_length=20)
    position: int | None = None
    is_won: bool | None = None
    is_lost: bool | None = None
    auto_probability: int | None = Field(None, ge=0, le=100)


class StageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    position: int
    color: str
    is_won: bool
    is_lost: bool
    auto_probability: int | None
    pipeline_id: uuid.UUID
    created_at: datetime


class StageReorder(BaseModel):
    """Para reordenar stages."""
    stage_ids: list[uuid.UUID] = Field(..., description="IDs na nova ordem")


# ==================== PIPELINE WITH STAGES ====================
# Moved here after StageResponse is defined

class PipelineWithStages(PipelineResponse):
    """Pipeline com stages incluídos."""
    stages: list[StageResponse] = []


# ==================== DEAL ====================

class DealBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    value: float = Field(default=0, ge=0)
    probability: int = Field(default=0, ge=0, le=100)
    expected_close_date: datetime | None = None
    notes: str | None = None


class DealCreate(DealBase):
    stage_id: uuid.UUID
    lead_id: uuid.UUID | None = None
    assigned_to_id: uuid.UUID | None = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class DealUpdate(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=255)
    value: float | None = Field(None, ge=0)
    probability: int | None = Field(None, ge=0, le=100)
    expected_close_date: datetime | None = None
    notes: str | None = None
    assigned_to_id: uuid.UUID | None = None
    custom_fields: dict[str, Any] | None = None


class DealMove(BaseModel):
    """Para mover deal entre stages."""
    stage_id: uuid.UUID
    position: int = 0


class DealWon(BaseModel):
    """Marcar deal como ganho."""
    pass


class DealLost(BaseModel):
    """Marcar deal como perdido."""
    reason: str | None = None


class DealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    value: float
    probability: int
    expected_close_date: datetime | None
    notes: str | None
    position: int
    is_won: bool
    is_lost: bool
    lost_reason: str | None
    custom_fields: dict[str, Any]

    tenant_id: uuid.UUID
    pipeline_id: uuid.UUID
    stage_id: uuid.UUID
    lead_id: uuid.UUID | None
    assigned_to_id: uuid.UUID | None
    created_by_id: uuid.UUID | None

    created_at: datetime
    updated_at: datetime
    won_at: datetime | None
    lost_at: datetime | None


class DealListResponse(BaseModel):
    items: list[DealResponse]
    total: int
    page: int
    pages: int
    per_page: int


# ==================== KANBAN VIEW ====================

class KanbanStage(BaseModel):
    """Stage com deals para visualização Kanban."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    position: int
    color: str
    is_won: bool
    is_lost: bool
    deals: list[DealResponse] = []
    deals_count: int = 0
    deals_value: float = 0


class KanbanView(BaseModel):
    """Visão completa do Kanban."""
    pipeline: PipelineResponse
    stages: list[KanbanStage]
    total_deals: int
    total_value: float
    weighted_value: float
