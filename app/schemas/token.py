"""
Schemas Pydantic para Tokens
"""
from pydantic import BaseModel


class Token(BaseModel):
    """Schema de resposta de token"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Schema para refresh token"""
    refresh_token: str

