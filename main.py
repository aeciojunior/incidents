"""
Aplicação principal do sistema de gestão de incidentes
"""
import sys
import os
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from loguru import logger

# Adiciona o diretório atual ao path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import get_session_factory, FailureType
from incident_manager import IncidentManager
from config import config


def main():
    """Função principal da aplicação"""
    logger.info("Iniciando Sistema de Gestão de Incidentes")
    
    try:
        # Cria sessão do banco de dados
        session_factory = get_session_factory(config.database.database_url)
        db_session = session_factory()
        
        # Inicializa o gerenciador de incidentes
        incident_manager = IncidentManager(db_session)
        
        # Testa integrações
        logger.info("Testando integrações...")
        integration_results = incident_manager.test_integrations()
        
        if not all(integration_results.values()):
            logger.warning("Algumas integrações falharam no teste")
            for integration, status in integration_results.items():
                if not status:
                    logger.error(f"Integração {integration} falhou no teste")
        
        # Inicia processamento em background
        incident_manager.start_background_processing()
        
        logger.info("Sistema iniciado com sucesso!")
        logger.info("Pressione Ctrl+C para parar o sistema")
        
        # Loop principal
        try:
            while True:
                # Aqui você pode adicionar lógica para receber falhas
                # Por exemplo, via API, webhook, ou monitoramento de logs
                pass
                
        except KeyboardInterrupt:
            logger.info("Parando sistema...")
            incident_manager.stop_background_processing()
            db_session.close()
            logger.info("Sistema parado com sucesso")
    
    except Exception as e:
        logger.error(f"Erro ao iniciar sistema: {e}")
        sys.exit(1)


def demo_usage():
    """Demonstração de uso do sistema"""
    logger.info("Executando demonstração do sistema")
    
    try:
        # Cria sessão do banco de dados
        session_factory = get_session_factory(config.database.database_url)
        db_session = session_factory()
        
        # Inicializa o gerenciador de incidentes
        incident_manager = IncidentManager(db_session)
        
        # Simula algumas falhas
        logger.info("Simulando falhas...")
        
        # Primeira falha - não deve criar incidente
        incident_manager.process_failure(
            error_message="Connection timeout to database server",
            error_code="DB_TIMEOUT",
            failure_type=FailureType.DATABASE_ERROR,
            metadata={"server": "db-prod-01", "user": "app_user"}
        )
        
        # Segunda falha similar - ainda não deve criar incidente
        incident_manager.process_failure(
            error_message="Connection timeout to database server",
            error_code="DB_TIMEOUT",
            failure_type=FailureType.DATABASE_ERROR,
            metadata={"server": "db-prod-01", "user": "app_user"}
        )
        
        # Terceira falha similar - deve criar incidente
        incident = incident_manager.process_failure(
            error_message="Connection timeout to database server",
            error_code="DB_TIMEOUT",
            failure_type=FailureType.DATABASE_ERROR,
            metadata={"server": "db-prod-01", "user": "app_user"}
        )
        
        if incident:
            logger.info(f"Incidente criado: {incident.id}")
            
            # Cria post-mortem
            post_mortem = incident_manager.create_post_mortem(
                incident_id=incident.id,
                summary="Falhas recorrentes de timeout na conexão com banco de dados",
                root_cause="Configuração inadequada de timeout no pool de conexões",
                impact_assessment="Impacto alto - usuários não conseguem acessar o sistema",
                lessons_learned="Revisar configurações de timeout e implementar retry automático"
            )
            
            if post_mortem:
                logger.info(f"Post-mortem criado: {post_mortem.id}")
                
                # Adiciona ações corretivas
                action1 = incident_manager.add_corrective_action(
                    incident_id=incident.id,
                    title="Ajustar timeout do pool de conexões",
                    description="Aumentar timeout de 30s para 60s no pool de conexões",
                    assigned_to="devops@empresa.com",
                    due_date=datetime.now().replace(hour=18, minute=0, second=0, microsecond=0)
                )
                
                action2 = incident_manager.add_corrective_action(
                    incident_id=incident.id,
                    title="Implementar retry automático",
                    description="Adicionar lógica de retry com backoff exponencial",
                    assigned_to="backend@empresa.com",
                    due_date=datetime.now().replace(hour=18, minute=0, second=0, microsecond=0)
                )
                
                if action1 and action2:
                    logger.info(f"Ações corretivas criadas: {action1.id}, {action2.id}")
        
        # Mostra estatísticas
        stats = incident_manager.get_incident_statistics()
        logger.info(f"Estatísticas: {stats}")
        
        db_session.close()
        logger.info("Demonstração concluída")
    
    except Exception as e:
        logger.error(f"Erro na demonstração: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo_usage()
    else:
        main()
