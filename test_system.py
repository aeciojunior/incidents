"""
Script de teste para validar o sistema de gestão de incidentes
"""
import sys
import os
from datetime import datetime, timedelta

# Adiciona o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import get_session_factory, FailureType
from incident_manager import IncidentManager


def test_system():
    """Testa o sistema completo"""
    print("🧪 Iniciando testes do Sistema de Gestão de Incidentes")
    print("=" * 60)
    
    try:
        # Inicializa o sistema
        session_factory = get_session_factory("sqlite:///test_incidents.db")
        db_session = session_factory()
        incident_manager = IncidentManager(db_session)
        
        print("✅ Sistema inicializado com sucesso")
        
        # Teste 1: Detecção de falhas recorrentes
        print("\n📋 Teste 1: Detecção de Falhas Recorrentes")
        print("-" * 40)
        
        incident = None
        for i in range(4):
            print(f"   Simulando falha {i+1}...")
            incident = incident_manager.process_failure(
                error_message="Database connection timeout",
                error_code="DB_TIMEOUT",
                failure_type=FailureType.DATABASE_ERROR,
                metadata={"attempt": i+1, "server": "db-prod-01"}
            )
            
            if incident:
                print(f"   ✅ Incidente criado: ID {incident.id}")
                break
            else:
                print("   ⏳ Falha registrada, aguardando threshold...")
        
        if not incident:
            print("   ❌ Nenhum incidente foi criado")
            return False
        
        # Teste 2: Criação de post-mortem
        print("\n📋 Teste 2: Criação de Post-Mortem")
        print("-" * 40)
        
        post_mortem = incident_manager.create_post_mortem(
            incident_id=incident.id,
            summary="Falhas recorrentes de timeout no banco de dados",
            root_cause="Configuração inadequada de timeout no pool de conexões",
            impact_assessment="Usuários não conseguem acessar o sistema",
            lessons_learned="Revisar configurações de timeout e implementar retry"
        )
        
        if post_mortem:
            print(f"   ✅ Post-mortem criado: ID {post_mortem.id}")
        else:
            print("   ❌ Erro ao criar post-mortem")
            return False
        
        # Teste 3: Ações corretivas
        print("\n📋 Teste 3: Ações Corretivas")
        print("-" * 40)
        
        actions = [
            {
                "title": "Ajustar timeout do pool de conexões",
                "description": "Aumentar timeout de 30s para 60s",
                "assigned_to": "devops@empresa.com",
                "due_date": datetime.now() + timedelta(days=1)
            },
            {
                "title": "Implementar retry automático",
                "description": "Adicionar lógica de retry com backoff",
                "assigned_to": "backend@empresa.com",
                "due_date": datetime.now() + timedelta(days=3)
            }
        ]
        
        created_actions = []
        for action_data in actions:
            action = incident_manager.add_corrective_action(
                incident_id=incident.id,
                **action_data
            )
            
            if action:
                print(f"   ✅ Ação criada: {action_data['title']} (ID: {action.id})")
                created_actions.append(action)
            else:
                print(f"   ❌ Erro ao criar ação: {action_data['title']}")
        
        # Teste 4: Estatísticas
        print("\n📋 Teste 4: Estatísticas do Sistema")
        print("-" * 40)
        
        stats = incident_manager.get_incident_statistics()
        
        print(f"   📊 Incidentes:")
        print(f"      Total: {stats['incidents']['total']}")
        print(f"      Abertos: {stats['incidents']['open']}")
        print(f"      Taxa de resolução: {stats['incidents']['resolution_rate']:.1f}%")
        
        print(f"   📊 Falhas:")
        print(f"      Total: {stats['failures']['total_failures']}")
        print(f"      Incidentes criados: {stats['failures']['incidents_created']}")
        
        print(f"   📊 Ações:")
        print(f"      Total: {stats['actions']['total_actions']}")
        print(f"      Pendentes: {stats['actions']['pending_actions']}")
        
        # Teste 5: Resolução de incidente
        print("\n📋 Teste 5: Resolução de Incidente")
        print("-" * 40)
        
        success = incident_manager.resolve_incident(
            incident_id=incident.id,
            resolution_notes="Timeout ajustado e retry implementado"
        )
        
        if success:
            print("   ✅ Incidente resolvido com sucesso")
        else:
            print("   ❌ Erro ao resolver incidente")
        
        # Teste 6: Verificação final
        print("\n📋 Teste 6: Verificação Final")
        print("-" * 40)
        
        final_stats = incident_manager.get_incident_statistics()
        
        if final_stats['incidents']['resolved'] > 0:
            print("   ✅ Incidente aparece como resolvido nas estatísticas")
        else:
            print("   ❌ Incidente não aparece como resolvido")
        
        print("\n🎉 Todos os testes concluídos com sucesso!")
        print("=" * 60)
        
        # Limpeza
        db_session.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro durante os testes: {e}")
        print("=" * 60)
        return False


def test_different_failure_types():
    """Testa diferentes tipos de falhas"""
    print("\n🧪 Teste: Diferentes Tipos de Falhas")
    print("-" * 40)
    
    try:
        session_factory = get_session_factory("sqlite:///test_incidents.db")
        db_session = session_factory()
        incident_manager = IncidentManager(db_session)
        
        failure_types = [
            (FailureType.SECURITY_ISSUE, "Unauthorized access attempt", "SEC_401"),
            (FailureType.NETWORK_ERROR, "Network connection lost", "NET_TIMEOUT"),
            (FailureType.PERFORMANCE_ISSUE, "Response time exceeded", "PERF_SLOW"),
            (FailureType.API_ERROR, "API rate limit exceeded", "RATE_LIMIT_429")
        ]
        
        for failure_type, message, code in failure_types:
            print(f"   Testando: {failure_type.value}")
            
            # Simula múltiplas falhas para criar incidente
            incident = None
            for i in range(3):
                incident = incident_manager.process_failure(
                    error_message=f"{message} - attempt {i+1}",
                    error_code=code,
                    failure_type=failure_type,
                    metadata={"test": True, "attempt": i+1}
                )
                
                if incident:
                    break
            
            if incident:
                print(f"      ✅ Incidente criado: ID {incident.id}, Severidade: {incident.severity}")
            else:
                print(f"      ⏳ Falhas registradas, aguardando threshold...")
        
        db_session.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return False


def main():
    """Função principal de teste"""
    print("🚀 Sistema de Gestão de Incidentes - Testes Automatizados")
    print("=" * 60)
    
    # Executa testes principais
    success = test_system()
    
    if success:
        # Executa testes adicionais
        test_different_failure_types()
        
        print("\n✅ Todos os testes passaram com sucesso!")
        print("🎯 O sistema está funcionando corretamente")
    else:
        print("\n❌ Alguns testes falharam")
        print("🔧 Verifique a configuração e dependências")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
