"""
Repository do AI Agent.
"""
import uuid
from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ai_agent.models import AgentConfig
from app.modules.ai_agent.schemas import AgentConfigUpdate


class AgentConfigRepository:
    
    @staticmethod
    def get_by_tenant(db: Session, tenant_id: uuid.UUID) -> AgentConfig | None:
        stmt = select(AgentConfig).where(AgentConfig.tenant_id == tenant_id)
        return db.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def create(
        db: Session,
        *,
        tenant_id: uuid.UUID,
        agent_name: str = "Laura",
        agent_role: str = "Assistente Virtual",
        company_name: str | None = None,
    ) -> AgentConfig:
        config = AgentConfig(
            tenant_id=tenant_id,
            agent_name=agent_name,
            agent_role=agent_role,
            company_name=company_name,
        )
        
        db.add(config)
        db.commit()
        db.refresh(config)
        
        return config
    
    @staticmethod
    def get_or_create(
        db: Session,
        *,
        tenant_id: uuid.UUID,
        company_name: str | None = None,
    ) -> tuple[AgentConfig, bool]:
        """Retorna (config, criada: bool)."""
        existing = AgentConfigRepository.get_by_tenant(db, tenant_id)
        
        if existing:
            return existing, False
        
        config = AgentConfigRepository.create(
            db,
            tenant_id=tenant_id,
            company_name=company_name,
        )
        return config, True
    
    @staticmethod
    def update(
        db: Session,
        *,
        config: AgentConfig,
        data: AgentConfigUpdate,
    ) -> AgentConfig:
        update_data = data.model_dump(exclude_unset=True)
        
        # Converter horários string para time
        if "schedule_start" in update_data and update_data["schedule_start"]:
            h, m = map(int, update_data["schedule_start"].split(":"))
            update_data["schedule_start"] = time(h, m)
        
        if "schedule_end" in update_data and update_data["schedule_end"]:
            h, m = map(int, update_data["schedule_end"].split(":"))
            update_data["schedule_end"] = time(h, m)
        
        for field, value in update_data.items():
            setattr(config, field, value)
        
        db.commit()
        db.refresh(config)
        
        return config
    
    @staticmethod
    def toggle(db: Session, *, config: AgentConfig, is_enabled: bool) -> AgentConfig:
        config.is_enabled = is_enabled
        db.commit()
        db.refresh(config)
        return config