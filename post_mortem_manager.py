"""
Sistema de gestão de post-mortems e ações corretivas
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from loguru import logger

from models import (
    Incident, PostMortem, CorrectiveAction, ActionReminder,
    PostMortemCreate, CorrectiveActionCreate, ActionStatus
)
from config import config


class PostMortemManager:
    """Gerenciador de post-mortems e ações corretivas"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.reminder_days = config.incident.reminder_days
    
    def create_post_mortem(
        self, 
        incident_id: int, 
        post_mortem_data: PostMortemCreate
    ) -> Optional[PostMortem]:
        """
        Cria um post-mortem para um incidente
        """
        try:
            # Verifica se o incidente existe
            incident = self.db_session.query(Incident).filter(
                Incident.id == incident_id
            ).first()
            
            if not incident:
                logger.error(f"Incidente {incident_id} não encontrado")
                return None
            
            # Verifica se já existe um post-mortem para este incidente
            existing_post_mortem = self.db_session.query(PostMortem).filter(
                PostMortem.incident_id == incident_id
            ).first()
            
            if existing_post_mortem:
                logger.warning(f"Post-mortem já existe para incidente {incident_id}")
                return existing_post_mortem
            
            # Cria o post-mortem
            post_mortem = PostMortem(
                incident_id=incident_id,
                summary=post_mortem_data.summary,
                root_cause=post_mortem_data.root_cause,
                impact_assessment=post_mortem_data.impact_assessment,
                lessons_learned=post_mortem_data.lessons_learned,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db_session.add(post_mortem)
            self.db_session.commit()
            
            logger.info(f"Post-mortem criado para incidente {incident_id}")
            return post_mortem
            
        except Exception as e:
            logger.error(f"Erro ao criar post-mortem: {e}")
            self.db_session.rollback()
            return None
    
    def add_corrective_action(
        self,
        incident_id: int,
        action_data: CorrectiveActionCreate
    ) -> Optional[CorrectiveAction]:
        """
        Adiciona uma ação corretiva a um incidente
        """
        try:
            # Verifica se o incidente existe
            incident = self.db_session.query(Incident).filter(
                Incident.id == incident_id
            ).first()
            
            if not incident:
                logger.error(f"Incidente {incident_id} não encontrado")
                return None
            
            # Busca o post-mortem associado
            post_mortem = self.db_session.query(PostMortem).filter(
                PostMortem.incident_id == incident_id
            ).first()
            
            # Cria a ação corretiva
            action = CorrectiveAction(
                incident_id=incident_id,
                post_mortem_id=post_mortem.id if post_mortem else None,
                title=action_data.title,
                description=action_data.description,
                assigned_to=action_data.assigned_to,
                due_date=action_data.due_date,
                status=ActionStatus.PENDING,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db_session.add(action)
            self.db_session.commit()
            
            # Cria lembretes para a ação
            self._create_action_reminders(action)
            
            logger.info(f"Ação corretiva criada: {action.id}")
            return action
            
        except Exception as e:
            logger.error(f"Erro ao criar ação corretiva: {e}")
            self.db_session.rollback()
            return None
    
    def _create_action_reminders(self, action: CorrectiveAction):
        """
        Cria lembretes automáticos para uma ação corretiva
        """
        try:
            for days in self.reminder_days:
                reminder_date = datetime.utcnow() + timedelta(days=days)
                
                reminder = ActionReminder(
                    action_id=action.id,
                    reminder_date=reminder_date,
                    created_at=datetime.utcnow()
                )
                
                self.db_session.add(reminder)
            
            self.db_session.commit()
            logger.info(f"Lembretes criados para ação {action.id}")
            
        except Exception as e:
            logger.error(f"Erro ao criar lembretes: {e}")
    
    def update_action_status(
        self,
        action_id: int,
        status: ActionStatus,
        notes: Optional[str] = None
    ) -> bool:
        """
        Atualiza o status de uma ação corretiva
        """
        try:
            action = self.db_session.query(CorrectiveAction).filter(
                CorrectiveAction.id == action_id
            ).first()
            
            if not action:
                logger.error(f"Ação {action_id} não encontrada")
                return False
            
            action.status = status
            action.updated_at = datetime.utcnow()
            
            if status == ActionStatus.COMPLETED:
                action.completed_at = datetime.utcnow()
                # Cancela lembretes pendentes
                self._cancel_pending_reminders(action_id)
            
            self.db_session.commit()
            
            logger.info(f"Status da ação {action_id} atualizado para {status}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao atualizar status da ação: {e}")
            self.db_session.rollback()
            return False
    
    def _cancel_pending_reminders(self, action_id: int):
        """
        Cancela lembretes pendentes para uma ação
        """
        try:
            pending_reminders = self.db_session.query(ActionReminder).filter(
                and_(
                    ActionReminder.action_id == action_id,
                    ActionReminder.email_sent == False
                )
            ).all()
            
            for reminder in pending_reminders:
                reminder.email_sent = True  # Marca como "enviado" para não processar
            
            self.db_session.commit()
            
        except Exception as e:
            logger.error(f"Erro ao cancelar lembretes: {e}")
    
    def get_pending_actions(self, assigned_to: Optional[str] = None) -> List[CorrectiveAction]:
        """
        Obtém ações corretivas pendentes
        """
        query = self.db_session.query(CorrectiveAction).filter(
            CorrectiveAction.status == ActionStatus.PENDING
        )
        
        if assigned_to:
            query = query.filter(CorrectiveAction.assigned_to == assigned_to)
        
        return query.order_by(desc(CorrectiveAction.created_at)).all()
    
    def get_overdue_actions(self) -> List[CorrectiveAction]:
        """
        Obtém ações corretivas em atraso
        """
        now = datetime.utcnow()
        
        return self.db_session.query(CorrectiveAction).filter(
            and_(
                CorrectiveAction.status == ActionStatus.PENDING,
                CorrectiveAction.due_date < now
            )
        ).order_by(desc(CorrectiveAction.due_date)).all()
    
    def get_actions_due_soon(self, days_ahead: int = 3) -> List[CorrectiveAction]:
        """
        Obtém ações que vencem em breve
        """
        now = datetime.utcnow()
        future_date = now + timedelta(days=days_ahead)
        
        return self.db_session.query(CorrectiveAction).filter(
            and_(
                CorrectiveAction.status == ActionStatus.PENDING,
                CorrectiveAction.due_date >= now,
                CorrectiveAction.due_date <= future_date
            )
        ).order_by(CorrectiveAction.due_date).all()
    
    def get_incident_actions(self, incident_id: int) -> List[CorrectiveAction]:
        """
        Obtém todas as ações corretivas de um incidente
        """
        return self.db_session.query(CorrectiveAction).filter(
            CorrectiveAction.incident_id == incident_id
        ).order_by(desc(CorrectiveAction.created_at)).all()
    
    def get_post_mortem(self, incident_id: int) -> Optional[PostMortem]:
        """
        Obtém o post-mortem de um incidente
        """
        return self.db_session.query(PostMortem).filter(
            PostMortem.incident_id == incident_id
        ).first()
    
    def get_action_statistics(self) -> Dict[str, Any]:
        """
        Retorna estatísticas das ações corretivas
        """
        total_actions = self.db_session.query(CorrectiveAction).count()
        
        pending_actions = self.db_session.query(CorrectiveAction).filter(
            CorrectiveAction.status == ActionStatus.PENDING
        ).count()
        
        completed_actions = self.db_session.query(CorrectiveAction).filter(
            CorrectiveAction.status == ActionStatus.COMPLETED
        ).count()
        
        overdue_actions = len(self.get_overdue_actions())
        
        # Ações por status
        actions_by_status = {}
        for status in ActionStatus:
            count = self.db_session.query(CorrectiveAction).filter(
                CorrectiveAction.status == status
            ).count()
            actions_by_status[status.value] = count
        
        return {
            "total_actions": total_actions,
            "pending_actions": pending_actions,
            "completed_actions": completed_actions,
            "overdue_actions": overdue_actions,
            "actions_by_status": actions_by_status,
            "completion_rate": (completed_actions / total_actions * 100) if total_actions > 0 else 0
        }
    
    def generate_post_mortem_report(self, incident_id: int) -> Optional[Dict[str, Any]]:
        """
        Gera um relatório completo do post-mortem
        """
        try:
            incident = self.db_session.query(Incident).filter(
                Incident.id == incident_id
            ).first()
            
            if not incident:
                return None
            
            post_mortem = self.get_post_mortem(incident_id)
            actions = self.get_incident_actions(incident_id)
            
            report = {
                "incident": {
                    "id": incident.id,
                    "title": incident.title,
                    "description": incident.description,
                    "failure_type": incident.failure_type,
                    "severity": incident.severity,
                    "status": incident.status,
                    "created_at": incident.created_at,
                    "resolved_at": incident.resolved_at,
                    "jira_ticket_id": incident.jira_ticket_id
                },
                "post_mortem": {
                    "summary": post_mortem.summary if post_mortem else None,
                    "root_cause": post_mortem.root_cause if post_mortem else None,
                    "impact_assessment": post_mortem.impact_assessment if post_mortem else None,
                    "lessons_learned": post_mortem.lessons_learned if post_mortem else None,
                    "created_at": post_mortem.created_at if post_mortem else None
                } if post_mortem else None,
                "actions": [
                    {
                        "id": action.id,
                        "title": action.title,
                        "description": action.description,
                        "status": action.status,
                        "assigned_to": action.assigned_to,
                        "due_date": action.due_date,
                        "completed_at": action.completed_at,
                        "created_at": action.created_at
                    }
                    for action in actions
                ],
                "statistics": {
                    "total_actions": len(actions),
                    "completed_actions": len([a for a in actions if a.status == ActionStatus.COMPLETED]),
                    "pending_actions": len([a for a in actions if a.status == ActionStatus.PENDING]),
                    "overdue_actions": len([a for a in actions if a.status == ActionStatus.PENDING and a.due_date and a.due_date < datetime.utcnow()])
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório de post-mortem: {e}")
            return None
