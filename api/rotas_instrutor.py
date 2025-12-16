from fastapi import APIRouter, HTTPException
from db import get_mongo_db
from bson.objectid import ObjectId
from bson.errors import InvalidId
from datetime import datetime, timezone
from fastapi import Depends
from auth_dep import get_ctx, RequestCtx
from cache_utils import invalidate_cache  

router = APIRouter()


def _as_list_str(v):
    """Garante lista[str] a partir de list/str/None."""
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if x is not None]
    return [str(v)]

def _coerce_carga(v, default=0, minv=0, maxv=10**9):
    try:
        n = int(v)
    except Exception:
        return default
    n = max(minv, min(n, maxv))
    return n

def _normalize_status(value):
    if value is None or value == "":
        return "Ativo"
    if isinstance(value, bool):
        return "Ativo" if value else "Inativo"
    s = str(value).strip().lower()
    if s in ("ativo", "at", "a", "1", "true", "verdadeiro", "yes", "sim"):
        return "Ativo"
    if s in ("inativo", "in", "i", "0", "false", "falso", "no", "nao", "não"):
        return "Inativo"
    return "Ativo"

def _normalize_instrutor(doc: dict):
    if not doc:
        return doc

    oid = doc.get("_id")
    if isinstance(oid, ObjectId):
        gen_time = oid.generation_time.astimezone(timezone.utc)
        doc["_id"] = str(oid)
    else:
        gen_time = None

    inst = doc.get("instituicao_id")
    if isinstance(inst, ObjectId):
        doc["instituicao_id"] = str(inst)
    elif inst is None:
        doc["instituicao_id"] = ""
    else:
        doc["instituicao_id"] = str(inst)

    doc["mapa_competencia"] = _as_list_str(doc.get("mapa_competencia"))
    doc["turnos"] = _as_list_str(doc.get("turnos"))
    doc["carga_horaria"] = _coerce_carga(doc.get("carga_horaria"), default=0)

    cat = doc.get("categoria", doc.get("categoriaInstrutor", []))
    doc["categoria"] = _as_list_str(cat)
    doc.pop("categoriaInstrutor", None)

    doc["status"] = _normalize_status(doc.get("status"))

    dt = doc.get("data_criacao")
    if isinstance(dt, datetime):
        doc["data_criacao"] = dt.astimezone(timezone.utc).isoformat()
    elif dt is None and gen_time is not None:
        doc["data_criacao"] = gen_time.isoformat()

    return doc

def _whitelist_payload(instrutor: dict, partial: bool = False) -> dict:
    """Aceita apenas chaves permitidas; se partial=True, não obriga presença."""
    allow = {
        "nome", "matricula", "telefone", "email",
        "instituicao_id", "turnos", "mapa_competencia",
        "carga_horaria", "categoria", "status"
    }
    clean = {k: instrutor[k] for k in list(instrutor.keys()) if k in allow}

    clean["instituicao_id"] = str(clean.get("instituicao_id", "") or "")
    clean["turnos"] = _as_list_str(clean.get("turnos"))
    clean["mapa_competencia"] = _as_list_str(clean.get("mapa_competencia"))
    clean["categoria"] = _as_list_str(clean.get("categoria"))
    clean["carga_horaria"] = _coerce_carga(clean.get("carga_horaria"), default=0, minv=0, maxv=60)

    if "status" in clean:
        clean["status"] = _normalize_status(clean.get("status"))

    return clean

def _oid_or_400(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(status_code=400, detail="ID inválido")


@router.get("/api/instrutores")
def listar_instrutores(ctx: RequestCtx = Depends(get_ctx)):
    db = get_mongo_db()
    col = db["instrutor"]
    pipeline = [
        {"$match": {"instituicao_id": str(ctx.inst_oid)}},
        {"$addFields": {"sortKey": {"$ifNull": ["$data_criacao", {"$toDate": "$_id"}]}}},
        {"$sort": {"sortKey": -1}},
        {"$project": {"sortKey": 0}},
    ]
    itens = list(col.aggregate(pipeline))
    return [_normalize_instrutor(x) for x in itens]

@router.post("/api/instrutores")
def criar_instrutor(instrutor: dict, ctx: RequestCtx = Depends(get_ctx)):
    db = get_mongo_db()
    instrutor = dict(instrutor or {})
    instrutor.pop("_id", None)
    instrutor.pop("data_criacao", None)

    clean = _whitelist_payload(instrutor, partial=False)
    clean["instituicao_id"] = str(ctx.inst_oid)
    clean["status"] = _normalize_status(clean.get("status"))

    result = db["instrutor"].insert_one(clean)
    
    invalidate_cache(str(ctx.inst_oid)) 

    saved = db["instrutor"].find_one({"_id": result.inserted_id})
    return _normalize_instrutor(saved)

@router.put("/api/instrutores/{id}")
def atualizar_instrutor(id: str, instrutor: dict, ctx: RequestCtx = Depends(get_ctx)):
    db = get_mongo_db()
    oid = _oid_or_400(id)
    instrutor = dict(instrutor or {})
    instrutor.pop("_id", None)
    instrutor.pop("data_criacao", None)

    clean = _whitelist_payload(instrutor, partial=True)
    if "instituicao_id" in clean:
        del clean["instituicao_id"]

    if not clean:
        updated = db["instrutor"].find_one({"_id": oid})
        if not updated:
            raise HTTPException(status_code=404, detail="Instrutor não encontrado")
        return _normalize_instrutor(updated)

    result = db["instrutor"].update_one(
        {"_id": oid, "instituicao_id": str(ctx.inst_oid)}, 
        {"$set": clean}
    )
    if result.matched_count:
        invalidate_cache(str(ctx.inst_oid))
        
        updated = db["instrutor"].find_one({"_id": oid})
        return _normalize_instrutor(updated)
    raise HTTPException(status_code=404, detail="Instrutor não encontrado")

@router.delete("/api/instrutores/{id}")
def remover_instrutor(id: str, ctx: RequestCtx = Depends(get_ctx)):
    db = get_mongo_db()
    oid = _oid_or_400(id)
    result = db["instrutor"].delete_one({"_id": oid, "instituicao_id": str(ctx.inst_oid)})
    if result.deleted_count:
        invalidate_cache(str(ctx.inst_oid))
        return {"msg": "Removido com sucesso"}
    raise HTTPException(status_code=404, detail="Instrutor não encontrado")