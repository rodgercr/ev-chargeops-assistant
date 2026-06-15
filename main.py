from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import auth, chat, admin
from routers import ev

app = FastAPI(title="GoodWeAI — EV ChargeOps Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,  prefix="/auth",  tags=["Autenticação"])
app.include_router(chat.router,  prefix="/chat",  tags=["Chat"])
app.include_router(admin.router, prefix="/admin", tags=["Administração"])
app.include_router(ev.router,    prefix="/ev",    tags=["Eletropostos & Sessões"])

app.mount("/", StaticFiles(directory="static", html=True), name="static")

@app.get("/api/status")
def status():
    return {"status": "ok", "sistema": "GoodWeAI"}
