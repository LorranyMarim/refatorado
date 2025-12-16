from fastapi import APIRouter, HTTPException, Body, status, Depends
from pydantic import BaseModel, conint, constr, validator
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
import re
from auth_dep import get_ctx, RequestCtx
from db import get_mongo_db
from cache_utils import invalidate_cache

router = APIRouter()

class TipoEnum(str, Enum):
    Presencial = "Presencial"
    EAD = "EAD"
    Semipresencial = "Semipresencial"

class NivelEnum(str, Enum):
    Tecnico = "Técnico"
    Aperfeicoamento = "Aperfeiçoamento"
    Qualificacao = "Qualificação"
    Especializacao = "Especialização"

class StatusEnum(str, Enum):
    Ativo = "Ativo"
    Inativo = "Inativo"

class CategoriaEnum(str, Enum):
    C = "C"
    A = "A"

class AreaEnum(str, Enum):
    TI = "TI"
    MetalMecanica = "Metal Mecânica"

class ModalidadeCarga(BaseModel):
    carga_horaria: conint(ge=0) = 0
    quantidade_aulas_45min: conint(ge=0) = 0
    dias_letivos: conint(ge=0) = 0

class OrdemUC(BaseModel):
    id: constr(min_length=1)
    unidade_curricular: constr(min_length=1)
    presencial: ModalidadeCarga = ModalidadeCarga()
    ead: ModalidadeCarga = ModalidadeCarga()

class CursoIn(BaseModel):
    instituicao_id: constr(min_length=1)
    nome: constr(min_length=3, max_length=100)
    nivel_curso: NivelEnum
    tipo: TipoEnum
    status: StatusEnum = StatusEnum.Ativo
    categoria: CategoriaEnum
    area_tecnologica: AreaEnum
    carga_horaria: conint(ge=1)
    ordem_ucs: List[OrdemUC]
    observacao: Optional[constr(max_length=1000)] = None

    @validator("ordem_ucs")
    def _validar_ucs(cls, v: List[OrdemUC]):
        if not v or len(v) == 0:
            raise ValueError("Selecione ao menos 1 UC.")
        ids = [u.id for u in v]
        if len(set(ids)) != len(ids):
            raise ValueError("Existem UCs duplicadas na lista.")
        return v

CursoUpdate = CursoIn

HEX24 = re.compile(r"^[0-9a-fA-F]{24}$")

def _to_obj_id(v: Any):
    """Converte string 24-hex para ObjectId; caso contrário, retorna o valor original."""
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str) and HEX24.match(v):
        return ObjectId(v)
    return v

def _strip_tags(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s = re.sub(r"<[^>]*>", "", s or "")
    return re.sub(r"\s+", " ", s).strip()

def _normalize(doc: dict) -> dict:
    if not doc:
        return doc
    if isinstance(doc.get("_id"), ObjectId):
        doc["_id"] = str(doc["_id"])
    if isinstance(doc.get("instituicao_id"), ObjectId):
        doc["instituicao_id"] = str(doc["instituicao_id"])
    dt = doc.get("data_criacao")
    if isinstance(dt, datetime):
        doc["data_criacao"] = dt.astimezone(timezone.utc).isoformat()
    return doc

def _check_refs(db, curso: CursoIn) -> Dict[str, str]:
    errors: Dict[str, str] = {}
    for idx, uc in enumerate(curso.ordem_ucs):
        oid = _to_obj_id(uc.id)
        if not db["unidade_curricular"].find_one({"_id": oid}):
            errors[f"ordem_ucs[{idx}].id"] = "UC não encontrada."
    return errors

def _conflict_exists(db, curso: CursoIn, exclude_id: Optional[str] = None) -> bool:
    filtro: Dict[str, Any] = {
        "instituicao_id": curso.instituicao_id,
        "categoria": curso.categoria.value,
    }
    nome_regex = {"$regex": f"^{re.escape(curso.nome)}$", "$options": "i"}
    filtro["nome"] = nome_regex

    if exclude_id and HEX24.match(exclude_id):
        filtro["_id"] = {"$ne": ObjectId(exclude_id)}

    return db["curso"].find_one(filtro) is not None

@router.get("/api/cursos")
def listar_cursos(ctx: RequestCtx = Depends(get_ctx)):
    db = get_mongo_db()
    itens = list(db["curso"].find({"instituicao_id": str(ctx.inst_oid)}).sort([("data_criacao", -1), ("_id", -1)]))
    return [_normalize(x) for x in itens]

@router.post("/api/cursos", status_code=status.HTTP_201_CREATED)
def criar_curso(payload: dict = Body(...), ctx: RequestCtx = Depends(get_ctx)):
    db = get_mongo_db()

    payload["instituicao_id"] = str(ctx.inst_oid)

    for field in ("nome", "observacao"):
        if field in payload and isinstance(payload[field], str):
            payload[field] = _strip_tags(payload[field])

    try:
        curso = CursoIn(**payload)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    ref_errors = _check_refs(db, curso)
    if ref_errors:
        raise HTTPException(status_code=422, detail=ref_errors)

    if _conflict_exists(db, curso):
        raise HTTPException(status_code=409, detail="Esta combinação de nome + instituição + categoria já existe.")

    data = curso.dict()
    data["data_criacao"] = datetime.now(timezone.utc)

    inserted = db["curso"].insert_one(data)
    saved = db["curso"].find_one({"_id": inserted.inserted_id})
    invalidate_cache(str(ctx.inst_oid)) 
    
    saved = db["curso"].find_one({"_id": inserted.inserted_id})
    return _normalize(saved)

@router.put("/api/cursos/{id}")
def atualizar_curso(id: str, payload: dict = Body(...), ctx: RequestCtx = Depends(get_ctx)): 
    db = get_mongo_db()

    if not HEX24.match(id):
        raise HTTPException(status_code=404, detail="Curso não encontrado")

    payload["instituicao_id"] = str(ctx.inst_oid)

    for field in ("nome", "observacao"):
        if field in payload and isinstance(payload[field], str):
            payload[field] = _strip_tags(payload[field])

    payload.pop("data_criacao", None)
    payload.pop("_id", None)

    try:
        curso = CursoUpdate(**payload)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not db["curso"].find_one({"_id": ObjectId(id), "instituicao_id": str(ctx.inst_oid)}):
        raise HTTPException(status_code=404, detail="Curso não encontrado ou acesso negado")

    ref_errors = _check_refs(db, curso)
    if ref_errors:
        raise HTTPException(status_code=422, detail=ref_errors)

    if _conflict_exists(db, curso, exclude_id=id):
        raise HTTPException(status_code=409, detail="Esta combinação de nome + instituição + categoria já existe.")

    res = db["curso"].update_one(
        {"_id": ObjectId(id), "instituicao_id": str(ctx.inst_oid)}, 
        {"$set": curso.dict()}
    )
    if res.matched_count:
        invalidate_cache(str(ctx.inst_oid))
    if res.matched_count:
        updated = db["curso"].find_one({"_id": ObjectId(id)})
        return _normalize(updated)
    
    raise HTTPException(status_code=404, detail="Curso não encontrado")

@router.delete("/api/cursos/{id}")
def deletar_curso(id: str, ctx: RequestCtx = Depends(get_ctx)): 
    db = get_mongo_db()
    if not HEX24.match(id):
        raise HTTPException(status_code=404, detail="Curso não encontrado")
    
    res = db["curso"].delete_one({"_id": ObjectId(id), "instituicao_id": str(ctx.inst_oid)})
    if res.deleted_count:
        invalidate_cache(str(ctx.inst_oid))
        return {"msg": "Removido com sucesso"}
    
    if res.deleted_count:
        return {"msg": "Removido com sucesso"}
    raise HTTPException(status_code=404, detail="Curso não encontrado")