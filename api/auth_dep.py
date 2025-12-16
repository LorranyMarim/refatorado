from fastapi import Depends, HTTPException, Request, status
from bson.objectid import ObjectId
from bson.errors import InvalidId
from auth_utils import verificar_token

class RequestCtx:
    def __init__(self, user_id: str, inst_id: str, inst_oid: ObjectId):
        self.user_id = user_id
        self.inst_id = inst_id
        self.inst_oid = inst_oid
def get_ctx(request: Request) -> RequestCtx:
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Não autenticado"
        )
    
    payload = verificar_token(token)
    
    inst_str = payload.get("inst")
    if not inst_str:
        raise HTTPException(
            status_code=403, 
            detail="Instituição não definida no token de acesso"
        )
    
    try:
        inst_oid = ObjectId(inst_str)
    except InvalidId:
        raise HTTPException(
            status_code=400, 
            detail="ID da instituição no token é inválido"
        )
    
    return RequestCtx(
        user_id=payload.get("sub"), 
        inst_id=inst_str, 
        inst_oid=inst_oid
    )
class CurrentUser:
    def __init__(self, user_id: str, inst_id: str):
        self.id = user_id
        self.inst_id = inst_id

def get_current_user(request: Request) -> CurrentUser:
    ctx = get_ctx(request)
    return CurrentUser(user_id=ctx.user, inst_id=ctx.inst)
