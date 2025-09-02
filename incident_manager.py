"""
Sistema principal de gestão de incidentes
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from loguru import logger
import schedule
import time
import threading

from models import (
    Incident, Failure, PostMortem, CorrectiveAction,
    IncidentCreate, PostMortemCreate, CorrectiveActionCreate,
    FailureType, IncidentStatus, ActionStatus
)
from failure_detector import FailureDetector
from jira_integration import JiraIntegration
from post_mortem_manager import PostMortemManager
from email_notifier import EmailNotifier
from config import config


class IncidentManager:
    """Sistema principal de gestão de incidentes"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.failure_detector = FailureDetector(db_session)
        self.jira_integration = JiraIntegration()
        self.post_mortem_manager = PostMortemManager(db_session)
        self.email_notifier = EmailNotifier(db_session)
        
        # Configuração de logging
        self._setup_logging()
        
        # Thread para processamento em background
        self._background_thread = None
        self._stop_background = False
    
    def _setup_logging(self):
        """Configura o sistema de logging"""
        logger.remove()  # Remove handler padrão
        
        # Log para arquivo
        logger.add(
            config.log_file,
            level=config.log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
            rotation="1 day",
            retention="30 days",
            compression="zip"
        )
        
        # Log para console
        logger.add(
            lambda msg: print(msg, end=""),
            level=config.log_level,
            format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}"
        )
    
    def process_failure(
        self,
        error_message: str,
        error_code: Optional[str] = None,
        stack_trace: Optional[str] = None,
        failure_type: FailureType = FailureType.OTHER,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Incident]:
        """
        Processa uma falha e determina se deve criar/atualizar um incidente
        """
        logger.info(f"Processando falha: {error_message[:100]}...")
        
        try:
            # Detecta se é uma falha recorrente
            existing_incident = self.failure_detector.detect_recurring_failures(
                error_message, error_code, failure_type, metadata
            )
            
            if existing_incident:
                # Falha recorrente - adiciona ao incidente existente
                logger.info(f"Falha recorrente detectada para incidente {existing_incident.id}")
                
                # Cria registro da falha
                failure = self.failure_detector.create_failure_record(
                    error_message, error_code, stack_trace, failure_type, metadata,
                    existing_incident.id
                )
                
                # Atualiza ticket JIRA se existir
                if existing_incident.jira_ticket_id:
                    failures = self.db_session.query(Failure).filter(
                        Failure.incident_id == existing_incident.id
                    ).all()
                    
                    self.jira_integration.update_incident_ticket(
                        existing_incident.jira_ticket_id, existing_incident, failures
                    )
                
                return existing_incident
            
            else:
                # Nova falha - verifica se deve criar incidente
                similar_failures = self.failure_detector._get_similar_failures(
                    error_message, error_code
                )
                
                if len(similar_failures) >= config.incident.failure_threshold - 1:
                    # Cria novo incidente
                    logger.info("Criando novo incidente para falhas recorrentes")
                    
                    incident = self._create_incident(
                        title=f"Falha Recorrente: {error_message[:50]}...",
                        description=f"Falhas similares detectadas {len(similar_failures) + 1} vezes",
                        failure_type=failure_type,
                        severity=self._determine_severity(failure_type, len(similar_failures) + 1)
                    )
                    
                    # Adiciona todas as falhas similares ao incidente
                    for similar_failure in similar_failures:
                        similar_failure.incident_id = incident.id
                    
                    # Cria registro da nova falha
                    failure = self.failure_detector.create_failure_record(
                        error_message, error_code, stack_trace, failure_type, metadata,
                        incident.id
                    )
                    
                    # Cria ticket JIRA
                    all_failures = self.db_session.query(Failure).filter(
                        Failure.incident_id == incident.id
                    ).all()
                    
                    jira_ticket_id = self.jira_integration.create_incident_ticket(
                        incident, all_failures
                    )
                    
                    if jira_ticket_id:
                        incident.jira_ticket_id = jira_ticket_id
                        self.db_session.commit()
                    
                    return incident
                
                else:
                    # Apenas registra a falha
                    logger.info("Registrando falha isolada")
                    failure = self.failure_detector.create_failure_record(
                        error_message, error_code, stack_trace, failure_type, metadata
                    )
                    return None
        
        except Exception as e:
            logger.error(f"Erro ao processar falha: {e}")
            self.db_session.rollback()
            return None
    
    def _create_incident(
        self,
        title: str,
        description: str,
        failure_type: FailureType,
        severity: str = "medium"
    ) -> Incident:
        """Cria um novo incidente"""
        incident = Incident(
            title=title,
            description=description,
            failure_type=failure_type,
            severity=severity,
            status=IncidentStatus.OPEN,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db_session.add(incident)
        self.db_session.commit()
        
        logger.info(f"Incidente criado: {incident.id}")
        return incident
    
    def _determine_severity(self, failure_type: FailureType, failure_count: int) -> str:
        """Determina a severidade baseada no tipo e quantidade de falhas"""
        if failure_type in [FailureType.SECURITY_ISSUE, FailureType.SYSTEM_ERROR]:
            return "critical" if failure_count >= 3 else "high"
        elif failure_type in [FailureType.DATABASE_ERROR, FailureType.API_ERROR]:
            return "high" if failure_count >= 5 else "medium"
        else:
            return "medium" if failure_count >= 3 else "low"
    
    def create_post_mortem(
        self,
        incident_id: int,
        summary: str,
        root_cause: str,
        impact_assessment: str,
        lessons_learned: str
    ) -> Optional[PostMortem]:
        """Cria um post-mortem para um incidente"""
        post_mortem_data = PostMortemCreate(
            summary=summary,
            root_cause=root_cause,
            impact_assessment=impact_assessment,
            lessons_learned=lessons_learned
        )
        
        return self.post_mortem_manager.create_post_mortem(incident_id, post_mortem_data)
    
    def add_corrective_action(
        self,
        incident_id: int,
        title: str,
        description: str,
        assigned_to: Optional[str] = None,
        due_date: Optional[datetime] = None
    ) -> Optional[CorrectiveAction]:
        """Adiciona uma ação corretiva a um incidente"""
        action_data = CorrectiveActionCreate(
            title=title,
            description=description,
            assigned_to=assigned_to,
            due_date=due_date
        )
        
        action = self.post_mortem_manager.add_corrective_action(incident_id, action_data)
        
        # Adiciona a ação ao ticket JIRA se existir
        if action:
            incident = self.db_session.query(Incident).filter(
                Incident.id == incident_id
            ).first()
            
            if incident and incident.jira_ticket_id:
                self.jira_integration.add_action_to_ticket(
                    incident.jira_ticket_id, title, description
                )
        
        return action
    
    def resolve_incident(self, incident_id: int, resolution_notes: Optional[str] = None) -> bool:
        """Resolve um incidente"""
        try:
            incident = self.db_session.query(Incident).filter(
                Incident.id == incident_id
            ).first()
            
            if not incident:
                logger.error(f"Incidente {incident_id} não encontrado")
                return False
            
            incident.status = IncidentStatus.RESOLVED
            incident.resolved_at = datetime.utcnow()
            incident.updated_at = datetime.utcnow()
            
            # Fecha ticket JIRA se existir
            if incident.jira_ticket_id:
                self.jira_integration.close_incident_ticket(
                    incident.jira_ticket_id, resolution_notes or "Incidente resolvido"
                )
            
            self.db_session.commit()
            
            logger.info(f"Incidente {incident_id} resolvido")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao resolver incidente: {e}")
            self.db_session.rollback()
            return False
    
    def get_incident_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas dos incidentes"""
        total_incidents = self.db_session.query(Incident).count()
        
        open_incidents = self.db_session.query(Incident).filter(
            Incident.status == IncidentStatus.OPEN
        ).count()
        
        resolved_incidents = self.db_session.query(Incident).filter(
            Incident.status == IncidentStatus.RESOLVED
        ).count()
        
        # Estatísticas de falhas
        failure_stats = self.failure_detector.get_failure_statistics()
        
        # Estatísticas de ações
        action_stats = self.post_mortem_manager.get_action_statistics()
        
        return {
            "incidents": {
                "total": total_incidents,
                "open": open_incidents,
                "resolved": resolved_incidents,
                "resolution_rate": (resolved_incidents / total_incidents * 100) if total_incidents > 0 else 0
            },
            "failures": failure_stats,
            "actions": action_stats
        }
    
    def _process_reminders(self):
        """Processa lembretes pendentes"""
        try:
            stats = self.email_notifier.process_pending_reminders()
            logger.info(f"Lembretes processados: {stats}")
        except Exception as e:
            logger.error(f"Erro ao processar lembretes: {e}")
    
    def _check_overdue_actions(self):
        """Verifica ações em atraso"""
        try:
            overdue_actions = self.post_mortem_manager.get_overdue_actions()
            
            if overdue_actions:
                logger.warning(f"{len(overdue_actions)} ações em atraso detectadas")
                self.email_notifier.send_overdue_actions_notification(overdue_actions)
        except Exception as e:
            logger.error(f"Erro ao verificar ações em atraso: {e}")
    
    def _cleanup_old_data(self):
        """Limpa dados antigos"""
        try:
            # Remove falhas antigas
            removed_failures = self.failure_detector.cleanup_old_failures()
            logger.info(f"Limpeza concluída: {removed_failures} falhas removidas")
        except Exception as e:
            logger.error(f"Erro na limpeza de dados: {e}")
    
    def _background_worker(self):
        """Worker em background para tarefas agendadas"""
        while not self._stop_background:
            try:
                schedule.run_pending()
                time.sleep(60)  # Verifica a cada minuto
            except Exception as e:
                logger.error(f"Erro no worker em background: {e}")
                time.sleep(60)
    
    def start_background_processing(self):
        """Inicia o processamento em background"""
        if self._background_thread and self._background_thread.is_alive():
            logger.warning("Processamento em background já está rodando")
            return
        
        # Agenda tarefas
        schedule.every().hour.do(self._process_reminders)
        schedule.every().day.at("09:00").do(self._check_overdue_actions)
        schedule.every().sunday.at("10:00").do(self._cleanup_old_data)
        
        # Inicia thread em background
        self._stop_background = False
        self._background_thread = threading.Thread(target=self._background_worker, daemon=True)
        self._background_thread.start()
        
        logger.info("Processamento em background iniciado")
    
    def stop_background_processing(self):
        """Para o processamento em background"""
        self._stop_background = True
        
        if self._background_thread:
            self._background_thread.join(timeout=5)
        
        schedule.clear()
        logger.info("Processamento em background parado")
    
    def test_integrations(self) -> Dict[str, bool]:
        """Testa todas as integrações"""
        results = {
            "jira": self.jira_integration.test_connection(),
            "email": self.email_notifier.test_email_connection(),
            "database": True  # Se chegou até aqui, o banco está funcionando
        }
        
        logger.info(f"Teste de integrações: {results}")
        return results
