"""
Handler para webhooks do n8n.
"""
import uuid
from sqlalchemy.orm import Session

from app.modules.webhooks.schemas import N8NMessageSent, N8NLeadUpdate, N8NCreateDeal
from app.modules.conversations.service import ConversationService
from app.modules.conversations.schemas import MessageCreate
from app.modules.conversations.models import MessageType
from app.modules.leads.service import LeadService
from app.modules.leads.schemas import LeadUpdate
from app.modules.pipeline.service import PipelineService, DealService
from app.modules.pipeline.schemas import DealCreate


class N8NWebhookHandler:
    """Processa callbacks do n8n."""
    
    @staticmethod
    def handle_message_sent(
        db: Session,
        *,
        tenant_id: uuid.UUID,
        data: N8NMessageSent,
    ) -> dict:
        """
        Registra mensagem enviada pela Laura.
        
        Chamado pelo n8n após enviar resposta via Z-API.
        """
        # Buscar conversa pelo telefone
        conversation = ConversationService.get_by_phone(db, data.phone, tenant_id)
        
        if not conversation:
            return {"success": False, "error": "Conversa não encontrada"}
        
        # Registrar mensagem
        message_data = MessageCreate(
            content=data.content,
            message_type=MessageType(data.message_type) if data.message_type else MessageType.TEXT,
        )
        
        message = ConversationService.send_message(
            db,
            conversation_id=conversation.id,
            tenant_id=tenant_id,
            data=message_data,
            sent_by_bot=True,
            external_id=data.external_id,
        )
        
        return {
            "success": True,
            "message_id": str(message.id),
            "conversation_id": str(conversation.id),
        }
    
    @staticmethod
    def handle_lead_update(
        db: Session,
        *,
        tenant_id: uuid.UUID,
        data: N8NLeadUpdate,
    ) -> dict:
        """
        Atualiza lead baseado em análise da Laura.
        
        Ex: Laura identificou interesse, aumenta score.
        """
        # Buscar lead pelo telefone ou ID
        lead = None
        
        if data.lead_id:
            try:
                lead = LeadService.get_or_404(db, uuid.UUID(data.lead_id), tenant_id)
            except:
                pass
        
        if not lead:
            lead = LeadService.get_by_phone(db, data.phone, tenant_id)
        
        if not lead:
            return {"success": False, "error": "Lead não encontrado"}
        
        # Montar update
        update_data = LeadUpdate(
            status=data.status,
            score=data.score,
            temperature=data.temperature,
            interest=data.interest,
            notes=data.notes,
            tags=data.tags,
            custom_fields=data.custom_fields,
        )
        
        # Remover campos None
        update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
        
        if update_dict:
            lead = LeadService.update(
                db,
                lead_id=lead.id,
                tenant_id=tenant_id,
                data=LeadUpdate(**update_dict),
            )
        
        return {
            "success": True,
            "lead_id": str(lead.id),
            "updated_fields": list(update_dict.keys()),
        }
    
    @staticmethod
    def handle_create_deal(
        db: Session,
        *,
        tenant_id: uuid.UUID,
        data: N8NCreateDeal,
    ) -> dict:
        """
        Cria deal quando Laura qualifica lead.
        """
        from app.modules.pipeline.repository import PipelineRepository, StageRepository
        
        # Buscar lead
        lead = None
        if data.lead_id:
            try:
                lead = LeadService.get_or_404(db, uuid.UUID(data.lead_id), tenant_id)
            except:
                pass
        
        if not lead:
            lead = LeadService.get_by_phone(db, data.phone, tenant_id)
        
        # Buscar pipeline (usar default se não especificado)
        pipeline_id = None
        if data.pipeline_id:
            pipeline_id = uuid.UUID(data.pipeline_id)
        else:
            default_pipeline = PipelineRepository.get_default(db, tenant_id)
            if default_pipeline:
                pipeline_id = default_pipeline.id
        
        if not pipeline_id:
            return {"success": False, "error": "Pipeline não encontrado"}
        
        # Buscar stage (usar primeiro se não especificado)
        stage_id = None
        if data.stage_id:
            stage_id = uuid.UUID(data.stage_id)
        else:
            stages = StageRepository.get_by_pipeline(db, pipeline_id)
            if stages:
                stage_id = stages[0].id
        
        if not stage_id:
            return {"success": False, "error": "Stage não encontrado"}
        
        # Criar deal
        deal_data = DealCreate(
            title=data.title,
            value=data.value,
            stage_id=stage_id,
            lead_id=lead.id if lead else None,
        )
        
        deal = DealService.create(
            db,
            data=deal_data,
            pipeline_id=pipeline_id,
            tenant_id=tenant_id,
        )
        
        return {
            "success": True,
            "deal_id": str(deal.id),
            "pipeline_id": str(pipeline_id),
            "stage_id": str(stage_id),
        }
    
    @staticmethod
    def dispatch(
        db: Session,
        *,
        tenant_id: uuid.UUID,
        action: str,
        data: dict,
    ) -> dict:
        """Roteia ação para handler correto."""
        
        handlers = {
            "message_sent": (N8NMessageSent, N8NWebhookHandler.handle_message_sent),
            "lead_update": (N8NLeadUpdate, N8NWebhookHandler.handle_lead_update),
            "create_deal": (N8NCreateDeal, N8NWebhookHandler.handle_create_deal),
        }
        
        if action not in handlers:
            return {"success": False, "error": f"Ação '{action}' não suportada"}
        
        schema_class, handler_func = handlers[action]
        
        try:
            parsed_data = schema_class(**data)
            return handler_func(db, tenant_id=tenant_id, data=parsed_data)
        except Exception as e:
            return {"success": False, "error": str(e)}