"""
Agregador de rotas da API v1
"""
from fastapi import APIRouter

from app.api.api_v1.endpoints import auth, leads, users, n8n

api_router = APIRouter()

# Registrar todos os routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(leads.router, prefix="/leads", tags=["leads"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(n8n.router, prefix="/n8n", tags=["n8n"])

