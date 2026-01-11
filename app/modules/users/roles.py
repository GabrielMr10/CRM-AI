"""
Enum de roles (papéis) dos usuários.

USO:
    from app.modules.users.roles import UserRole
    
    if user.role == UserRole.ADMIN:
        # pode gerenciar usuários
    
    if user.has_permission(UserRole.MANAGER):
        # pode acessar dados

HIERARQUIA (maior para menor):
    OWNER > ADMIN > MANAGER > MEMBER
"""
from enum import Enum


class UserRole(str, Enum):
    """
    Papéis disponíveis no sistema.
    
    Herda de str para serialização automática em JSON.
    """
    
    OWNER = "owner"        # Dono do tenant - poder total
    ADMIN = "admin"        # Administrador - gerencia usuários
    MANAGER = "manager"    # Gerente - acesso completo aos dados
    MEMBER = "member"      # Membro - acesso básico
    
    @classmethod
    def get_hierarchy(cls) -> dict[str, int]:
        """Retorna hierarquia de roles (maior = mais poder)."""
        return {
            cls.OWNER: 100,
            cls.ADMIN: 80,
            cls.MANAGER: 60,
            cls.MEMBER: 40,
        }
    
    @property
    def level(self) -> int:
        """Nível de poder do role."""
        return self.get_hierarchy().get(self, 0)
    
    def has_permission(self, required_role: "UserRole") -> bool:
        """
        Verifica se este role tem permissão igual ou superior.
        
        Exemplo:
            UserRole.ADMIN.has_permission(UserRole.MANAGER)  # True
            UserRole.MEMBER.has_permission(UserRole.ADMIN)   # False
        """
        return self.level >= required_role.level
    
    @classmethod
    def choices(cls) -> list[str]:
        """Lista de valores para validação."""
        return [role.value for role in cls]


# Roles que podem gerenciar outros usuários
MANAGEMENT_ROLES = {UserRole.OWNER, UserRole.ADMIN}

# Roles que podem ver todos os dados do tenant
DATA_ACCESS_ROLES = {UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER}