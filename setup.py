"""
Script de configuração inicial do Sistema de Gestão de Incidentes
"""
import os
import sys
import subprocess
from pathlib import Path


def check_python_version():
    """Verifica se a versão do Python é compatível"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ é necessário")
        print(f"   Versão atual: {sys.version}")
        return False
    
    print(f"✅ Python {sys.version.split()[0]} - Compatível")
    return True


def install_dependencies():
    """Instala as dependências do projeto"""
    print("\n📦 Instalando dependências...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✅ Dependências instaladas com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar dependências: {e}")
        return False


def create_directories():
    """Cria diretórios necessários"""
    print("\n📁 Criando diretórios...")
    
    directories = ["data", "logs", "backups"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"   ✅ Diretório '{directory}' criado")
    
    return True


def create_env_file():
    """Cria arquivo .env se não existir"""
    print("\n⚙️ Configurando arquivo de ambiente...")
    
    env_file = Path(".env")
    env_example = Path("env_example.txt")
    
    if env_file.exists():
        print("   ✅ Arquivo .env já existe")
        return True
    
    if not env_example.exists():
        print("   ❌ Arquivo env_example.txt não encontrado")
        return False
    
    # Copia o arquivo de exemplo
    with open(env_example, 'r') as src, open(env_file, 'w') as dst:
        dst.write(src.read())
    
    print("   ✅ Arquivo .env criado a partir do exemplo")
    print("   ⚠️  Configure as variáveis de ambiente no arquivo .env")
    
    return True


def test_database_connection():
    """Testa a conexão com o banco de dados"""
    print("\n🗄️ Testando conexão com banco de dados...")
    
    try:
        from models import get_session_factory
        from config import config
        
        session_factory = get_session_factory(config.database.database_url)
        session = session_factory()
        session.close()
        
        print("   ✅ Conexão com banco de dados OK")
        return True
    except Exception as e:
        print(f"   ❌ Erro na conexão com banco: {e}")
        return False


def test_integrations():
    """Testa as integrações externas"""
    print("\n🔗 Testando integrações...")
    
    try:
        from models import get_session_factory
        from incident_manager import IncidentManager
        from config import config
        
        session_factory = get_session_factory(config.database.database_url)
        session = session_factory()
        incident_manager = IncidentManager(session)
        
        results = incident_manager.test_integrations()
        
        for integration, status in results.items():
            if status:
                print(f"   ✅ {integration.upper()}: OK")
            else:
                print(f"   ⚠️  {integration.upper()}: Falhou (verifique configuração)")
        
        session.close()
        return True
    except Exception as e:
        print(f"   ❌ Erro ao testar integrações: {e}")
        return False


def run_demo():
    """Executa uma demonstração do sistema"""
    print("\n🎬 Executando demonstração...")
    
    try:
        subprocess.check_call([sys.executable, "main.py", "demo"])
        print("   ✅ Demonstração executada com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Erro na demonstração: {e}")
        return False


def main():
    """Função principal de configuração"""
    print("🚀 Sistema de Gestão de Incidentes - Configuração Inicial")
    print("=" * 60)
    
    steps = [
        ("Verificação do Python", check_python_version),
        ("Instalação de dependências", install_dependencies),
        ("Criação de diretórios", create_directories),
        ("Configuração de ambiente", create_env_file),
        ("Teste de banco de dados", test_database_connection),
        ("Teste de integrações", test_integrations),
    ]
    
    success_count = 0
    
    for step_name, step_function in steps:
        print(f"\n📋 {step_name}")
        print("-" * 40)
        
        if step_function():
            success_count += 1
        else:
            print(f"   ⚠️  {step_name} falhou")
    
    print("\n" + "=" * 60)
    print(f"📊 Resumo: {success_count}/{len(steps)} etapas concluídas")
    
    if success_count == len(steps):
        print("✅ Configuração concluída com sucesso!")
        print("\n🎯 Próximos passos:")
        print("   1. Configure as variáveis no arquivo .env")
        print("   2. Execute: python main.py demo")
        print("   3. Execute: python main.py (para iniciar o sistema)")
        print("   4. Execute: python api_example.py (para API REST)")
        
        # Pergunta se quer executar a demo
        try:
            response = input("\n🎬 Executar demonstração agora? (s/n): ").lower()
            if response in ['s', 'sim', 'y', 'yes']:
                run_demo()
        except KeyboardInterrupt:
            print("\n   Configuração finalizada")
    
    else:
        print("❌ Configuração incompleta")
        print("   Verifique os erros acima e tente novamente")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
