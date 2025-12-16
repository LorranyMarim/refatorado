from fastapi import APIRouter, HTTPException, Depends
from db import get_mongo_db
from bson.objectid import ObjectId
from datetime import datetime, timezone
from auth_dep import get_ctx, RequestCtx
from cache_utils import invalidate_cache

router = APIRouter()

def _normalize_empresa(doc):
    """Converte ObjectId para str e normaliza data_criacao para ISO-8601 (UTC)."""
    if not doc:
        return doc
    oid = doc.get("_id")
    if isinstance(oid, ObjectId):
        doc["_id"] = str(oid)


    inst = doc.get("instituicao_id")
    if isinstance(inst, ObjectId):
        doc["instituicao_id"] = str(inst)

    dt = doc.get("data_criacao")
    if isinstance(dt, datetime):
        doc["data_criacao"] = dt.astimezone(timezone.utc).isoformat()
    elif dt is None and isinstance(oid, ObjectId):
        doc["data_criacao"] = oid.generation_time.astimezone(timezone.utc).isoformat()

    return doc

@router.get("/api/empresas")
def listar_empresas(ctx: RequestCtx = Depends(get_ctx)):
    """
    Lista apenas empresas da instituição logada.
    """
    db = get_mongo_db()
    col = db["empresa"]

    pipeline = [
        {"$match": {"instituicao_id": str(ctx.inst_oid)}},
        {
            "$addFields": {
                "sortKey": {
                    "$ifNull": ["$data_criacao", {"$toDate": "$_id"}]
                }
            }
        },
        {"$sort": {"sortKey": -1}},
        {"$project": {"sortKey": 0}}
    ]

    empresas = list(col.aggregate(pipeline))
    return [_normalize_empresa(e) for e in empresas]

@router.post("/api/empresas")
def adicionar_empresa(empresa: dict, ctx: RequestCtx = Depends(get_ctx)):
    """
    Cria empresa vinculada à instituição do usuário logado.
    """
    db = get_mongo_db()
    
    if "razao_social" not in empresa or "cnpj" not in empresa:
        raise HTTPException(status_code=400, detail="Campos obrigatórios: razao_social, cnpj")

    empresa["instituicao_id"] = str(ctx.inst_oid)

    empresa.pop("data_criacao", None)
    empresa["data_criacao"] = datetime.now(timezone.utc)

    result = db["empresa"].insert_one(empresa)
    
    invalidate_cache(str(ctx.inst_oid))

    saved = db["empresa"].find_one({"_id": result.inserted_id})
    return _normalize_empresa(saved)

@router.put("/api/empresas/{empresa_id}")
def editar_empresa(empresa_id: str, empresa: dict, ctx: RequestCtx = Depends(get_ctx)):
    db = get_mongo_db()
    empresa = dict(empresa or {})
    
    empresa.pop("data_criacao", None)
    empresa.pop("_id", None)
    empresa.pop("instituicao_id", None) 

    result = db["empresa"].update_one(
        {"_id": ObjectId(empresa_id), "instituicao_id": str(ctx.inst_oid)},
        {"$set": empresa}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Empresa não encontrada ou acesso negado")

    invalidate_cache(str(ctx.inst_oid))

    updated = db["empresa"].find_one({"_id": ObjectId(empresa_id)})
    return _normalize_empresa(updated)

@router.delete("/api/empresas/{empresa_id}")
def excluir_empresa(empresa_id: str, ctx: RequestCtx = Depends(get_ctx)):
    db = get_mongo_db()
    
    result = db["empresa"].delete_one(
        {"_id": ObjectId(empresa_id), "instituicao_id": str(ctx.inst_oid)}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Empresa não encontrada ou acesso negado")
    
    invalidate_cache(str(ctx.inst_oid))
    
    return {"msg": "Empresa excluída"}