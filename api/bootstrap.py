from fastapi import APIRouter, Depends, Response
from db import get_mongo_db
from auth_dep import get_ctx, RequestCtx
from cache_utils import get_version_hash

router = APIRouter()

@router.get("/api/bootstrap")
def get_bootstrap_data(response: Response, ctx: RequestCtx = Depends(get_ctx)):
    db = get_mongo_db()
    inst_str = str(ctx.inst_oid) 
    inst_oid = ctx.inst_oid    
    version = get_version_hash(inst_str)
    response.headers["Cache-Control"] = "no-cache, must-revalidate"
    response.headers["ETag"] = version

    cursos = list(db["curso"].find(
        {"instituicao_id": inst_str, "status": "Ativo"}, 
        {"_id": 1, "nome": 1}
    ).sort("nome", 1))

    instrutores = list(db["instrutor"].find(
        {"instituicao_id": inst_str, "status": "Ativo"}, 
        {"_id": 1, "nome": 1}
    ).sort("nome", 1))

    ucs = list(db["unidade_curricular"].find(
        {"instituicao_id": inst_str, "status": "Ativa"}, 
        {"_id": 1, "descricao": 1} 
    ).sort("descricao", 1))

    calendarios = list(db["calendario"].find(
        {"id_instituicao": inst_oid}, 
        {"_id": 1, "nome_calendario": 1}
    ).sort("nome_calendario", 1))

    return {
        "version": version,
        "cursos": [{"id": str(c["_id"]), "nome": c.get("nome")} for c in cursos],
        "instrutores": [{"id": str(c["_id"]), "nome": c.get("nome")} for c in instrutores],
        "unidades_curriculares": [{"id": str(c["_id"]), "nome": c.get("descricao")} for c in ucs],
        "calendarios": [{"id": str(c["_id"]), "nome": c.get("nome_calendario")} for c in calendarios],
        "user": {
            "id": ctx.user_id,
            "inst_id": inst_str
        }
    }