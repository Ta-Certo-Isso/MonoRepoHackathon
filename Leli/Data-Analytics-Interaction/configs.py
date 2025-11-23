# Importa bibliotecas padrão para manipulação de sistema e banco de dados
import os
import sys

import duckdb as db

# Pega o diretório onde está o próprio config.py (a raiz do projeto)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Função que adiciona os caminhos das pastas do projeto ao sys.path
def mapeia_pastas():
    pastas = ["database", "models", "src", "utils", "tests"]
    # Adiciona cada pasta no sys.path para que os módulos possam ser importados de qualquer lugar do projeto
    for p in pastas:
        caminho = os.path.join(BASE_DIR, p)
        sys.path.append(caminho)


# Função que cria uma conexão com o banco de dados DuckDB utilizado no projeto
def criar_conexao_db():
    # Constrói o caminho completo a partir da raiz do projeto (BASE_DIR)
    db_path = os.path.join(
        BASE_DIR,
        "database",  # A pasta onde o arquivo .db está
        "governo_interact.db",
    )

    # A variável 'db_path' agora contém o caminho absoluto correto
    con = db.connect(db_path)
    return con
