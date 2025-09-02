"""
Integração com JIRA para criação automática de tickets
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from jira import JIRA
from loguru import logger
import json

from models import Incident, Failure, FailureType, IncidentStatus
from config import config


class JiraIntegration:
    """Integração com JIRA para gestão de tickets"""
    
    def __init__(self):
        self.jira = None
        self._connect()
    
    def _connect(self):
        """Estabelece conexão com o JIRA"""
        try:
            self.jira = JIRA(
                server=config.jira.url,
                basic_auth=(config.jira.username, config.jira.api_token)
            )
            logger.info("Conexão com JIRA estabelecida com sucesso")
        except Exception as e:
            logger.error(f"Erro ao conectar com JIRA: {e}")
            raise
    
    def _get_issue_fields(self, incident: Incident, failures: List[Failure]) -> Dict[str, Any]:
        """Prepara os campos do ticket JIRA"""
        # Conta o número de falhas
        failure_count = len(failures)
        
        # Prepara descrição detalhada
        description = self._build_description(incident, failures)
        
        # Determina prioridade baseada na severidade e frequência
        priority = self._determine_priority(incident.severity, failure_count)
        
        # Prepara labels
        labels = [
            "incident",
            f"failure-type-{incident.failure_type}",
            f"severity-{incident.severity}",
            f"recurring-{failure_count}x"
        ]
        
        fields = {
            "project": {"key": config.jira.project_key},
            "summary": f"[RECORRENTE] {incident.title} ({failure_count} ocorrências)",
            "description": description,
            "issuetype": {"name": config.jira.issue_type},
            "priority": {"name": priority},
            "labels": labels,
            "customfield_10001": failure_count,  # Campo customizado para contagem de falhas
        }
        
        return fields
    
    def _build_description(self, incident: Incident, failures: List[Failure]) -> str:
        """Constrói a descrição detalhada do ticket"""
        description_parts = [
            f"*Incidente ID:* {incident.id}",
            f"*Tipo de Falha:* {incident.failure_type}",
            f"*Severidade:* {incident.severity}",
            f"*Total de Ocorrências:* {len(failures)}",
            "",
            "*Descrição:*",
            incident.description or "Nenhuma descrição fornecida",
            "",
            "*Falhas Detectadas:*"
        ]
        
        # Adiciona detalhes das falhas
        for i, failure in enumerate(failures[-5:], 1):  # Mostra apenas as últimas 5
            description_parts.extend([
                f"",
                f"*Falha {i}:*",
                f"*Data:* {failure.occurred_at.strftime('%d/%m/%Y %H:%M:%S')}",
                f"*Mensagem:* {failure.error_message[:200]}...",
            ])
            
            if failure.error_code:
                description_parts.append(f"*Código:* {failure.error_code}")
        
        if len(failures) > 5:
            description_parts.append(f"",
                                   f"*... e mais {len(failures) - 5} falhas similares*")
        
        # Adiciona informações de contexto
        description_parts.extend([
            "",
            "*Contexto:*",
            "Este ticket foi criado automaticamente pelo sistema de detecção de falhas recorrentes.",
            f"Falhas similares foram detectadas {len(failures)} vezes.",
            "",
            "*Próximos Passos:*",
            "1. Investigar a causa raiz das falhas recorrentes",
            "2. Implementar ações corretivas",
            "3. Configurar monitoramento adicional se necessário"
        ])
        
        return "\n".join(description_parts)
    
    def _determine_priority(self, severity: str, failure_count: int) -> str:
        """Determina a prioridade do ticket baseada na severidade e frequência"""
        if severity == "critical" or failure_count >= 10:
            return "Highest"
        elif severity == "high" or failure_count >= 5:
            return "High"
        elif severity == "medium" or failure_count >= 3:
            return "Medium"
        else:
            return "Low"
    
    def create_incident_ticket(self, incident: Incident, failures: List[Failure]) -> Optional[str]:
        """
        Cria um ticket no JIRA para um incidente
        Retorna o ID do ticket criado ou None em caso de erro
        """
        try:
            if not self.jira:
                self._connect()
            
            fields = self._get_issue_fields(incident, failures)
            
            # Cria o ticket
            issue = self.jira.create_issue(fields=fields)
            
            logger.info(f"Ticket JIRA criado: {issue.key}")
            return issue.key
            
        except Exception as e:
            logger.error(f"Erro ao criar ticket JIRA: {e}")
            return None
    
    def update_incident_ticket(self, jira_ticket_id: str, incident: Incident, failures: List[Failure]) -> bool:
        """
        Atualiza um ticket existente no JIRA com novas informações
        """
        try:
            if not self.jira:
                self._connect()
            
            issue = self.jira.issue(jira_ticket_id)
            
            # Atualiza a descrição com as novas falhas
            new_description = self._build_description(incident, failures)
            
            # Adiciona comentário sobre a nova falha
            comment = f"*Nova falha detectada:*\n"
            comment += f"Data: {failures[-1].occurred_at.strftime('%d/%m/%Y %H:%M:%S')}\n"
            comment += f"Mensagem: {failures[-1].error_message[:200]}...\n"
            comment += f"Total de ocorrências: {len(failures)}"
            
            issue.add_comment(comment)
            
            # Atualiza o título se necessário
            new_summary = f"[RECORRENTE] {incident.title} ({len(failures)} ocorrências)"
            if issue.fields.summary != new_summary:
                issue.update(summary=new_summary)
            
            # Atualiza a prioridade se necessário
            new_priority = self._determine_priority(incident.severity, len(failures))
            if issue.fields.priority.name != new_priority:
                issue.update(priority={"name": new_priority})
            
            logger.info(f"Ticket JIRA atualizado: {jira_ticket_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao atualizar ticket JIRA {jira_ticket_id}: {e}")
            return False
    
    def close_incident_ticket(self, jira_ticket_id: str, resolution: str = "Fixed") -> bool:
        """
        Fecha um ticket no JIRA
        """
        try:
            if not self.jira:
                self._connect()
            
            issue = self.jira.issue(jira_ticket_id)
            
            # Transições disponíveis dependem do workflow do JIRA
            transitions = self.jira.transitions(issue)
            
            # Procura pela transição de fechamento
            close_transition = None
            for transition in transitions:
                if transition['name'].lower() in ['close', 'resolve', 'done', 'fechar', 'resolver']:
                    close_transition = transition
                    break
            
            if close_transition:
                self.jira.transition_issue(issue, close_transition['id'], 
                                         comment=f"Incidente resolvido automaticamente. Resolução: {resolution}")
                logger.info(f"Ticket JIRA fechado: {jira_ticket_id}")
                return True
            else:
                logger.warning(f"Nenhuma transição de fechamento encontrada para {jira_ticket_id}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao fechar ticket JIRA {jira_ticket_id}: {e}")
            return False
    
    def get_ticket_status(self, jira_ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém o status atual de um ticket no JIRA
        """
        try:
            if not self.jira:
                self._connect()
            
            issue = self.jira.issue(jira_ticket_id)
            
            return {
                "key": issue.key,
                "status": issue.fields.status.name,
                "assignee": issue.fields.assignee.displayName if issue.fields.assignee else None,
                "priority": issue.fields.priority.name,
                "created": issue.fields.created,
                "updated": issue.fields.updated,
                "summary": issue.fields.summary
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter status do ticket JIRA {jira_ticket_id}: {e}")
            return None
    
    def add_action_to_ticket(self, jira_ticket_id: str, action_title: str, action_description: str) -> bool:
        """
        Adiciona uma ação corretiva como comentário no ticket
        """
        try:
            if not self.jira:
                self._connect()
            
            issue = self.jira.issue(jira_ticket_id)
            
            comment = f"*Ação Corretiva Adicionada:*\n"
            comment += f"**Título:** {action_title}\n"
            comment += f"**Descrição:** {action_description}\n"
            comment += f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            
            issue.add_comment(comment)
            
            logger.info(f"Ação corretiva adicionada ao ticket: {jira_ticket_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao adicionar ação ao ticket JIRA {jira_ticket_id}: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Testa a conexão com o JIRA
        """
        try:
            if not self.jira:
                self._connect()
            
            # Tenta buscar informações do projeto
            project = self.jira.project(config.jira.project_key)
            logger.info(f"Conexão com JIRA testada com sucesso. Projeto: {project.name}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao testar conexão com JIRA: {e}")
            return False
