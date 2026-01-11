"""
Ponto de entrada da aplicação FastAPI.
Monta middlewares e registra rotas dos módulos.

"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

# ==================== CRIAR APP ====================
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# ==================== MIDDLEWARES ====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== REGISTRAR ROTAS ====================
# Descomente conforme criar os módulos:

from app.modules.auth.router import router as auth_router
from app.modules.tenants.router import router as tenants_router
from app.modules.users.router import router as users_router
from app.modules.leads.router import router as leads_router
from app.modules.pipeline.router import router as pipeline_router
from app.modules.conversations.router import router as conversations_router
from app.modules.webhooks.router import router as webhooks_router
from app.modules.ai_agent.router import router as ai_agent_router

app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["Auth"])
app.include_router(tenants_router, prefix=f"{settings.API_V1_STR}/tenants", tags=["Tenants"])
app.include_router(users_router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])
app.include_router(leads_router, prefix=f"{settings.API_V1_STR}/leads", tags=["Leads"])
app.include_router(pipeline_router, prefix=f"{settings.API_V1_STR}/pipelines", tags=["Pipeline"])
app.include_router(conversations_router, prefix=f"{settings.API_V1_STR}/conversations", tags=["Conversations"])
app.include_router(webhooks_router, prefix=f"{settings.API_V1_STR}/webhooks", tags=["Webhooks"])
app.include_router(ai_agent_router, prefix=f"{settings.API_V1_STR}/ai-agent", tags=["AI Agent"])


# ==================== HEALTH CHECKS ====================
@app.get("/", tags=["Health"])
def root():
    """Root endpoint - confirma que API está rodando."""
    return {"message": f"{settings.PROJECT_NAME} is running 🚀", "version": settings.VERSION}


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check para load balancers e monitoramento."""
    return {"status": "healthy"}