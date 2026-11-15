from datetime import date
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import Descarga
from schemas import DescargaIn, DescargaOut
from services import nisar_service as nisar, nisar_download as dl, regioes

router = APIRouter(prefix="/nisar", tags=["NISAR"])

@router.get("/estado")
def estado():
    """Modo de funcionamento e se o ASF responde. O token nunca é mostrado."""
    try:
        asf = {"acessivel": True, "detalhe": nisar.saude()}
    except nisar.NisarIndisponivel as e:
        asf = {"acessivel": False, "detalhe": str(e)}
    return {"modo": nisar.MODO, "fonte": "ASF DAAC", "asf": asf, "token_configurado": bool(dl.token()),
            "limite_descarga_mb": dl.MAX_MB}

@router.get("/produtos")
def produtos():
    return {"recomendado": nisar.PRODUTO_OMISSAO, "produtos": nisar.PRODUTOS, "limitacoes": nisar.LIMITACOES}

@router.get("/disponibilidade")
def disponibilidade(regiao: str, dataInicial: date, dataFinal: date,
                    produto: str = Query(nisar.PRODUTO_OMISSAO), limite: int = Query(20, ge=1, le=100)):
    if not regioes.existe(regiao):
        raise HTTPException(422, "Região desconhecida")
    if produto not in nisar.PRODUTOS:
        raise HTTPException(422, f"Produto desconhecido. Valores: {', '.join(nisar.PRODUTOS)}")
    if dataInicial >= dataFinal:
        raise HTTPException(422, "dataInicial tem de ser anterior a dataFinal")
    try:
        return nisar.disponibilidade(regiao, dataInicial.isoformat(), dataFinal.isoformat(), produto, limite)
    except nisar.NisarIndisponivel as e:
        raise HTTPException(502, str(e))

@router.post("/descargas", response_model=DescargaOut, status_code=202)
def pedir_descarga(d: DescargaIn, bg: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        dl.validar(d.url, d.bytes)
    except dl.DescargaInvalida as e:
        raise HTTPException(400, str(e))
    desc = dl.criar(db, d.url)
    bg.add_task(dl.executar, desc.id)
    return desc

@router.get("/descargas", response_model=list[DescargaOut])
def listar_descargas(db: Session = Depends(get_db)):
    return list(db.scalars(select(Descarga).order_by(Descarga.id.desc()).limit(100)))

@router.get("/descargas/{id}", response_model=DescargaOut)
def estado_descarga(id: int, db: Session = Depends(get_db)):
    d = db.get(Descarga, id)
    if not d:
        raise HTTPException(404, "Descarga não encontrada")
    return d
