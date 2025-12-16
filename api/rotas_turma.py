from fastapi import APIRouter, HTTPException, Response, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from bson import ObjectId
from db import get_mongo_db
from datetime import datetime, timezone
from fastapi import Depends
from auth_dep import get_ctx, RequestCtx
from cache_utils import invalidate_cache  

router = APIRouter(prefix="/api/turmas", tags=["Turmas"])


def _norm_status(val) -> bool:
    if val is None:
        return True
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if s in ("ativo", "true", "1", "on", "yes", "sim"):
        return True
    if s in ("inativo", "false", "0", "off", "no", "nao", "não"):
        return False
    raise HTTPException(status_code=400, detail="Campo 'status' inválido")

class UnidadeCurricularTurma(BaseModel):
    id_uc: str
    id_instrutor: str
    data_inicio: str
    data_fim: str

class TurmaCreate(BaseModel):
    codigo: str
    id_curso: str
    data_inicio: str
    data_fim: str
    turno: str
    num_alunos: int
    id_instituicao: str
    id_calendario: str
    id_empresa: str
    status: Optional[str] = "Ativo"  
    area_tecnologica: Optional[str] = None
    nivel_curso: Optional[str] = None
    tipo: Optional[str] = None
    categoria: Optional[str] = None
    observacoes: Optional[str] = None
    unidades_curriculares: List[UnidadeCurricularTurma]

def _to_oid(value: str, field: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Campo '{field}' inválido")

def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
     return {
        "id": str(doc.get("_id")),
        "codigo": doc.get("codigo", ""),
        "data_inicio": doc.get("data_inicio", ""),
        "data_fim": doc.get("data_fim", ""),
        "turno": doc.get("turno", ""),
        "status": doc.get("status", ""), 
        "id_empresa": str(doc["id_empresa"]) if isinstance(doc.get("id_empresa"), ObjectId) else doc.get("id_empresa"),
        "id_curso": str(doc["id_curso"]) if isinstance(doc.get("id_curso"), ObjectId) else doc.get("id_curso"),
        "area_tecnologica": doc.get("area_tecnologica", ""),  
        "data_hora_criacao": (
            doc["data_hora_criacao"].isoformat()
            if isinstance(doc.get("data_hora_criacao"), datetime)
            else (doc.get("data_hora_criacao") or "")
        ), 
    }

def _serialize_full(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    for f in ["id_curso", "id_instituicao", "id_calendario", "id_empresa"]:
        if f in doc and isinstance(doc[f], ObjectId):
            doc[f] = str(doc[f])
    if "unidades_curriculares" in doc:
        for uc in doc["unidades_curriculares"]:
            for f in ["id_uc", "id_instrutor"]:
                if isinstance(uc.get(f), ObjectId):
                    uc[f] = str(uc[f])
    if isinstance(doc.get("data_hora_criacao"), datetime):
        doc["data_hora_criacao"] = doc["data_hora_criacao"].isoformat()
    return doc

@router.post("/", status_code=201)
@router.post("", status_code=201, include_in_schema=False) 
def criar_turma(turma: TurmaCreate, ctx: RequestCtx = Depends(get_ctx)):
    db = get_mongo_db()
    doc = turma.dict()
    doc["id_curso"]       = _to_oid(doc["id_curso"], "id_curso")
    doc["id_instituicao"] = ctx.inst_oid 
    doc["id_calendario"]  = _to_oid(doc["id_calendario"], "id_calendario")
    doc["id_empresa"]     = _to_oid(doc["id_empresa"], "id_empresa")

    if not doc.get("unidades_curriculares"):
        raise HTTPException(status_code=400, detail="'unidades_curriculares' não pode ser vazio")
    for uc in doc["unidades_curriculares"]:
        uc["id_uc"] = _to_oid(uc["id_uc"], "unidades_curriculares[].id_uc")
        id_instr = uc.get("id_instrutor")
        if id_instr is None or str(id_instr).strip() == "":
            uc["id_instrutor"] = None
        else:
            uc["id_instrutor"] = _to_oid(id_instr, "unidades_curriculares[].id_instrutor")

    doc["data_hora_criacao"] =  datetime.now(timezone.utc)
    res = db["turma"].insert_one(doc)
    
    invalidate_cache(str(ctx.inst_oid))
    
    return {"msg": "Turma cadastrada com sucesso", "id": str(res.inserted_id)}

@router.put("/{turma_id}")
@router.put("/{turma_id}/", include_in_schema=False)        
def atualizar_turma(turma_id: str, turma: TurmaCreate, ctx: RequestCtx = Depends(get_ctx)):
    db = get_mongo_db()
    _id = _to_oid(turma_id, "turma_id")
    doc = turma.dict()

    doc["id_curso"]       = _to_oid(doc["id_curso"], "id_curso")
    
    doc["id_instituicao"] = ctx.inst_oid

    doc["id_calendario"]  = _to_oid(doc["id_calendario"], "id_calendario")
    doc["id_empresa"]     = _to_oid(doc["id_empresa"], "id_empresa")

    if not doc.get("unidades_curriculares"):
        raise HTTPException(status_code=400, detail="'unidades_curriculares' não pode ser vazio")
    for uc in doc["unidades_curriculares"]:
        uc["id_uc"] = _to_oid(uc["id_uc"], "unidades_curriculares[].id_uc")
        id_instr = uc.get("id_instrutor")
        if id_instr is None or str(id_instr).strip() == "":
            uc["id_instrutor"] = None
        else:
            uc["id_instrutor"] = _to_oid(id_instr, "unidades_curriculares[].id_instrutor")

    res = db["turma"].update_one(
        {"_id": _id, "id_instituicao": ctx.inst_oid}, 
        {"$set": doc}
    )
    
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Turma não encontrada ou acesso negado")
    
    invalidate_cache(str(ctx.inst_oid))
    
    return {"msg": "Turma atualizada com sucesso", "id": turma_id}

@router.get("/", tags=["Turmas"])
@router.get("", include_in_schema=False)
def listar_turmas(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    sort_by: str = Query("data_hora_criacao"),
    sort_dir: str = Query("desc"),
    ctx: RequestCtx = Depends(get_ctx) 
):
    """
    Retorna {items, page, page_size, total} para preencher a tabela do front.
    Faz lookup em 'empresa' para trazer 'razao_social' como 'empresa_razao_social'.
    """
    db = get_mongo_db()
    coll = db["turma"]

    allow = {
        "codigo": "codigo",
        "turno": "turno",
        "status": "status",
        "area_tecnologica": "area_tecnologica",
        "data_hora_criacao": "data_hora_criacao",
        "data_inicio": "data_inicio",
        "data_fim": "data_fim",
    }
    sort_key = allow.get(sort_by, "data_hora_criacao")
    sort_val = -1 if sort_dir.lower() == "desc" else 1

    pipeline = [
        {"$match": {"id_instituicao": ctx.inst_oid}}, 
        {"$sort": {sort_key: sort_val}},
        {"$skip": (page - 1) * page_size},
        {"$limit": page_size},
        {
            "$lookup": {
                "from": "empresa",
                "localField": "id_empresa",
                "foreignField": "_id",
                "as": "empresa",
            }
        },
        {"$unwind": {"path": "$empresa", "preserveNullAndEmptyArrays": True}},
        {
            "$project": {
                "_id": 1,
                "codigo": 1,
                "turno": 1,
                "status": 1,
                "area_tecnologica": 1,
                "id_empresa": 1,
                "data_hora_criacao": 1,
                "empresa_razao_social": "$empresa.razao_social",
            }
        },
    ]
    items = []
    for d in coll.aggregate(pipeline):
        items.append({
            "id": str(d.get("_id")),
            "codigo": d.get("codigo", ""),
            "turno": d.get("turno", ""),
            "status": d.get("status", ""), 
            "area_tecnologica": d.get("area_tecnologica", ""),
            "id_empresa": (
                str(d["id_empresa"]) if isinstance(d.get("id_empresa"), ObjectId)
                else (d.get("id_empresa") or "")
            ),
            "empresa_razao_social": d.get("empresa_razao_social") or "",
            "data_hora_criacao": (
                d["data_hora_criacao"].isoformat()
                if isinstance(d.get("data_hora_criacao"), datetime)
                else (d.get("data_hora_criacao") or "")
            ),
        })

    total = coll.count_documents({"id_instituicao": ctx.inst_oid})
    
    return {"items": items, "page": page, "page_size": page_size, "total": total}