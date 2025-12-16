from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rotas_usuario import router as usuario_router
from rotas_curso import router as curso_router
from rotas_instituicao import router as instituicao_router
from rotas_uc import router as uc_router
from rotas_empresa import router as empresa_router
from rotas_calendario import router as calendario_router
from rotas_instrutor import router as instrutor_router
from rotas_turma import router as turma_router
from rotas_dashboard import router as dashboard_router
from fastapi.middleware.gzip import GZipMiddleware
from bootstrap import router as bootstrap_router
from fastapi.middleware.gzip import GZipMiddleware

app = FastAPI(
    title="API SENAI Betim",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=500)

app.include_router(usuario_router)
app.include_router(curso_router)
app.include_router(instituicao_router)
app.include_router(uc_router)  
app.include_router(empresa_router)
app.include_router(calendario_router)
app.include_router(instrutor_router)
app.include_router(turma_router)    
app.include_router(dashboard_router)
app.include_router(bootstrap_router, prefix="/api")
app.add_middleware(GZipMiddleware, minimum_size=1024)


@app.get("/")
def status():
    return {"ok": True, "msg": "API online"}
