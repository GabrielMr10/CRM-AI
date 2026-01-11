"""
Exceções do módulo AI Agent.
"""
from app.core.exceptions import NotFoundException


class AgentConfigNotFoundError(NotFoundException):
    def __init__(self, tenant_id: str | None = None):
        detail = "Configuração do agente não encontrada"
        if tenant_id:
            detail = f"Configuração do agente não encontrada para tenant '{tenant_id}'"
        super().__init__(detail=detail)