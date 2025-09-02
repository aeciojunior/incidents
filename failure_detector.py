"""
Sistema de detecção de falhas recorrentes
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from loguru import logger
import hashlib
import json

from models import Incident, Failure, FailureType, IncidentStatus
from config import config


class FailureDetector:
    """Detector de falhas recorrentes"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.failure_threshold = config.incident.failure_threshold
        self.time_window_hours = config.incident.time_window_hours
    
    def _generate_failure_hash(self, error_message: str, error_code: Optional[str] = None) -> str:
        """Gera um hash único para identificar falhas similares"""
        content = f"{error_message}:{error_code or ''}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_similar_failures(
        self, 
        error_message: str, 
        error_code: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> List[Failure]:
        """Busca falhas similares dentro de uma janela de tempo"""
        if time_window is None:
            time_window = timedelta(hours=self.time_window_hours)
        
        cutoff_time = datetime.utcnow() - time_window
        
        # Busca falhas com mensagem de erro similar
        similar_failures = self.db_session.query(Failure).join(Incident).filter(
            and_(
                Failure.error_message.ilike(f"%{error_message[:50]}%"),
                Failure.occurred_at >= cutoff_time,
                Incident.status != IncidentStatus.CLOSED
            )
        ).order_by(desc(Failure.occurred_at)).all()
        
        return similar_failures
    
    def _calculate_similarity_score(self, failure1: Failure, failure2: Failure) -> float:
        """Calcula a similaridade entre duas falhas (0-1)"""
        score = 0.0
        
        # Compara mensagens de erro
        if failure1.error_message and failure2.error_message:
            msg1_words = set(failure1.error_message.lower().split())
            msg2_words = set(failure2.error_message.lower().split())
            if msg1_words and msg2_words:
                intersection = len(msg1_words.intersection(msg2_words))
                union = len(msg1_words.union(msg2_words))
                score += (intersection / union) * 0.6
        
        # Compara códigos de erro
        if failure1.error_code and failure2.error_code:
            if failure1.error_code == failure2.error_code:
                score += 0.4
        
        return score
    
    def _group_similar_failures(self, failures: List[Failure]) -> List[List[Failure]]:
        """Agrupa falhas similares"""
        if not failures:
            return []
        
        groups = []
        processed = set()
        
        for i, failure in enumerate(failures):
            if failure.id in processed:
                continue
            
            group = [failure]
            processed.add(failure.id)
            
            for j, other_failure in enumerate(failures[i+1:], i+1):
                if other_failure.id in processed:
                    continue
                
                similarity = self._calculate_similarity_score(failure, other_failure)
                if similarity > 0.7:  # Threshold de similaridade
                    group.append(other_failure)
                    processed.add(other_failure.id)
            
            groups.append(group)
        
        return groups
    
    def detect_recurring_failures(
        self, 
        error_message: str, 
        error_code: Optional[str] = None,
        failure_type: FailureType = FailureType.OTHER,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Incident]:
        """
        Detecta se uma falha é recorrente e retorna o incidente associado
        ou cria um novo se necessário
        """
        logger.info(f"Analisando falha: {error_message[:100]}...")
        
        # Busca falhas similares
        similar_failures = self._get_similar_failures(error_message, error_code)
        
        if not similar_failures:
            logger.info("Nenhuma falha similar encontrada")
            return None
        
        # Agrupa falhas similares
        failure_groups = self._group_similar_failures(similar_failures)
        
        # Verifica se algum grupo tem o número mínimo de falhas
        for group in failure_groups:
            if len(group) >= self.failure_threshold - 1:  # -1 porque vamos adicionar a nova falha
                # Encontra o incidente mais recente do grupo
                incident_ids = [f.incident_id for f in group if f.incident_id]
                if incident_ids:
                    most_recent_incident = self.db_session.query(Incident).filter(
                        Incident.id.in_(incident_ids)
                    ).order_by(desc(Incident.created_at)).first()
                    
                    if most_recent_incident:
                        logger.info(f"Falha recorrente detectada para incidente {most_recent_incident.id}")
                        return most_recent_incident
        
        # Se chegou até aqui, não é uma falha recorrente
        logger.info("Falha não é recorrente")
        return None
    
    def create_failure_record(
        self,
        error_message: str,
        error_code: Optional[str] = None,
        stack_trace: Optional[str] = None,
        failure_type: FailureType = FailureType.OTHER,
        metadata: Optional[Dict[str, Any]] = None,
        incident_id: Optional[int] = None
    ) -> Failure:
        """Cria um registro de falha"""
        failure = Failure(
            incident_id=incident_id,
            error_message=error_message,
            error_code=error_code,
            stack_trace=stack_trace,
            metadata=metadata or {},
            occurred_at=datetime.utcnow()
        )
        
        self.db_session.add(failure)
        self.db_session.commit()
        
        logger.info(f"Registro de falha criado: {failure.id}")
        return failure
    
    def get_failure_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Retorna estatísticas de falhas"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Total de falhas
        total_failures = self.db_session.query(Failure).filter(
            Failure.occurred_at >= cutoff_date
        ).count()
        
        # Falhas por tipo
        failures_by_type = self.db_session.query(
            func.count(Failure.id).label('count')
        ).join(Incident).filter(
            Failure.occurred_at >= cutoff_date
        ).group_by(Incident.failure_type).all()
        
        # Incidentes criados
        incidents_created = self.db_session.query(Incident).filter(
            Incident.created_at >= cutoff_date
        ).count()
        
        # Falhas recorrentes detectadas
        recurring_incidents = self.db_session.query(Incident).join(Failure).filter(
            and_(
                Incident.created_at >= cutoff_date,
                func.count(Failure.id) >= self.failure_threshold
            )
        ).group_by(Incident.id).count()
        
        return {
            "total_failures": total_failures,
            "incidents_created": incidents_created,
            "recurring_incidents": recurring_incidents,
            "period_days": days,
            "failure_threshold": self.failure_threshold
        }
    
    def cleanup_old_failures(self, days_to_keep: int = 90):
        """Remove falhas antigas para manter o banco limpo"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        old_failures = self.db_session.query(Failure).filter(
            Failure.occurred_at < cutoff_date
        ).all()
        
        for failure in old_failures:
            self.db_session.delete(failure)
        
        self.db_session.commit()
        
        logger.info(f"Removidas {len(old_failures)} falhas antigas")
        return len(old_failures)
