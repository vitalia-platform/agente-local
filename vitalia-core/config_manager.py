import os
from pathlib import Path
from dotenv import load_dotenv

class VitaliaConfig:
    """
    Gerenciador centralizado de configurações e caminhos dinâmicos do projeto.
    Substitui a prática de caminhos 'chumbados' no código (hardcoded).
    """
    def __init__(self):
        # Resolve a raiz do projeto (supondo que este arquivo está em vitalia-core/)
        self.base_dir = Path(__file__).resolve().parent.parent

        # Carrega variáveis de ambiente (mantendo compatibilidade)
        env_path = self.base_dir / '.env'
        if env_path.exists():
            load_dotenv(env_path)

        # Diretórios fundamentais do SDD / Kit v0.4.0
        self.memory_dir = self.base_dir / '.vitalia' / 'memory'
        self.skills_dir = self.base_dir / '.agents' / 'skills'
        
        # Subdiretórios específicos
        self.shards_dir = self.memory_dir / 'data_storage' / 'shards'
        self.session_dir = self.memory_dir / 'session'
        
        # Arquivos vitais
        self.machines_file = self.session_dir / 'machines.json'
        self.pipeline_file = self.base_dir / '.vitalia' / 'pipeline.json'

        # Garante a existência dos diretórios de armazenamento dinamicamente
        self.shards_dir.mkdir(parents=True, exist_ok=True)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def get_redis_url(self) -> str:
        redis_pass = os.getenv("REDIS_PASSWORD", "secret")
        redis_port = os.getenv("REDIS_PORT", "6379")
        return f"redis://:{redis_pass}@localhost:{redis_port}/0"

# Instância Singleton para importar em outros arquivos
config = VitaliaConfig()
