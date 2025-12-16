from db import get_mongo_db
from pymongo import ASCENDING, DESCENDING

def criar_indices():
    db = get_mongo_db()
    print("--- Iniciando Otimização de Índices ---")

    print("Indexando Turma...")
    db.turma.create_index([("id_instituicao", ASCENDING), ("data_hora_criacao", DESCENDING)])
    db.turma.create_index([("id_instituicao", ASCENDING), ("status", ASCENDING)])

    print("Indexando Curso...")
    db.curso.create_index([("instituicao_id", ASCENDING), ("nome", ASCENDING)])

    print("Indexando Instrutor...")
    db.instrutor.create_index([("instituicao_id", ASCENDING), ("nome", ASCENDING)])

    print("Indexando Unidade Curricular...")
    db.unidade_curricular.create_index([("instituicao_id", ASCENDING), ("descricao", ASCENDING)])

    print("Indexando Calendário...")
    db.calendario.create_index([("id_instituicao", ASCENDING), ("data_inicial", DESCENDING)])

    print("Indexando Empresa...")
    db.empresa.create_index([("instituicao_id", ASCENDING), ("razao_social", ASCENDING)])

    print("Indexando Usuário...")
    db.usuario.create_index([("instituicao_id", ASCENDING), ("user_name", ASCENDING)])
    db.usuario.create_index([("user_name_lc", ASCENDING)], unique=True)

    print("\n✅ Sucesso! Todos os índices foram criados e o banco está otimizado.")

if __name__ == "__main__":
    criar_indices()