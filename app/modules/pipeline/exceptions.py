"""
Exceções específicas do módulo Pipeline.
"""
from app.core.exceptions import NotFoundException, BadRequestException


class PipelineNotFoundError(NotFoundException):
    def __init__(self, pipeline_id: str | None = None):
        detail = "Pipeline não encontrado"
        if pipeline_id:
            detail = f"Pipeline '{pipeline_id}' não encontrado"
        super().__init__(detail=detail)


class StageNotFoundError(NotFoundException):
    def __init__(self, stage_id: str | None = None):
        detail = "Stage não encontrado"
        if stage_id:
            detail = f"Stage '{stage_id}' não encontrado"
        super().__init__(detail=detail)


class DealNotFoundError(NotFoundException):
    def __init__(self, deal_id: str | None = None):
        detail = "Deal não encontrado"
        if deal_id:
            detail = f"Deal '{deal_id}' não encontrado"
        super().__init__(detail=detail)


class CannotDeleteDefaultPipelineError(BadRequestException):
    def __init__(self):
        super().__init__(detail="Não é possível excluir o pipeline padrão")


class CannotDeleteStageWithDealsError(BadRequestException):
    def __init__(self):
        super().__init__(detail="Não é possível excluir stage com deals. Mova os deals primeiro.")