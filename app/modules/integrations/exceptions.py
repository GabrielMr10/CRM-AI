"""
Exceções customizadas do módulo de integrações.
"""
from fastapi import HTTPException, status


class EvolutionAPIException(HTTPException):
    """Erro na comunicação com Evolution API."""

    def __init__(self, detail: str = "Erro na comunicação com Evolution API"):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail
        )


class InstanceNotFoundException(HTTPException):
    """Instância WhatsApp não encontrada."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instância WhatsApp não encontrada. Inicie a conexão primeiro."
        )


class InstanceAlreadyConnectedException(HTTPException):
    """WhatsApp já está conectado."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="WhatsApp já está conectado"
        )


class QRCodeGenerationException(HTTPException):
    """Falha ao gerar QR Code."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível gerar o QR Code. Tente novamente."
        )
