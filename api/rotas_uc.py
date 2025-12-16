from fastapi import APIRouter, HTTPException, Query, Depends
from db import get_mongo_db
from bson.objectid import ObjectId
from pydantic import BaseModel, Field, validator
from typing import Literal, Optional, List
from datetime import datetime, timezone
import re
from pymongo.collation import Collation
from auth_dep import get_ctx, RequestCtx
from cache_utils import invalidate_cache  

router = APIRouter()

FORBIDDEN_CHARS = re.compile(r'[<>"\';{}]')

class UnidadeCurricularModel(BaseModel):
    descricao: str = Field(..., min_length=2, max_length=100)
    sala_ideal: str = Field(..., min_length=2, max_length=100)
    instituicao_id: str = Field(..., min_length=2, max_length=100)
    status: Literal['Ativa', 'Inativa']

    @validator('descricao', 'sala_ideal', 'instituicao_id', pre=True)
    def sanitize_and_check_chars(cls, v):
        if not isinstance(v, str):
            raise ValueError("Valor inválido.")
        val = v.strip()
        if FORBIDDEN_CHARS.search(val):
            raise ValueError("O campo contém caracteres não permitidos.")
        return val

def _try_objectid(s: str):
    try:
        return ObjectId(s)
    except Exception:
        return None

@router.get("/api/unidades_curriculares")
def listar_ucs(
    q: Optional[str] = None,
    status: Optional[List[str]] = Query(None),
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 10,
    ctx: RequestCtx = Depends(get_ctx)
):
    db = get_mongo_db()
    filtro: dict = {}

    filtro["instituicao_id"] = str(ctx.inst_oid)

    if q:
        filtro["$or"] = [
            {"descricao":  {"$regex": q, "$options": "i"}},
            {"sala_ideal": {"$regex": q, "$options": "i"}},
        ]

    if status:
        norm = []
        for s in status:
            if not s: continue
            v = s.strip().capitalize()
            if v == "Ativo": v = "Ativa"
            elif v == "Inativo": v = "Inativa"
            if v in ("Ativa", "Inativa"):
                norm.append(v)
        if norm:
            filtro["status"] = {"$in": norm}

    if created_from or created_to:
        if created_from and created_from.tzinfo is None:
            created_from = created_from.replace(tzinfo=timezone.utc)
        if created_to and created_to.tzinfo is None:
            created_to = created_to.replace(tzinfo=timezone.utc)
        
        if created_from and created_to and created_from > created_to:
            created_from, created_to = created_to, created_from

        rng = {}
        if created_from: rng["$gte"] = created_from.astimezone(timezone.utc)
        if created_to: rng["$lte"] = created_to.astimezone(timezone.utc)
        if rng: filtro["data_criacao"] = rng

    page = max(1, int(page))
    page_size = min(max(1, int(page_size)), 100)

    col = db["unidade_curricular"]
    coll = Collation('pt', strength=1)

    total = col.count_documents(filtro, collation=coll)
    cursor = (
        col.find(filtro, collation=coll)
           .sort("data_criacao", -1)
           .skip((page - 1) * page_size)
           .limit(page_size)
    )

    items = []
    for uc in cursor:
        oid = uc.get("_id")
        if isinstance(uc.get("instituicao_id"), ObjectId):
            uc["instituicao_id"] = str(uc["instituicao_id"])

        if uc.get("data_criacao") is None and isinstance(oid, ObjectId):
            uc["data_criacao"] = oid.generation_time

        if isinstance(uc.get("data_criacao"), datetime):
            uc["data_criacao"] = uc["data_criacao"].astimezone(timezone.utc).isoformat()

        uc["_id"] = str(oid)
        items.append(uc)

    return {"items": items, "total": total, "page": page, "page_size": page_size}

@router.post("/api/unidades_curriculares")
def criar_uc(uc: UnidadeCurricularModel, ctx: RequestCtx = Depends(get_ctx)):
    db = get_mongo_db()
    data = uc.dict()

    data['instituicao_id'] = str(ctx.inst_oid)
    data['status'] = data['status'].capitalize()
    data['data_criacao'] = datetime.now(timezone.utc)
    data.pop('_id', None)

    inserted = db["unidade_curricular"].insert_one(data)
    
    invalidate_cache(str(ctx.inst_oid))
    
    return {"_id": str(inserted.inserted_id)}

@router.put("/api/unidades_curriculares/{id}")
def atualizar_uc(id: str, uc: UnidadeCurricularModel, ctx: RequestCtx = Depends(get_ctx)):
    oid = _try_objectid(id)
    if not oid:
        raise HTTPException(status_code=400, detail="ID inválido")

    db = get_mongo_db()
    data = uc.dict()
    data['status'] = data['status'].capitalize()
    data.pop('_id', None)
    data.pop('data_criacao', None)
    
    data['instituicao_id'] = str(ctx.inst_oid)

    res = db["unidade_curricular"].update_one(
        {"_id": oid, "instituicao_id": str(ctx.inst_oid)}, 
        {"$set": data}
    )
    
    if res.matched_count:
        invalidate_cache(str(ctx.inst_oid))
        return {"msg": "Atualizado com sucesso"}
    raise HTTPException(status_code=404, detail="UC não encontrada ou acesso negado")

@router.delete("/api/unidades_curriculares/{id}")
def deletar_uc(id: str, ctx: RequestCtx = Depends(get_ctx)):
    oid = _try_objectid(id)
    if not oid:
        raise HTTPException(status_code=400, detail="ID inválido")

    db = get_mongo_db()
    
    res = db["unidade_curricular"].delete_one(
        {"_id": oid, "instituicao_id": str(ctx.inst_oid)}
    )
    
    if res.deleted_count:
        invalidate_cache(str(ctx.inst_oid))
        return {"msg": "Removido com sucesso"}
    raise HTTPException(status_code=404, detail="UC não encontrada ou acesso negado")


@router.get("/api/gestao_ucs/bootstrap")
def bootstrap_ucs(ctx: RequestCtx = Depends(get_ctx)):
    db = get_mongo_db()

    inst_oid = ctx.inst_oid
    instituicao = db["instituicao"].find_one({"_id": inst_oid})
    
    lista_inst = []
    if instituicao:
        instituicao["_id"] = str(instituicao["_id"])
        lista_inst.append(instituicao)

    cursor_ucs = db["unidade_curricular"].find({"instituicao_id": str(inst_oid)}).sort("data_criacao", -1)
    
    lista_ucs = []
    for uc in cursor_ucs:
        uc["_id"] = str(uc["_id"])
        if isinstance(uc.get("data_criacao"), datetime):
            uc["data_criacao"] = uc["data_criacao"].astimezone(timezone.utc).isoformat()
        elif isinstance(uc.get("data_criacao"), ObjectId):
             uc["data_criacao"] = uc["data_criacao"].generation_time.isoformat()
             
        lista_ucs.append(uc)

    return {
        "instituicoes": lista_inst,
        "ucs": lista_ucs
    }