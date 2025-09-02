"""
Exemplos de uso do Sistema de Gestão de Incidentes
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json

from models import get_session_factory, FailureType, ActionStatus
from incident_manager import IncidentManager


class IncidentExamples:
    """Exemplos práticos de uso do sistema"""
    
    def __init__(self):
        session_factory = get_session_factory("sqlite:///incidents.db")
        self.db_session = session_factory()
        self.incident_manager = IncidentManager(self.db_session)
    
    def exemplo_deteccao_falhas_recorrentes(self):
        """Exemplo: Detecção de falhas recorrentes"""
        print("=== Exemplo: Detecção de Falhas Recorrentes ===")
        
        # Simula falhas de timeout de banco de dados
        error_messages = [
            "Connection timeout to database server",
            "Connection timeout to database server", 
            "Connection timeout to database server",
            "Connection timeout to database server"
        ]
        
        for i, error_msg in enumerate(error_messages):
            print(f"Processando falha {i+1}: {error_msg}")
            
            incident = self.incident_manager.process_failure(
                error_message=error_msg,
                error_code="DB_TIMEOUT",
                failure_type=FailureType.DATABASE_ERROR,
                metadata={
                    "server": "db-prod-01",
                    "user": "app_user",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            if incident:
                print(f"✅ Incidente criado: ID {incident.id}, JIRA: {incident.jira_ticket_id}")
            else:
                print("⏳ Falha registrada, aguardando threshold...")
        
        print()
    
    def exemplo_post_mortem_completo(self):
        """Exemplo: Criação de post-mortem completo"""
        print("=== Exemplo: Post-Mortem Completo ===")
        
        # Cria um incidente de exemplo
        incident = self.incident_manager.process_failure(
            error_message="API rate limit exceeded",
            error_code="RATE_LIMIT_429",
            failure_type=FailureType.API_ERROR,
            metadata={"endpoint": "/api/users", "rate_limit": "1000/hour"}
        )
        
        if not incident:
            print("❌ Nenhum incidente criado")
            return
        
        print(f"📋 Criando post-mortem para incidente {incident.id}")
        
        # Cria post-mortem
        post_mortem = self.incident_manager.create_post_mortem(
            incident_id=incident.id,
            summary="Falhas recorrentes de rate limit na API de usuários",
            root_cause="Configuração inadequada de rate limiting e falta de cache",
            impact_assessment="Usuários não conseguem acessar funcionalidades críticas",
            lessons_learned="Implementar cache Redis e revisar limites de rate"
        )
        
        if post_mortem:
            print(f"✅ Post-mortem criado: ID {post_mortem.id}")
            
            # Adiciona ações corretivas
            acoes = [
                {
                    "title": "Implementar cache Redis",
                    "description": "Adicionar cache Redis para reduzir chamadas à API",
                    "assigned_to": "backend@empresa.com",
                    "due_date": datetime.now() + timedelta(days=3)
                },
                {
                    "title": "Revisar configuração de rate limiting",
                    "description": "Ajustar limites de rate para diferentes tipos de usuário",
                    "assigned_to": "devops@empresa.com",
                    "due_date": datetime.now() + timedelta(days=1)
                },
                {
                    "title": "Implementar retry com backoff",
                    "description": "Adicionar lógica de retry automático com backoff exponencial",
                    "assigned_to": "backend@empresa.com",
                    "due_date": datetime.now() + timedelta(days=5)
                }
            ]
            
            for acao in acoes:
                action = self.incident_manager.add_corrective_action(
                    incident_id=incident.id,
                    title=acao["title"],
                    description=acao["description"],
                    assigned_to=acao["assigned_to"],
                    due_date=acao["due_date"]
                )
                
                if action:
                    print(f"✅ Ação criada: {acao['title']} (ID: {action.id})")
        
        print()
    
    def exemplo_workflow_completo(self):
        """Exemplo: Workflow completo de um incidente"""
        print("=== Exemplo: Workflow Completo ===")
        
        # 1. Detecção de falhas
        print("1️⃣ Detectando falhas...")
        incident = None
        
        for i in range(5):
            incident = self.incident_manager.process_failure(
                error_message="Memory leak detected in application",
                error_code="MEMORY_LEAK",
                failure_type=FailureType.SYSTEM_ERROR,
                metadata={"memory_usage": f"{(i+1)*20}%", "process": "app-server"}
            )
            
            if incident:
                print(f"   Incidente criado após {i+1} falhas")
                break
        
        if not incident:
            print("❌ Nenhum incidente criado")
            return
        
        # 2. Criação de post-mortem
        print("2️⃣ Criando post-mortem...")
        post_mortem = self.incident_manager.create_post_mortem(
            incident_id=incident.id,
            summary="Vazamento de memória detectado no servidor de aplicação",
            root_cause="Objetos não sendo liberados corretamente pelo garbage collector",
            impact_assessment="Degradação gradual de performance até crash do sistema",
            lessons_learned="Implementar monitoramento de memória e revisar código crítico"
        )
        
        # 3. Ações corretivas
        print("3️⃣ Criando ações corretivas...")
        acoes = [
            {
                "title": "Implementar monitoramento de memória",
                "description": "Adicionar alertas para uso de memória > 80%",
                "assigned_to": "monitoring@empresa.com",
                "due_date": datetime.now() + timedelta(days=1)
            },
            {
                "title": "Revisar código crítico",
                "description": "Auditar código para vazamentos de memória",
                "assigned_to": "senior-dev@empresa.com",
                "due_date": datetime.now() + timedelta(days=7)
            }
        ]
        
        for acao in acoes:
            self.incident_manager.add_corrective_action(
                incident_id=incident.id,
                **acao
            )
        
        # 4. Simula resolução
        print("4️⃣ Resolvendo incidente...")
        success = self.incident_manager.resolve_incident(
            incident_id=incident.id,
            resolution_notes="Vazamento corrigido e monitoramento implementado"
        )
        
        if success:
            print("✅ Incidente resolvido com sucesso")
        
        # 5. Estatísticas
        print("5️⃣ Estatísticas finais:")
        stats = self.incident_manager.get_incident_statistics()
        print(f"   Total de incidentes: {stats['incidents']['total']}")
        print(f"   Taxa de resolução: {stats['incidents']['resolution_rate']:.1f}%")
        print(f"   Ações pendentes: {stats['actions']['pending_actions']}")
        
        print()
    
    def exemplo_diferentes_tipos_falhas(self):
        """Exemplo: Diferentes tipos de falhas"""
        print("=== Exemplo: Diferentes Tipos de Falhas ===")
        
        tipos_falhas = [
            {
                "tipo": FailureType.SECURITY_ISSUE,
                "mensagem": "Unauthorized access attempt detected",
                "codigo": "SEC_401",
                "metadata": {"ip": "192.168.1.100", "user": "admin"}
            },
            {
                "tipo": FailureType.NETWORK_ERROR,
                "mensagem": "Network connection lost",
                "codigo": "NET_TIMEOUT",
                "metadata": {"endpoint": "api.external.com", "timeout": "30s"}
            },
            {
                "tipo": FailureType.PERFORMANCE_ISSUE,
                "mensagem": "Response time exceeded threshold",
                "codigo": "PERF_SLOW",
                "metadata": {"response_time": "5.2s", "threshold": "2s"}
            }
        ]
        
        for falha in tipos_falhas:
            print(f"Processando falha: {falha['tipo'].value}")
            
            incident = self.incident_manager.process_failure(
                error_message=falha["mensagem"],
                error_code=falha["codigo"],
                failure_type=falha["tipo"],
                metadata=falha["metadata"]
            )
            
            if incident:
                print(f"   ✅ Incidente criado: ID {incident.id}, Severidade: {incident.severity}")
            else:
                print("   ⏳ Falha registrada")
        
        print()
    
    def exemplo_estatisticas_detalhadas(self):
        """Exemplo: Estatísticas detalhadas"""
        print("=== Exemplo: Estatísticas Detalhadas ===")
        
        stats = self.incident_manager.get_incident_statistics()
        
        print("📊 Estatísticas do Sistema:")
        print(f"   Incidentes:")
        print(f"     Total: {stats['incidents']['total']}")
        print(f"     Abertos: {stats['incidents']['open']}")
        print(f"     Resolvidos: {stats['incidents']['resolved']}")
        print(f"     Taxa de resolução: {stats['incidents']['resolution_rate']:.1f}%")
        
        print(f"   Falhas:")
        print(f"     Total: {stats['failures']['total_failures']}")
        print(f"     Incidentes criados: {stats['failures']['incidents_created']}")
        print(f"     Falhas recorrentes: {stats['failures']['recurring_incidents']}")
        
        print(f"   Ações Corretivas:")
        print(f"     Total: {stats['actions']['total_actions']}")
        print(f"     Pendentes: {stats['actions']['pending_actions']}")
        print(f"     Concluídas: {stats['actions']['completed_actions']}")
        print(f"     Em atraso: {stats['actions']['overdue_actions']}")
        print(f"     Taxa de conclusão: {stats['actions']['completion_rate']:.1f}%")
        
        print()
    
    def exemplo_integracao_webhook(self):
        """Exemplo: Integração via webhook"""
        print("=== Exemplo: Integração via Webhook ===")
        
        # Simula dados de um webhook
        webhook_data = {
            "error_message": "Database connection pool exhausted",
            "error_code": "DB_POOL_EXHAUSTED",
            "failure_type": "DATABASE_ERROR",
            "metadata": {
                "database": "postgresql",
                "pool_size": 20,
                "active_connections": 20,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        print("📡 Processando webhook...")
        print(f"   Dados recebidos: {json.dumps(webhook_data, indent=2)}")
        
        incident = self.incident_manager.process_failure(
            error_message=webhook_data["error_message"],
            error_code=webhook_data["error_code"],
            failure_type=FailureType(webhook_data["failure_type"]),
            metadata=webhook_data["metadata"]
        )
        
        if incident:
            print(f"✅ Incidente processado: ID {incident.id}")
            print(f"   JIRA Ticket: {incident.jira_ticket_id}")
            print(f"   Severidade: {incident.severity}")
        else:
            print("⏳ Falha registrada, aguardando mais ocorrências")
        
        print()
    
    def executar_todos_exemplos(self):
        """Executa todos os exemplos"""
        print("🚀 Executando todos os exemplos do Sistema de Gestão de Incidentes\n")
        
        try:
            self.exemplo_deteccao_falhas_recorrentes()
            self.exemplo_post_mortem_completo()
            self.exemplo_workflow_completo()
            self.exemplo_diferentes_tipos_falhas()
            self.exemplo_estatisticas_detalhadas()
            self.exemplo_integracao_webhook()
            
            print("✅ Todos os exemplos executados com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro durante execução dos exemplos: {e}")
        
        finally:
            self.db_session.close()


def main():
    """Função principal para executar exemplos"""
    examples = IncidentExamples()
    examples.executar_todos_exemplos()


if __name__ == "__main__":
    main()
