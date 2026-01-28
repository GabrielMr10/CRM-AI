# app/modules/webhooks/handlers/evolution.py

import logging
from uuid import UUID
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.modules.conversations.service import ConversationService
from app.modules.integrations.evolution_client import evolution_client
from app.modules.leads.models import Lead
from app.modules.tenants.models import Tenant

logger = logging.getLogger(__name__)

# Mapeamento para parser robusto de tipos
MESSAGE_TYPES_MAP = {
    "conversation": "text",
    "extendedTextMessage": "text",
    "imageMessage": "image",
    "videoMessage": "video",
    "audioMessage": "audio",
    "documentMessage": "document",
    "stickerMessage": "sticker",
    "contactMessage": "contact",
    "locationMessage": "location",
    "voiceMessage": "audio",
}

async def _create_session() -> Session:
    """Cria sessão thread-safe fora do loop principal"""
    return await run_in_threadpool(SessionLocal)

async def handle_evolution_webhook(tenant_id: str, payload: dict):
    """
    Handler da Evolution API - Production Grade (Blindado).
    - Validação forte
    - Sessão isolada
    - Commit atômico
    - Parser robusto
    """

    # 1️⃣ Validação inicial (Rápida, sem DB)
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        logger.warning(f"⚠️ Tenant ID inválido recebido: {tenant_id}")
        return {"status": "ignored", "reason": "invalid_tenant_id"}

    if payload.get("type") != "MESSAGES_UPSERT":
        return {"status": "ignored", "reason": "not_upsert"}

    # Cria sessão isolada
    db = await _create_session()

    try:
        # 2️⃣ Valida tenant (Na threadpool para não travar)
        tenant = await run_in_threadpool(
            lambda: db.query(Tenant).filter(Tenant.id == tenant_uuid).first()
        )
        if not tenant:
            logger.warning(f"⚠️ Tenant inexistente: {tenant_id}")
            return {"status": "ignored", "reason": "tenant_not_found"}

        # 3️⃣ Extração de Dados
        data = payload.get("data", {})
        key = data.get("key", {})
        message_content = data.get("message", {})

        remote_jid = key.get("remoteJid", "")
        from_me = key.get("fromMe", False)
        message_id = key.get("id")

        if "status@broadcast" in remote_jid:
            return {"status": "ignored", "reason": "broadcast"}
        
        if "@" not in remote_jid:
            return {"status": "ignored", "reason": "invalid_remote_jid"}

        customer_phone = remote_jid.split("@")[0]

        # 4️⃣ Parser Robusto (Map Based)
        text = None
        msg_type = "unknown"

        for raw_type, mapped_type in MESSAGE_TYPES_MAP.items():
            if raw_type in message_content:
                msg_type = mapped_type
                content_data = message_content[raw_type]

                if mapped_type == "text":
                    text = content_data if isinstance(content_data, str) else content_data.get("text")
                elif mapped_type in ["image", "video", "document"]:
                    text = content_data.get("caption") or f"[{mapped_type.capitalize()}]"
                elif mapped_type == "audio":
                    text = "[Áudio]"
                elif mapped_type == "sticker":
                    text = "[Sticker]"
                elif mapped_type == "location":
                    text = "[Localização]"
                elif mapped_type == "contact":
                    text = "[Contato]"
                break

        if not msg_type or msg_type == "unknown":
            logger.info("⚠️ Tipo de mensagem não suportado ou desconhecido - ignorando")
            return {"status": "ignored", "reason": "unsupported_message_type"}

        if msg_type == "text" and not text:
             return {"status": "ignored", "reason": "empty_text"}

        # 5️⃣ Processamento Principal (Service)
        # Chamamos o método estático dentro da threadpool
        # auto_commit=False é essencial aqui
        await run_in_threadpool(
            lambda: ConversationService.process_incoming_message(
                db,
                tenant_id=str(tenant_uuid),
                customer_phone=customer_phone,
                content=text,
                message_type=msg_type,
                is_me=from_me,
                gateway_message_id=message_id,
                provider="evolution",
                auto_commit=False # Segura o commit!
            )
        )

        # 6️⃣ Enriquecimento de Perfil (Isolado)
        if not from_me:
            await _enrich_contact_profile(db, str(tenant_uuid), customer_phone)

        # 7️⃣ Commit Final Atômico
        await run_in_threadpool(db.commit)
        
        return {"status": "success"}

    except Exception as e:
        logger.error(f"❌ Erro Crítico Evolution: {e}", exc_info=True)
        # Salva o banco de ficar travado em estado de erro
        await run_in_threadpool(db.rollback)
        return {"status": "error", "message": str(e)}
        
    finally:
        # Fecha a conexão incondicionalmente
        await run_in_threadpool(db.close)

async def _enrich_contact_profile(db: Session, tenant_id: str, phone: str):
    """Busca foto de perfil de forma segura sem quebrar o fluxo."""
    try:
        lead = await run_in_threadpool(
            lambda: db.query(Lead).filter(
                Lead.phone == phone, 
                Lead.tenant_id == tenant_id
            ).first()
        )

        if lead and not lead.profile_picture_url:
            logger.info(f"📸 Buscando foto para {phone}...")
            # Chamada HTTP async (não bloqueia)
            profile_pic_url = await evolution_client.get_profile_picture(
                tenant_id=tenant_id,
                phone_number=phone
            )
            
            if profile_pic_url:
                lead.profile_picture_url = profile_pic_url
                # O objeto lead já está na sessão, commit final salvará isso
                logger.info(f"✅ Foto encontrada para: {phone}")
                
    except Exception as e:
        logger.warning(f"⚠️ Falha não-crítica ao buscar foto: {e}")