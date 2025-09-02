# 🚀 Guia de Início Rápido

## Instalação e Configuração em 5 Minutos

### 1. Pré-requisitos
- Python 3.8+
- Acesso a JIRA (opcional)
- Servidor SMTP para emails (opcional)

### 2. Instalação Automática
```bash
# Clone ou baixe os arquivos
# Execute o script de configuração
python setup.py
```

### 3. Configuração Manual (se necessário)
```bash
# Instalar dependências
pip install -r requirements.txt

# Copiar arquivo de configuração
cp env_example.txt .env

# Editar configurações
nano .env
```

### 4. Configuração Mínima (.env)
```env
# Configurações obrigatórias
DATABASE_URL=sqlite:///incidents.db
LOG_LEVEL=INFO

# JIRA (opcional)
JIRA_URL=https://seu-dominio.atlassian.net
JIRA_USERNAME=seu-email@empresa.com
JIRA_API_TOKEN=seu-token
JIRA_PROJECT_KEY=PROJ

# Email (opcional)
SMTP_SERVER=smtp.gmail.com
EMAIL_USERNAME=seu-email@gmail.com
EMAIL_PASSWORD=sua-senha-app
FROM_EMAIL=seu-email@gmail.com
```

### 5. Teste Rápido
```bash
# Executar demonstração
python main.py demo

# Executar testes
python test_system.py
```

### 6. Uso Básico
```python
from models import get_session_factory, FailureType
from incident_manager import IncidentManager

# Inicializar
session_factory = get_session_factory("sqlite:///incidents.db")
db_session = session_factory()
incident_manager = IncidentManager(db_session)

# Reportar falha
incident = incident_manager.process_failure(
    error_message="Database connection timeout",
    error_code="DB_TIMEOUT",
    failure_type=FailureType.DATABASE_ERROR
)
```

### 7. API REST
```bash
# Iniciar API
python api_example.py

# Testar API
curl http://localhost:5000/health
curl -X POST http://localhost:5000/api/failures \
  -H "Content-Type: application/json" \
  -d '{"error_message": "Test error", "failure_type": "SYSTEM_ERROR"}'
```

### 8. Docker (Opcional)
```bash
# Com Docker Compose
docker-compose up -d

# Com Docker
docker build -t incidents-system .
docker run -p 5000:5000 --env-file .env incidents-system
```

## 🎯 Casos de Uso Comuns

### Monitoramento de Aplicação
```python
# Integrar com seu sistema de logs
import logging

class IncidentHandler(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.ERROR:
            incident_manager.process_failure(
                error_message=record.getMessage(),
                failure_type=FailureType.SYSTEM_ERROR,
                metadata={"logger": record.name, "level": record.levelname}
            )

# Adicionar ao logger
logger = logging.getLogger()
logger.addHandler(IncidentHandler())
```

### Webhook para Falhas
```python
from flask import Flask, request

app = Flask(__name__)

@app.route('/webhook/failure', methods=['POST'])
def handle_failure():
    data = request.json
    incident = incident_manager.process_failure(
        error_message=data['error_message'],
        error_code=data.get('error_code'),
        failure_type=FailureType(data.get('failure_type', 'OTHER'))
    )
    return {'incident_id': incident.id if incident else None}
```

### Monitoramento de Performance
```python
import time
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            # Reporta falha
            incident_manager.process_failure(
                error_message=str(e),
                failure_type=FailureType.SYSTEM_ERROR,
                metadata={"function": func.__name__, "args": str(args)}
            )
            raise
        finally:
            duration = time.time() - start_time
            if duration > 5.0:  # Mais de 5 segundos
                incident_manager.process_failure(
                    error_message=f"Function {func.__name__} took {duration:.2f}s",
                    failure_type=FailureType.PERFORMANCE_ISSUE,
                    metadata={"function": func.__name__, "duration": duration}
                )
    return wrapper
```

## 🔧 Troubleshooting

### Problemas Comuns

1. **Erro de importação**
   ```bash
   # Verificar se está no diretório correto
   ls -la *.py
   
   # Instalar dependências
   pip install -r requirements.txt
   ```

2. **Erro de banco de dados**
   ```bash
   # Verificar permissões
   ls -la incidents.db
   
   # Recriar banco
   rm incidents.db
   python main.py demo
   ```

3. **Erro de JIRA**
   ```bash
   # Testar conexão
   python -c "from jira_integration import JiraIntegration; JiraIntegration().test_connection()"
   ```

4. **Erro de email**
   ```bash
   # Testar SMTP
   python -c "from email_notifier import EmailNotifier; EmailNotifier(session).test_email_connection()"
   ```

### Logs
```bash
# Ver logs em tempo real
tail -f incidents.log

# Logs com filtro
grep "ERROR" incidents.log
```

## 📚 Recursos Adicionais

- **Documentação completa**: README.md
- **Exemplos práticos**: examples.py
- **API REST**: api_example.py
- **Testes**: test_system.py
- **Docker**: Dockerfile, docker-compose.yml

## 🆘 Suporte

- **Issues**: Abra uma issue no GitHub
- **Email**: incidents@empresa.com
- **Documentação**: Consulte README.md para detalhes completos
