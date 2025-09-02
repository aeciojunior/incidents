"""
Configurações do sistema de gestão de incidentes
"""
import os
from typing import Optional
from pydantic import BaseSettings, Field
from dotenv import load_dotenv

load_dotenv()


class JiraConfig(BaseSettings):
    """Configurações do JIRA"""
    url: str = Field(..., env="JIRA_URL")
    username: str = Field(..., env="JIRA_USERNAME")
    api_token: str = Field(..., env="JIRA_API_TOKEN")
    project_key: str = Field(..., env="JIRA_PROJECT_KEY")
    issue_type: str = Field(default="Bug", env="JIRA_ISSUE_TYPE")
    
    class Config:
        env_prefix = "JIRA_"


class EmailConfig(BaseSettings):
    """Configurações de email"""
    smtp_server: str = Field(..., env="SMTP_SERVER")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    username: str = Field(..., env="EMAIL_USERNAME")
    password: str = Field(..., env="EMAIL_PASSWORD")
    from_email: str = Field(..., env="FROM_EMAIL")
    use_tls: bool = Field(default=True, env="USE_TLS")
    
    class Config:
        env_prefix = "EMAIL_"


class DatabaseConfig(BaseSettings):
    """Configurações do banco de dados"""
    database_url: str = Field(default="sqlite:///incidents.db", env="DATABASE_URL")
    
    class Config:
        env_prefix = "DB_"


class IncidentConfig(BaseSettings):
    """Configurações de incidentes"""
    failure_threshold: int = Field(default=3, env="FAILURE_THRESHOLD")
    time_window_hours: int = Field(default=24, env="TIME_WINDOW_HOURS")
    reminder_days: list[int] = Field(default=[7, 14, 30], env="REMINDER_DAYS")
    
    class Config:
        env_prefix = "INCIDENT_"


class Config:
    """Configuração principal"""
    jira: JiraConfig = JiraConfig()
    email: EmailConfig = EmailConfig()
    database: DatabaseConfig = DatabaseConfig()
    incident: IncidentConfig = IncidentConfig()
    
    # Configurações de logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="incidents.log", env="LOG_FILE")


# Instância global de configuração
config = Config()
