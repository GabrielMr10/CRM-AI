"""
Endpoints específicos para integração com n8n/IA
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user_id, oauth2_scheme
from app.db.session import get_db
from app.schemas.msg_n8n import N8NWebhookRequest, N8NWebhookResponse, N8NMessageSchema

router = APIRouter()


def get_current_user_dependency(token: str = Depends(oauth2_scheme)) -> int:
    """Dependency para obter usuário atual"""
    return get_current_user_id(token)


@router.post("/log")
def log_interaction_from_n8n(msg: N8NMessageSchema, db: Session = Depends(get_db)):
    """
    Recebe logs do n8n e salva no banco do CRM.
    """
    # Aqui entraria a lógica de salvar no banco
    # Exemplo: criar uma interação no banco de dados
    # from app.models.interaction import Interaction
    # interaction = Interaction(
    #     message=msg.message,
    #     lead_id=msg.lead_id,
    #     user_id=msg.user_id,
    #     source="n8n"
    # )
    # db.add(interaction)
    # db.commit()
    
    return {"status": "received", "lead": msg.lead_phone}


@router.post("/webhook", response_model=N8NWebhookResponse)
async def receive_n8n_webhook(
    webhook_data: N8NWebhookRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_dependency)
):
    """Recebe webhook do n8n com dados de interação/IA"""
    # Aqui você pode processar os dados recebidos do n8n
    # Por exemplo, salvar interações no banco de dados
    
    # Exemplo de processamento
    try:
        # Lógica de processamento dos dados do webhook
        # Por exemplo, criar uma interação no banco
        # interaction = Interaction(**webhook_data.dict())
        # db.add(interaction)
        # db.commit()
        
        return {
            "status": "success",
            "message": "Webhook recebido com sucesso",
            "data": webhook_data.dict()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao processar webhook: {str(e)}"
        )


@router.post("/send-to-n8n")
async def send_to_n8n(
    data: dict,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_dependency)
):
    """Envia dados para o n8n via webhook"""
    if not settings.N8N_WEBHOOK_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="URL do webhook n8n não configurada"
        )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.N8N_WEBHOOK_URL,
                json=data,
                timeout=30.0
            )
            response.raise_for_status()
            
            return {
                "status": "success",
                "message": "Dados enviados para n8n com sucesso",
                "n8n_response": response.json()
            }
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao comunicar com n8n: {str(e)}"
        )

