"""
Exemplo de API REST para o Sistema de Gestão de Incidentes
"""
from flask import Flask, request, jsonify
from datetime import datetime
from typing import Dict, Any
import json

from models import get_session_factory, FailureType, ActionStatus
from incident_manager import IncidentManager
from config import config

app = Flask(__name__)

# Inicialização global
session_factory = get_session_factory(config.database.database_url)
db_session = session_factory()
incident_manager = IncidentManager(db_session)


@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de health check"""
    try:
        # Testa integrações
        integrations = incident_manager.test_integrations()
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "integrations": integrations
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/failures', methods=['POST'])
def report_failure():
    """Endpoint para reportar falhas"""
    try:
        data = request.get_json()
        
        # Validação básica
        if not data or 'error_message' not in data:
            return jsonify({
                "error": "error_message é obrigatório"
            }), 400
        
        # Processa a falha
        incident = incident_manager.process_failure(
            error_message=data['error_message'],
            error_code=data.get('error_code'),
            stack_trace=data.get('stack_trace'),
            failure_type=FailureType(data.get('failure_type', 'OTHER')),
            metadata=data.get('metadata', {})
        )
        
        response = {
            "success": True,
            "incident_created": incident is not None,
            "incident_id": incident.id if incident else None,
            "jira_ticket_id": incident.jira_ticket_id if incident else None,
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(response), 201 if incident else 200
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/incidents', methods=['GET'])
def get_incidents():
    """Endpoint para listar incidentes"""
    try:
        # Parâmetros de query
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Busca incidentes
        query = db_session.query(Incident)
        
        if status:
            query = query.filter(Incident.status == status)
        
        incidents = query.offset(offset).limit(limit).all()
        
        result = []
        for incident in incidents:
            # Conta falhas associadas
            failure_count = db_session.query(Failure).filter(
                Failure.incident_id == incident.id
            ).count()
            
            result.append({
                "id": incident.id,
                "title": incident.title,
                "description": incident.description,
                "failure_type": incident.failure_type,
                "severity": incident.severity,
                "status": incident.status,
                "jira_ticket_id": incident.jira_ticket_id,
                "created_at": incident.created_at.isoformat(),
                "updated_at": incident.updated_at.isoformat(),
                "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
                "failure_count": failure_count
            })
        
        return jsonify({
            "incidents": result,
            "total": len(result),
            "offset": offset,
            "limit": limit
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/incidents/<int:incident_id>', methods=['GET'])
def get_incident(incident_id: int):
    """Endpoint para obter detalhes de um incidente"""
    try:
        incident = db_session.query(Incident).filter(
            Incident.id == incident_id
        ).first()
        
        if not incident:
            return jsonify({
                "error": "Incidente não encontrado"
            }), 404
        
        # Busca falhas associadas
        failures = db_session.query(Failure).filter(
            Failure.incident_id == incident_id
        ).all()
        
        # Busca post-mortem
        post_mortem = incident_manager.post_mortem_manager.get_post_mortem(incident_id)
        
        # Busca ações corretivas
        actions = incident_manager.post_mortem_manager.get_incident_actions(incident_id)
        
        result = {
            "id": incident.id,
            "title": incident.title,
            "description": incident.description,
            "failure_type": incident.failure_type,
            "severity": incident.severity,
            "status": incident.status,
            "jira_ticket_id": incident.jira_ticket_id,
            "created_at": incident.created_at.isoformat(),
            "updated_at": incident.updated_at.isoformat(),
            "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
            "failures": [
                {
                    "id": f.id,
                    "error_message": f.error_message,
                    "error_code": f.error_code,
                    "occurred_at": f.occurred_at.isoformat(),
                    "metadata": f.metadata
                }
                for f in failures
            ],
            "post_mortem": {
                "id": post_mortem.id,
                "summary": post_mortem.summary,
                "root_cause": post_mortem.root_cause,
                "impact_assessment": post_mortem.impact_assessment,
                "lessons_learned": post_mortem.lessons_learned,
                "created_at": post_mortem.created_at.isoformat()
            } if post_mortem else None,
            "actions": [
                {
                    "id": a.id,
                    "title": a.title,
                    "description": a.description,
                    "status": a.status,
                    "assigned_to": a.assigned_to,
                    "due_date": a.due_date.isoformat() if a.due_date else None,
                    "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                    "created_at": a.created_at.isoformat()
                }
                for a in actions
            ]
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/incidents/<int:incident_id>/post-mortem', methods=['POST'])
def create_post_mortem(incident_id: int):
    """Endpoint para criar post-mortem"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "Dados do post-mortem são obrigatórios"
            }), 400
        
        required_fields = ['summary', 'root_cause', 'impact_assessment', 'lessons_learned']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "error": f"Campo '{field}' é obrigatório"
                }), 400
        
        post_mortem = incident_manager.create_post_mortem(
            incident_id=incident_id,
            summary=data['summary'],
            root_cause=data['root_cause'],
            impact_assessment=data['impact_assessment'],
            lessons_learned=data['lessons_learned']
        )
        
        if not post_mortem:
            return jsonify({
                "error": "Erro ao criar post-mortem"
            }), 500
        
        return jsonify({
            "success": True,
            "post_mortem_id": post_mortem.id,
            "timestamp": datetime.now().isoformat()
        }), 201
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/incidents/<int:incident_id>/actions', methods=['POST'])
def add_corrective_action(incident_id: int):
    """Endpoint para adicionar ação corretiva"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "Dados da ação são obrigatórios"
            }), 400
        
        required_fields = ['title', 'description']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "error": f"Campo '{field}' é obrigatório"
                }), 400
        
        action = incident_manager.add_corrective_action(
            incident_id=incident_id,
            title=data['title'],
            description=data['description'],
            assigned_to=data.get('assigned_to'),
            due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None
        )
        
        if not action:
            return jsonify({
                "error": "Erro ao criar ação corretiva"
            }), 500
        
        return jsonify({
            "success": True,
            "action_id": action.id,
            "timestamp": datetime.now().isoformat()
        }), 201
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/actions/<int:action_id>/status', methods=['PUT'])
def update_action_status(action_id: int):
    """Endpoint para atualizar status de ação"""
    try:
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({
                "error": "Status é obrigatório"
            }), 400
        
        try:
            status = ActionStatus(data['status'])
        except ValueError:
            return jsonify({
                "error": f"Status inválido. Valores aceitos: {[s.value for s in ActionStatus]}"
            }), 400
        
        success = incident_manager.post_mortem_manager.update_action_status(
            action_id=action_id,
            status=status,
            notes=data.get('notes')
        )
        
        if not success:
            return jsonify({
                "error": "Erro ao atualizar status da ação"
            }), 500
        
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/incidents/<int:incident_id>/resolve', methods=['POST'])
def resolve_incident(incident_id: int):
    """Endpoint para resolver incidente"""
    try:
        data = request.get_json() or {}
        
        success = incident_manager.resolve_incident(
            incident_id=incident_id,
            resolution_notes=data.get('resolution_notes')
        )
        
        if not success:
            return jsonify({
                "error": "Erro ao resolver incidente"
            }), 500
        
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Endpoint para obter estatísticas"""
    try:
        stats = incident_manager.get_incident_statistics()
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/actions/pending', methods=['GET'])
def get_pending_actions():
    """Endpoint para obter ações pendentes"""
    try:
        assigned_to = request.args.get('assigned_to')
        actions = incident_manager.post_mortem_manager.get_pending_actions(assigned_to)
        
        result = [
            {
                "id": a.id,
                "title": a.title,
                "description": a.description,
                "status": a.status,
                "assigned_to": a.assigned_to,
                "due_date": a.due_date.isoformat() if a.due_date else None,
                "incident_id": a.incident_id,
                "created_at": a.created_at.isoformat()
            }
            for a in actions
        ]
        
        return jsonify({
            "actions": result,
            "total": len(result)
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/actions/overdue', methods=['GET'])
def get_overdue_actions():
    """Endpoint para obter ações em atraso"""
    try:
        actions = incident_manager.post_mortem_manager.get_overdue_actions()
        
        result = [
            {
                "id": a.id,
                "title": a.title,
                "description": a.description,
                "status": a.status,
                "assigned_to": a.assigned_to,
                "due_date": a.due_date.isoformat() if a.due_date else None,
                "incident_id": a.incident_id,
                "created_at": a.created_at.isoformat(),
                "days_overdue": (datetime.now() - a.due_date).days if a.due_date else 0
            }
            for a in actions
        ]
        
        return jsonify({
            "actions": result,
            "total": len(result)
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handler para 404"""
    return jsonify({
        "error": "Endpoint não encontrado",
        "timestamp": datetime.now().isoformat()
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handler para 500"""
    return jsonify({
        "error": "Erro interno do servidor",
        "timestamp": datetime.now().isoformat()
    }), 500


if __name__ == '__main__':
    print("🚀 Iniciando API do Sistema de Gestão de Incidentes")
    print("📚 Documentação da API:")
    print("   GET  /health                    - Health check")
    print("   POST /api/failures              - Reportar falha")
    print("   GET  /api/incidents             - Listar incidentes")
    print("   GET  /api/incidents/<id>        - Obter incidente")
    print("   POST /api/incidents/<id>/post-mortem - Criar post-mortem")
    print("   POST /api/incidents/<id>/actions - Adicionar ação")
    print("   PUT  /api/actions/<id>/status   - Atualizar status")
    print("   POST /api/incidents/<id>/resolve - Resolver incidente")
    print("   GET  /api/statistics            - Estatísticas")
    print("   GET  /api/actions/pending       - Ações pendentes")
    print("   GET  /api/actions/overdue       - Ações em atraso")
    print()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
