"""
Sistema de notificações por email para ações corretivas
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from loguru import logger
import json

from models import CorrectiveAction, ActionReminder, ActionStatus, Incident
from config import config


class EmailNotifier:
    """Sistema de notificações por email"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.smtp_server = config.email.smtp_server
        self.smtp_port = config.email.smtp_port
        self.username = config.email.username
        self.password = config.email.password
        self.from_email = config.email.from_email
        self.use_tls = config.email.use_tls
    
    def _create_smtp_connection(self) -> Optional[smtplib.SMTP]:
        """
        Cria uma conexão SMTP
        """
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            if self.use_tls:
                server.starttls()
            
            server.login(self.username, self.password)
            return server
            
        except Exception as e:
            logger.error(f"Erro ao conectar com servidor SMTP: {e}")
            return None
    
    def _send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = False
    ) -> bool:
        """
        Envia um email
        """
        try:
            server = self._create_smtp_connection()
            if not server:
                return False
            
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email enviado para {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar email: {e}")
            return False
    
    def _build_action_reminder_email(self, action: CorrectiveAction, reminder_type: str) -> tuple[str, str]:
        """
        Constrói o conteúdo do email de lembrete
        """
        incident = self.db_session.query(Incident).filter(
            Incident.id == action.incident_id
        ).first()
        
        if reminder_type == "overdue":
            subject = f"🚨 AÇÃO CORRETIVA EM ATRASO - {action.title}"
            urgency = "URGENTE"
            color = "#dc3545"
        elif reminder_type == "due_soon":
            subject = f"⏰ AÇÃO CORRETIVA VENCE EM BREVE - {action.title}"
            urgency = "IMPORTANTE"
            color = "#ffc107"
        else:
            subject = f"📋 LEMBRETE - Ação Corretiva Pendente - {action.title}"
            urgency = "LEMBRETE"
            color = "#17a2b8"
        
        # Constrói o corpo do email em HTML
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {color}; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 20px; border-radius: 0 0 5px 5px; }}
                .action-details {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid {color}; }}
                .incident-details {{ background-color: #e9ecef; padding: 15px; margin: 15px 0; border-radius: 5px; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #6c757d; }}
                .button {{ display: inline-block; background-color: {color}; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{urgency}</h1>
                    <h2>{subject}</h2>
                </div>
                
                <div class="content">
                    <p>Olá,</p>
                    
                    <p>Este é um lembrete automático sobre uma ação corretiva que requer sua atenção:</p>
                    
                    <div class="action-details">
                        <h3>📋 Detalhes da Ação</h3>
                        <p><strong>Título:</strong> {action.title}</p>
                        <p><strong>Descrição:</strong> {action.description}</p>
                        <p><strong>Status:</strong> {action.status.value.upper()}</p>
                        <p><strong>Responsável:</strong> {action.assigned_to or 'Não atribuído'}</p>
                        <p><strong>Data de Vencimento:</strong> {action.due_date.strftime('%d/%m/%Y %H:%M') if action.due_date else 'Não definida'}</p>
                        <p><strong>Criada em:</strong> {action.created_at.strftime('%d/%m/%Y %H:%M')}</p>
                    </div>
                    
                    <div class="incident-details">
                        <h3>🔍 Incidente Relacionado</h3>
                        <p><strong>ID:</strong> {incident.id}</p>
                        <p><strong>Título:</strong> {incident.title}</p>
                        <p><strong>Tipo de Falha:</strong> {incident.failure_type}</p>
                        <p><strong>Severidade:</strong> {incident.severity}</p>
                        <p><strong>Ticket JIRA:</strong> {incident.jira_ticket_id or 'Não criado'}</p>
                    </div>
                    
                    <p><strong>Próximos Passos:</strong></p>
                    <ul>
                        <li>Revise os detalhes da ação corretiva</li>
                        <li>Implemente as correções necessárias</li>
                        <li>Atualize o status da ação quando concluída</li>
                        <li>Documente as lições aprendidas</li>
                    </ul>
                    
                    <p>Se você tiver dúvidas ou precisar de mais informações, entre em contato com a equipe de incidentes.</p>
                    
                    <p>Atenciosamente,<br>Sistema de Gestão de Incidentes</p>
                </div>
                
                <div class="footer">
                    <p>Este é um email automático do sistema de gestão de incidentes.</p>
                    <p>Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return subject, html_body
    
    def send_action_reminder(self, action: CorrectiveAction, reminder_type: str = "normal") -> bool:
        """
        Envia um lembrete por email para uma ação corretiva
        """
        if not action.assigned_to:
            logger.warning(f"Ação {action.id} não tem responsável atribuído")
            return False
        
        subject, html_body = self._build_action_reminder_email(action, reminder_type)
        
        return self._send_email(
            to_email=action.assigned_to,
            subject=subject,
            body=html_body,
            is_html=True
        )
    
    def send_overdue_actions_notification(self, overdue_actions: List[CorrectiveAction]) -> bool:
        """
        Envia notificação sobre ações em atraso
        """
        if not overdue_actions:
            return True
        
        subject = f"🚨 {len(overdue_actions)} Ação(ões) Corretiva(s) em Atraso"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #dc3545; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 20px; border-radius: 0 0 5px 5px; }}
                .action-item {{ background-color: white; padding: 15px; margin: 10px 0; border-left: 4px solid #dc3545; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #6c757d; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 AÇÕES EM ATRASO</h1>
                    <h2>{len(overdue_actions)} ação(ões) corretiva(s) precisam de atenção imediata</h2>
                </div>
                
                <div class="content">
                    <p>As seguintes ações corretivas estão em atraso e requerem atenção imediata:</p>
        """
        
        for action in overdue_actions:
            incident = self.db_session.query(Incident).filter(
                Incident.id == action.incident_id
            ).first()
            
            html_body += f"""
                    <div class="action-item">
                        <h3>📋 {action.title}</h3>
                        <p><strong>Responsável:</strong> {action.assigned_to or 'Não atribuído'}</p>
                        <p><strong>Vencimento:</strong> {action.due_date.strftime('%d/%m/%Y %H:%M') if action.due_date else 'Não definida'}</p>
                        <p><strong>Incidente:</strong> #{incident.id} - {incident.title}</p>
                        <p><strong>Descrição:</strong> {action.description[:200]}...</p>
                    </div>
            """
        
        html_body += """
                    <p><strong>Ação Necessária:</strong></p>
                    <ul>
                        <li>Revise cada ação em atraso</li>
                        <li>Implemente as correções necessárias</li>
                        <li>Atualize o status das ações no sistema</li>
                        <li>Comunique possíveis atrasos adicionais</li>
                    </ul>
                    
                    <p>Atenciosamente,<br>Sistema de Gestão de Incidentes</p>
                </div>
                
                <div class="footer">
                    <p>Este é um email automático do sistema de gestão de incidentes.</p>
                    <p>Data/Hora: """ + datetime.now().strftime('%d/%m/%Y %H:%M:%S') + """</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Envia para administradores ou equipe de incidentes
        # Aqui você pode configurar uma lista de emails para notificações
        admin_emails = ["admin@empresa.com", "incidents@empresa.com"]
        
        success = True
        for email in admin_emails:
            if not self._send_email(email, subject, html_body, is_html=True):
                success = False
        
        return success
    
    def process_pending_reminders(self) -> Dict[str, int]:
        """
        Processa todos os lembretes pendentes
        """
        now = datetime.utcnow()
        
        # Busca lembretes que devem ser enviados
        pending_reminders = self.db_session.query(ActionReminder).filter(
            and_(
                ActionReminder.reminder_date <= now,
                ActionReminder.email_sent == False
            )
        ).all()
        
        stats = {
            "total_reminders": len(pending_reminders),
            "sent_successfully": 0,
            "failed": 0,
            "no_assignee": 0
        }
        
        for reminder in pending_reminders:
            action = self.db_session.query(CorrectiveAction).filter(
                CorrectiveAction.id == reminder.action_id
            ).first()
            
            if not action:
                logger.warning(f"Ação {reminder.action_id} não encontrada para lembrete {reminder.id}")
                reminder.email_sent = True
                stats["failed"] += 1
                continue
            
            # Verifica se a ação ainda está pendente
            if action.status != ActionStatus.PENDING:
                logger.info(f"Ação {action.id} não está mais pendente, cancelando lembrete")
                reminder.email_sent = True
                continue
            
            if not action.assigned_to:
                logger.warning(f"Ação {action.id} não tem responsável atribuído")
                reminder.email_sent = True
                stats["no_assignee"] += 1
                continue
            
            # Determina o tipo de lembrete
            reminder_type = "normal"
            if action.due_date and action.due_date < now:
                reminder_type = "overdue"
            elif action.due_date and (action.due_date - now).days <= 3:
                reminder_type = "due_soon"
            
            # Envia o email
            if self.send_action_reminder(action, reminder_type):
                reminder.email_sent = True
                reminder.sent_at = now
                stats["sent_successfully"] += 1
            else:
                stats["failed"] += 1
        
        self.db_session.commit()
        
        logger.info(f"Processamento de lembretes concluído: {stats}")
        return stats
    
    def send_weekly_summary(self, recipient_email: str) -> bool:
        """
        Envia um resumo semanal das ações corretivas
        """
        # Busca estatísticas da semana
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        total_actions = self.db_session.query(CorrectiveAction).filter(
            CorrectiveAction.created_at >= week_ago
        ).count()
        
        completed_actions = self.db_session.query(CorrectiveAction).filter(
            and_(
                CorrectiveAction.created_at >= week_ago,
                CorrectiveAction.status == ActionStatus.COMPLETED
            )
        ).count()
        
        pending_actions = self.db_session.query(CorrectiveAction).filter(
            CorrectiveAction.status == ActionStatus.PENDING
        ).count()
        
        overdue_actions = len(self.db_session.query(CorrectiveAction).filter(
            and_(
                CorrectiveAction.status == ActionStatus.PENDING,
                CorrectiveAction.due_date < datetime.utcnow()
            )
        ).all())
        
        subject = f"📊 Resumo Semanal - Gestão de Incidentes ({datetime.now().strftime('%d/%m/%Y')})"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 20px; border-radius: 0 0 5px 5px; }}
                .stat-box {{ background-color: white; padding: 15px; margin: 10px 0; border-radius: 5px; text-align: center; }}
                .stat-number {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #6c757d; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Resumo Semanal</h1>
                    <h2>Gestão de Incidentes</h2>
                </div>
                
                <div class="content">
                    <p>Resumo das atividades da última semana:</p>
                    
                    <div class="stat-box">
                        <div class="stat-number">{total_actions}</div>
                        <div>Novas Ações Criadas</div>
                    </div>
                    
                    <div class="stat-box">
                        <div class="stat-number">{completed_actions}</div>
                        <div>Ações Concluídas</div>
                    </div>
                    
                    <div class="stat-box">
                        <div class="stat-number">{pending_actions}</div>
                        <div>Ações Pendentes</div>
                    </div>
                    
                    <div class="stat-box">
                        <div class="stat-number">{overdue_actions}</div>
                        <div>Ações em Atraso</div>
                    </div>
                    
                    <p><strong>Taxa de Conclusão:</strong> {(completed_actions / total_actions * 100) if total_actions > 0 else 0:.1f}%</p>
                    
                    <p>Atenciosamente,<br>Sistema de Gestão de Incidentes</p>
                </div>
                
                <div class="footer">
                    <p>Este é um email automático do sistema de gestão de incidentes.</p>
                    <p>Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(recipient_email, subject, html_body, is_html=True)
    
    def test_email_connection(self) -> bool:
        """
        Testa a conexão de email
        """
        try:
            server = self._create_smtp_connection()
            if server:
                server.quit()
                logger.info("Conexão de email testada com sucesso")
                return True
            return False
        except Exception as e:
            logger.error(f"Erro ao testar conexão de email: {e}")
            return False
