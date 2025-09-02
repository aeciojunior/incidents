# Sistema de Gestão de Incidentes

Uma solução robusta e confiável em Python para gestão automatizada de incidentes, com integração ao JIRA e sistema de follow-up de post-mortems.

## 🚀 Funcionalidades

### ✅ Detecção Automática de Falhas Recorrentes
- Sistema inteligente que detecta padrões de falhas similares
- Criação automática de incidentes quando o threshold é atingido
- Análise de similaridade baseada em mensagens de erro e códigos
- Configuração flexível de janelas de tempo e limites

### 🎫 Integração com JIRA
- Criação automática de tickets para falhas recorrentes
- Atualização automática de tickets existentes com novas ocorrências
- Priorização inteligente baseada na severidade e frequência
- Fechamento automático de tickets quando incidentes são resolvidos

### 📋 Sistema de Post-Mortems
- Criação estruturada de post-mortems para incidentes
- Tracking completo de ações corretivas
- Status de progresso das ações (Pendente, Em Progresso, Concluída)
- Relatórios detalhados de post-mortems

### 📧 Sistema de Lembretes por Email
- Lembretes automáticos para ações corretivas pendentes
- Notificações de ações em atraso
- Resumos semanais de atividades
- Templates de email profissionais e informativos

### 📊 Monitoramento e Estatísticas
- Dashboard com estatísticas em tempo real
- Métricas de resolução de incidentes
- Tracking de ações corretivas
- Relatórios de performance

## 🛠️ Instalação

### Pré-requisitos
- Python 3.8+
- Acesso a um servidor JIRA
- Servidor SMTP para envio de emails
- SQLite (padrão) ou outro banco de dados suportado pelo SQLAlchemy

### Instalação das Dependências

```bash
pip install -r requirements.txt
```

### Configuração

1. Copie o arquivo de exemplo de configuração:
```bash
cp env_example.txt .env
```

2. Configure as variáveis de ambiente no arquivo `.env`:

```env
# Configurações do JIRA
JIRA_URL=https://seu-dominio.atlassian.net
JIRA_USERNAME=seu-email@empresa.com
JIRA_API_TOKEN=seu-token-api-jira
JIRA_PROJECT_KEY=PROJ
JIRA_ISSUE_TYPE=Bug

# Configurações de Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USERNAME=seu-email@gmail.com
EMAIL_PASSWORD=sua-senha-app
FROM_EMAIL=seu-email@gmail.com
USE_TLS=true

# Configurações do Banco de Dados
DATABASE_URL=sqlite:///incidents.db

# Configurações de Incidentes
FAILURE_THRESHOLD=3
TIME_WINDOW_HOURS=24
REMINDER_DAYS=7,14,30

# Configurações de Log
LOG_LEVEL=INFO
LOG_FILE=incidents.log
```

### Obtenção do Token JIRA

1. Acesse: https://id.atlassian.com/manage-profile/security/api-tokens
2. Clique em "Create API token"
3. Dê um nome ao token e copie o valor gerado
4. Use este token na variável `JIRA_API_TOKEN`

## 🚀 Uso

### Execução Básica

```bash
python main.py
```

### Demonstração

```bash
python main.py demo
```

### Uso Programático

```python
from models import get_session_factory, FailureType
from incident_manager import IncidentManager
from datetime import datetime

# Inicialização
session_factory = get_session_factory("sqlite:///incidents.db")
db_session = session_factory()
incident_manager = IncidentManager(db_session)

# Processamento de uma falha
incident = incident_manager.process_failure(
    error_message="Connection timeout to database server",
    error_code="DB_TIMEOUT",
    failure_type=FailureType.DATABASE_ERROR,
    metadata={"server": "db-prod-01", "user": "app_user"}
)

# Criação de post-mortem
if incident:
    post_mortem = incident_manager.create_post_mortem(
        incident_id=incident.id,
        summary="Falhas recorrentes de timeout na conexão com banco de dados",
        root_cause="Configuração inadequada de timeout no pool de conexões",
        impact_assessment="Impacto alto - usuários não conseguem acessar o sistema",
        lessons_learned="Revisar configurações de timeout e implementar retry automático"
    )
    
    # Adição de ações corretivas
    action = incident_manager.add_corrective_action(
        incident_id=incident.id,
        title="Ajustar timeout do pool de conexões",
        description="Aumentar timeout de 30s para 60s no pool de conexões",
        assigned_to="devops@empresa.com",
        due_date=datetime.now().replace(hour=18, minute=0, second=0, microsecond=0)
    )
```

## 📁 Estrutura do Projeto

```
incidents/
├── main.py                 # Aplicação principal
├── config.py              # Configurações do sistema
├── models.py              # Modelos de dados (SQLAlchemy + Pydantic)
├── failure_detector.py    # Sistema de detecção de falhas
├── jira_integration.py    # Integração com JIRA
├── post_mortem_manager.py # Gerenciamento de post-mortems
├── email_notifier.py      # Sistema de notificações por email
├── incident_manager.py    # Gerenciador principal
├── requirements.txt       # Dependências Python
├── env_example.txt        # Exemplo de configuração
└── README.md             # Esta documentação
```

## ⚙️ Configurações Avançadas

### Tipos de Falhas Suportados

- `SYSTEM_ERROR`: Erros de sistema
- `NETWORK_ERROR`: Erros de rede
- `DATABASE_ERROR`: Erros de banco de dados
- `API_ERROR`: Erros de API
- `PERFORMANCE_ISSUE`: Problemas de performance
- `SECURITY_ISSUE`: Problemas de segurança
- `OTHER`: Outros tipos

### Configuração de Thresholds

- `FAILURE_THRESHOLD`: Número mínimo de falhas para criar incidente (padrão: 3)
- `TIME_WINDOW_HOURS`: Janela de tempo para análise de falhas (padrão: 24h)
- `REMINDER_DAYS`: Dias para envio de lembretes (padrão: 7, 14, 30)

### Configuração de Severidade

A severidade é determinada automaticamente baseada em:
- Tipo de falha
- Número de ocorrências
- Impacto estimado

## 🔧 API e Integração

### Webhook para Falhas

O sistema pode ser integrado via webhook para receber falhas automaticamente:

```python
from flask import Flask, request
from incident_manager import IncidentManager

app = Flask(__name__)

@app.route('/webhook/failure', methods=['POST'])
def handle_failure():
    data = request.json
    
    incident = incident_manager.process_failure(
        error_message=data['error_message'],
        error_code=data.get('error_code'),
        failure_type=FailureType(data.get('failure_type', 'OTHER')),
        metadata=data.get('metadata', {})
    )
    
    return {'incident_id': incident.id if incident else None}
```

### Integração com Sistemas de Monitoramento

```python
# Exemplo de integração com Prometheus/Grafana
import requests

def send_metrics_to_prometheus():
    stats = incident_manager.get_incident_statistics()
    
    # Envia métricas para Prometheus
    requests.post('http://prometheus:9091/metrics/job/incidents', data={
        'incidents_total': stats['incidents']['total'],
        'incidents_open': stats['incidents']['open'],
        'actions_pending': stats['actions']['pending_actions']
    })
```

## 📊 Monitoramento

### Logs

O sistema gera logs estruturados em:
- Arquivo: `incidents.log` (rotacionado diariamente)
- Console: Para desenvolvimento
- Níveis: DEBUG, INFO, WARNING, ERROR

### Métricas Disponíveis

- Total de incidentes
- Taxa de resolução
- Ações pendentes/concluídas
- Falhas por tipo
- Tempo médio de resolução

## 🚨 Troubleshooting

### Problemas Comuns

1. **Erro de conexão com JIRA**
   - Verifique URL, username e token
   - Teste com: `python -c "from jira_integration import JiraIntegration; JiraIntegration().test_connection()"`

2. **Erro de envio de email**
   - Verifique configurações SMTP
   - Para Gmail, use senha de app específica
   - Teste com: `python -c "from email_notifier import EmailNotifier; EmailNotifier(session).test_email_connection()"`

3. **Problemas de banco de dados**
   - Verifique permissões de escrita
   - Para SQLite, verifique se o arquivo pode ser criado

### Logs de Debug

Para ativar logs detalhados:
```env
LOG_LEVEL=DEBUG
```

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 📞 Suporte

Para suporte e dúvidas:
- Abra uma issue no GitHub
- Entre em contato: incidents@empresa.com

## 🔄 Roadmap

- [ ] Interface web para gestão
- [ ] Integração com Slack/Teams
- [ ] Dashboard em tempo real
- [ ] Machine Learning para detecção de padrões
- [ ] API REST completa
- [ ] Integração com mais ferramentas de monitoramento
