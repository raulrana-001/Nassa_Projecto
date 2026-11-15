"""Coordena as análises: cria a tarefa, executa em segundo plano e converte para o formato da API."""
import os
import time
from sqlalchemy.orm import Session
from database.connection import SessionLocal
from database.models import Analise
from processing.comparison import resultado_demo
from services import nisar_service, pipeline

NOMES = {"vegetacao": "vegetação", "zonas_humidas": "zonas húmidas"}
# PROCESSAMENTO: auto (omissão) usa dados NISAR locais se existirem, senão DEMO; real = só dados reais; demo = só simulado
PROCESSAMENTO = os.getenv("PROCESSAMENTO", "auto").lower()
ATRASO_DEMO = float(os.getenv("DEMO_DELAY", "2.5"))  # segundos, só para ver o estado "em processamento"

def criar(db: Session, d) -> Analise:
    a = Analise(regiao=d.regiao, fenomeno=d.fenomeno, data_inicial=d.dataInicial.isoformat(),
                data_final=d.dataFinal.isoformat(), banda=d.banda)
    db.add(a); db.commit(); db.refresh(a)
    return a

def executar(analise_id: int) -> None:
    """Corre fora do pedido HTTP (BackgroundTasks), com sessão própria."""
    db = SessionLocal()
    try:
        a = db.get(Analise, analise_id)
        try:
            res = None
            if PROCESSAMENTO != "demo":
                a.mensagem = "a processar produtos NISAR locais"; db.commit()
                try:
                    res = pipeline.processar(a.regiao, a.fenomeno, a.data_inicial, a.data_final, a.id)
                    a.mensagem = None
                except pipeline.SemDadosLocais as e:
                    if PROCESSAMENTO == "real":
                        raise
                    a.mensagem = f"Resultado simulado (DEMO): {e}"
            if res is None:
                time.sleep(ATRASO_DEMO)
                res = resultado_demo(a.regiao, a.fenomeno, a.data_inicial, a.data_final, NOMES[a.fenomeno])
            a.resultado, a.demo, a.estado = res, res.get("demo", True), "concluida"
        except Exception as e:
            a.estado, a.mensagem = "erro", str(e)
        db.commit()
    finally:
        db.close()

def para_dict(a: Analise) -> dict:
    d = {"id": a.id, "regiao": a.regiao, "fenomeno": a.fenomeno, "dataInicial": a.data_inicial,
         "dataFinal": a.data_final, "banda": a.banda, "estado": a.estado, "demo": a.demo, "mensagem": a.mensagem}
    if a.resultado:
        d.update(a.resultado)
    return d
