"""
Model User - Representa um usuario do sistema TMC Redacao.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID, uuid4


class UserBase(BaseModel):
    """Campos base para User."""
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=1, max_length=255)


class UserLogin(BaseModel):
    """Schema para login."""
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UserCreate(UserBase):
    """Schema para criar usuario (admin cria)."""
    password: str = Field(..., min_length=10)
    role: Literal['admin', 'user'] = 'user'


class UserUpdate(BaseModel):
    """Schema para atualizar usuario (todos opcionais)."""
    name: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    role: Optional[Literal['admin', 'user']] = None
    is_active: Optional[bool] = None


class User(UserBase):
    """Schema completo do usuario (retornado do banco)."""
    id: UUID = Field(default_factory=uuid4)
    role: Literal['admin', 'user'] = 'user'
    avatar: Optional[str] = None
    is_new_user: bool = True
    is_active: bool = True
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}

    def to_frontend_format(self) -> dict:
        """Convert to frontend format (exclude sensitive fields)."""
        return {
            "id": str(self.id),
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "avatar": self.avatar,
            "isNewUser": self.is_new_user,
            "isActive": self.is_active,
            "lastLogin": self.last_login.isoformat() if self.last_login else None,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserWithPassword(User):
    """User with password_hash (internal use only, never expose to frontend)."""
    password_hash: str = ""
