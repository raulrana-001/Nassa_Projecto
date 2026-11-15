from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import Analise
from schemas import AnaliseIn, AnaliseOut
from services import analysis_service as svc, pipeline, regioes

router = APIRouter(tags=["Análises"])

def _obter(db: Session, id: int) -> Analise:
    a = db.get(Analise, id)
    if not a:
        raise HTTPException(404, "Análise não encontrada")
    return a

@router.post("/analises", response_model=AnaliseOut, status_code=202)
def criar_analise(dados: AnaliseIn, bg: BackgroundTasks, db: Session = Depends(get_db)):
    if not regioes.existe(dados.regiao):
        raise HTTPException(422, "Região desconhecida")
    a = svc.criar(db, dados)
    bg.add_task(svc.executar, a.id)
    return svc.para_dict(a)

@router.get("/analises", response_model=list[AnaliseOut])
def listar_analises(db: Session = Depends(get_db)):
    q = select(Analise).order_by(Analise.id.desc()).limit(100)
    return [svc.para_dict(a) for a in db.scalars(q)]

@router.get("/analises/{id}", response_model=AnaliseOut)
def estado_analise(id: int, db: Session = Depends(get_db)):
    return svc.para_dict(_obter(db, id))

@router.get("/resultados/{id}", response_model=AnaliseOut)
def resultados(id: int, db: Session = Depends(get_db)):
    a = _obter(db, id)
    if a.estado != "concluida":
        raise HTTPException(409, f"Análise no estado '{a.estado}'")
    return svc.para_dict(a)

@router.get("/analises/{id}/mapa.png")
def mapa(id: int, db: Session = Depends(get_db)):
    _obter(db, id)
    f = pipeline.PASTA_RES / f"analise_{id}.png"
    if not f.exists():
        raise HTTPException(404, "Esta análise não tem mapa (resultado simulado ou ainda em processamento)")
    return FileResponse(f, media_type="image/png")
