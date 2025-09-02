"""
Modelos de dados para o sistema de gestão de incidentes
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from pydantic import BaseModel, Field
import json

Base = declarative_base()


class IncidentStatus(str, Enum):
    """Status dos incidentes"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ActionStatus(str, Enum):
    """Status das ações corretivas"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class FailureType(str, Enum):
    """Tipos de falhas"""
    SYSTEM_ERROR = "system_error"
    NETWORK_ERROR = "network_error"
    DATABASE_ERROR = "database_error"
    API_ERROR = "api_error"
    PERFORMANCE_ISSUE = "performance_issue"
    SECURITY_ISSUE = "security_issue"
    OTHER = "other"


# Modelos do SQLAlchemy
class Incident(Base):
    """Modelo de incidente no banco de dados"""
    __tablename__ = "incidents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    failure_type = Column(String(50), nullable=False)
    severity = Column(String(20), default="medium")
    status = Column(String(20), default=IncidentStatus.OPEN)
    jira_ticket_id = Column(String(50), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime)
    
    # Relacionamentos
    failures = relationship("Failure", back_populates="incident")
    post_mortem = relationship("PostMortem", back_populates="incident", uselist=False)
    actions = relationship("CorrectiveAction", back_populates="incident")


class Failure(Base):
    """Modelo de falha individual"""
    __tablename__ = "failures"
    
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"))
    error_message = Column(Text)
    error_code = Column(String(100))
    stack_trace = Column(Text)
    metadata = Column(JSON)  # Informações adicionais como IP, user_id, etc.
    occurred_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    incident = relationship("Incident", back_populates="failures")


class PostMortem(Base):
    """Modelo de post-mortem"""
    __tablename__ = "post_mortems"
    
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), unique=True)
    summary = Column(Text)
    root_cause = Column(Text)
    impact_assessment = Column(Text)
    lessons_learned = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    incident = relationship("Incident", back_populates="post_mortem")
    actions = relationship("CorrectiveAction", back_populates="post_mortem")


class CorrectiveAction(Base):
    """Modelo de ação corretiva"""
    __tablename__ = "corrective_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"))
    post_mortem_id = Column(Integer, ForeignKey("post_mortems.id"))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(20), default=ActionStatus.PENDING)
    assigned_to = Column(String(100))
    due_date = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    incident = relationship("Incident", back_populates="actions")
    post_mortem = relationship("PostMortem", back_populates="actions")
    reminders = relationship("ActionReminder", back_populates="action")


class ActionReminder(Base):
    """Modelo de lembretes para ações corretivas"""
    __tablename__ = "action_reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    action_id = Column(Integer, ForeignKey("corrective_actions.id"))
    reminder_date = Column(DateTime, nullable=False)
    sent_at = Column(DateTime)
    email_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    action = relationship("CorrectiveAction", back_populates="reminders")


# Modelos Pydantic para API
class FailureCreate(BaseModel):
    """Modelo para criação de falha"""
    error_message: str
    error_code: Optional[str] = None
    stack_trace: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    failure_type: FailureType = FailureType.OTHER


class IncidentCreate(BaseModel):
    """Modelo para criação de incidente"""
    title: str
    description: Optional[str] = None
    failure_type: FailureType
    severity: str = "medium"


class PostMortemCreate(BaseModel):
    """Modelo para criação de post-mortem"""
    summary: str
    root_cause: str
    impact_assessment: str
    lessons_learned: str


class CorrectiveActionCreate(BaseModel):
    """Modelo para criação de ação corretiva"""
    title: str
    description: str
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None


class IncidentResponse(BaseModel):
    """Modelo de resposta de incidente"""
    id: int
    title: str
    description: Optional[str]
    failure_type: str
    severity: str
    status: str
    jira_ticket_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    failure_count: int
    
    class Config:
        from_attributes = True


class PostMortemResponse(BaseModel):
    """Modelo de resposta de post-mortem"""
    id: int
    incident_id: int
    summary: str
    root_cause: str
    impact_assessment: str
    lessons_learned: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CorrectiveActionResponse(BaseModel):
    """Modelo de resposta de ação corretiva"""
    id: int
    incident_id: int
    title: str
    description: str
    status: str
    assigned_to: Optional[str]
    due_date: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Função para criar o banco de dados
def create_database(database_url: str):
    """Cria o banco de dados e as tabelas"""
    engine = create_engine(database_url)
    Base.metadata.create_all(bind=engine)
    return engine


def get_session_factory(database_url: str):
    """Retorna uma factory de sessões do banco de dados"""
    engine = create_database(database_url)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
