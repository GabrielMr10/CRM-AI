"""
Importa todos os models para o Alembic detectar.
"""
from app.db.session import Base  # noqa

# Models
from app.modules.tenants.models import Tenant  # noqa
from app.modules.users.models import User  # noqa
from app.modules.leads.models import Lead # noqa
from app.modules.pipeline.models import Pipeline, Stage, Deal  # noqa
from app.modules.conversations.models import Conversation, Message  # noqa
from app.modules.ai_agent.models import AgentConfig  # noqa
