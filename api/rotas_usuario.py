from fastapi import APIRouter, HTTPException, Response, Request, status
from db import get_mongo_db
from auth import verificar_senha
from auth_utils import criar_token
from pydantic import BaseModel, validator
from datetime import timedelta
from bson.objectid import ObjectId
from bson.errors import InvalidId
import re
import time
from datetime import timedelta
from fastapi import Depends
from auth_dep import get_ctx, RequestCtx
from cache_utils import invalidate_cache
from redis_client import get_redis


router = APIRouter()

LOCK_MINUTES = 5
MAX_ATTEMPTS = 5


class UsuarioLogin(BaseModel):
    user_name: str
    senha: str
    instituicao_id: str | None = None

    @validator('user_name')
    def validar_user(cls, v):
        v = v.strip()
        if not (4 <= len(v) <= 50):
            raise ValueError("Usuário deve ter entre 4 e 50 caracteres.")
        if re.search(r"[<>'\"]", v):
            raise ValueError("Usuário contém caracteres inválidos.")
        return v

    @validator('senha')
    def validar_senha(cls, v):
        if not (4 <= len(v) <= 50):
            raise ValueError("Senha deve ter entre 4 e 50 caracteres.")
        return v


def _oid_or_400(s: str) -> ObjectId:
    try:
        return ObjectId(s)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=400, detail="Instituição inválida")

@router.post("/api/logout")
def api_logout(response: Response):
    response.delete_cookie("session_token", path="/") 
    return {"ok": True}

@router.post("/api/login")
@router.post("/api/login")
def login(dados: UsuarioLogin, response: Response, request: Request):
    ip = request.client.host
    r = get_redis()
    
    key_attempts = f"login_attempts:{ip}"
    key_blocked = f"login_blocked:{ip}"

    if r.exists(key_blocked):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Muitas tentativas. Tente novamente em {LOCK_MINUTES} minutos."
        )

    db = get_mongo_db()
    usuario = db["usuario"].find_one({"user_name_lc": dados.user_name.lower()})
    def registrar_falha():
        attempts = r.incr(key_attempts)
        if attempts == 1:
            r.expire(key_attempts, 3600)
            
        if attempts >= MAX_ATTEMPTS:
            r.setex(key_blocked, LOCK_MINUTES * 60, "blocked")
            r.delete(key_attempts)
    
    erro_login = HTTPException(status_code=401, detail="Usuário ou senha incorretos.")
    hash_salvo = (usuario or {}).get("senha")



    if not usuario or not hash_salvo or not verificar_senha(dados.senha, hash_salvo):
        registrar_falha() 
        raise erro_login
    
    r.delete(key_attempts)
    r.delete(key_blocked)

    inst_id_user = usuario.get("instituicao_id")
    inst_id_user = str(inst_id_user) if inst_id_user is not None else None

    insts_user = usuario.get("instituicoes_ids") or []
    insts_user = [str(x) for x in insts_user if x is not None]

    chosen = (dados.instituicao_id or "").strip()

    if insts_user:

        if not chosen or chosen not in insts_user:
            raise HTTPException(status_code=403, detail="Instituição não permitida para este usuário.")
        inst_final = chosen

    elif inst_id_user:

        if chosen and chosen != inst_id_user:
            raise HTTPException(status_code=403, detail="Instituição não permitida para este usuário.")
        inst_final = inst_id_user

    else:
        if not chosen:
            raise HTTPException(status_code=403, detail="Selecione uma instituição válida.")
        inst_exists = db["instituicao"].find_one({"_id": _oid_or_400(chosen)})
        if not inst_exists:
            raise HTTPException(status_code=400, detail="Instituição inválida.")
        inst_final = chosen

    token = criar_token(
        {"sub": usuario.get("user_name"),
         "inst": inst_final
         }, expires_delta=timedelta(minutes=30))
    response.set_cookie(
        key="session_token", 
        value=token, 
        httponly=True, 
        max_age=30*60, 
        samesite="lax",
         )
    

    return {
        "id": str(usuario.get("_id")),
        "nome": usuario.get("nome"),
        "tipo_acesso": usuario.get("tipo_acesso"),
        "user_name": usuario.get("user_name"),
        "instituicao_id": inst_final,
        "token": token 
    }

@router.get("/api/usuarios")
def listar_usuarios(ctx: RequestCtx = Depends(get_ctx)):
    """Lista apenas usuários da mesma instituição do admin logado"""
    db = get_mongo_db()

    filtro = {
        "$or": [
            {"instituicao_id": str(ctx.inst_oid)},
            {"instituicoes_ids": str(ctx.inst_oid)}
        ]
    }
    
    usuarios = list(db["usuario"].find(filtro, {"senha": 0}))

    for u in usuarios:
        u["id"] = str(u["_id"])
        del u["_id"]
        
    return usuarios

@router.post("/api/usuarios", status_code=201)
def criar_usuario(dados: dict, ctx: RequestCtx = Depends(get_ctx)):
    """Cria usuário vinculado forçadamente à instituição do admin"""
    db = get_mongo_db()
    
    if not dados.get("user_name") or not dados.get("senha"):
        raise HTTPException(status_code=400, detail="Usuário e senha são obrigatórios")

    if db["usuario"].find_one({"user_name_lc": dados["user_name"].lower()}):
        raise HTTPException(status_code=400, detail="Nome de usuário já existe")

    from auth import get_password_hash 
    
    novo_usuario = {
        "nome": dados.get("nome"),
        "user_name": dados["user_name"],
        "user_name_lc": dados["user_name"].lower(),
        "senha": get_password_hash(dados["senha"]),
        "tipo_acesso": dados.get("tipo_acesso", "instrutor"),
        "ativo": True,
        
        "instituicao_id": str(ctx.inst_oid), 
        "instituicoes_ids": [str(ctx.inst_oid)]
    }
    
    db["usuario"].insert_one(novo_usuario)
    
    invalidate_cache(str(ctx.inst_oid))
    
    return {"msg": "Usuário criado com sucesso"}

@router.put("/api/usuarios/{user_id}")
def atualizar_usuario(user_id: str, dados: dict, ctx: RequestCtx = Depends(get_ctx)):
    db = get_mongo_db()
    oid = _oid_or_400(user_id)
    
    filtro_seguranca = {
        "_id": oid,
        "$or": [
            {"instituicao_id": str(ctx.inst_oid)},
            {"instituicoes_ids": str(ctx.inst_oid)}
        ]
    }
    
    usuario_existente = db["usuario"].find_one(filtro_seguranca)
    if not usuario_existente:
        raise HTTPException(status_code=404, detail="Usuário não encontrado ou acesso negado")

    campos_update = {}
    if "nome" in dados: campos_update["nome"] = dados["nome"]
    if "tipo_acesso" in dados: campos_update["tipo_acesso"] = dados["tipo_acesso"]
    if "ativo" in dados: campos_update["ativo"] = dados["ativo"]
    
    if dados.get("senha"):
        from auth import get_password_hash
        campos_update["senha"] = get_password_hash(dados["senha"])

    if "instituicao_id" in dados:
        del dados["instituicao_id"]

    db["usuario"].update_one({"_id": oid}, {"$set": campos_update})
    
    invalidate_cache(str(ctx.inst_oid))
    
    return {"msg": "Usuário atualizado"}

@router.delete("/api/usuarios/{user_id}")
def deletar_usuario(user_id: str, ctx: RequestCtx = Depends(get_ctx)):
    db = get_mongo_db()
    oid = _oid_or_400(user_id)
    
    res = db["usuario"].delete_one({
        "_id": oid,
        "$or": [
            {"instituicao_id": str(ctx.inst_oid)},
            {"instituicoes_ids": str(ctx.inst_oid)}
        ]
    })
    
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado ou acesso negado")
    
    invalidate_cache(str(ctx.inst_oid))
        
    return {"msg": "Usuário removido"}