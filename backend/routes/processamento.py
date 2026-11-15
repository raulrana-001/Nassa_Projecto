import re
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database.connection import get_db
from schemas import PrepararIn
from processing import raster
from services import nisar_service as nisar, nisar_download as dl, pipeline, preparacao, regioes

router = APIRouter(prefix="/processamento", tags=["Processamento"])

@router.get("/dados-locais")
def dados_locais():
    """Produtos GCOV já presentes em data/raw (não abre os ficheiros)."""
    out = []
    for p in pipeline.ficheiros(dl.PASTA):
        i = pipeline.info(p.name)
        out.append({"nome": p.name, "tamanho_mb": round(p.stat().st_size / 1e6, 1),
                    "pilha": dict(zip(("orbita", "direccao", "quadro"), i["pilha"])) if i else None,
                    "inicio": i["inicio"].isoformat() if i else None})
    return {"pasta": str(dl.PASTA), "produtos": out}

@router.post("/preparar", status_code=200)
def preparar(d: PrepararIn, bg: BackgroundTasks, db: Session = Depends(get_db)):
    """Mostra a pilha de produtos necessária e, com descarregar=true, inicia a descarga dos que faltam."""
    if not regioes.existe(d.regiao):
        raise HTTPException(422, "Região desconhecida")
    if d.dataInicial >= d.dataFinal:
        raise HTTPException(422, "dataInicial tem de ser anterior a dataFinal")
    try:
        plano = preparacao.planear(d.regiao, d.dataInicial.isoformat(), d.dataFinal.isoformat(), d.maxCenas)
    except nisar.NisarIndisponivel as e:
        raise HTTPException(502, str(e))
    except preparacao.SemPilha as e:
        raise HTTPException(404, str(e))
    plano["descargas"] = []
    if d.descarregar:
        em_falta = [c for c in plano["cenas"] if not c["local"]]
        try:
            for c in em_falta:
                dl.validar(c["url"], c["bytes"])
        except dl.DescargaInvalida as e:
            raise HTTPException(400, str(e))
        for c in em_falta:
            desc = dl.criar(db, c["url"])
            bg.add_task(dl.executar, desc.id)
            plano["descargas"].append(desc.id)
    return plano

POLS = {"HH": ("HHHH",), "HV": ("HVHV", "VHVH"), "VV": ("VVVV",)}

@router.get("/vista")
def vista(nome: str, regiao: str, pol: str = Query("HV", pattern="^(HH|HV|VV)$")):
    """Imagem SAR (retroescalonamento em dB, escala de cinzentos) de um produto GCOV local, recortada à região."""
    reg = regioes.obter(regiao)
    if not reg:
        raise HTTPException(422, "Região desconhecida")
    f = dl.PASTA / nome
    if Path(nome).name != nome or not nome.endswith(".h5") or not f.is_file():
        raise HTTPException(404, "Produto não encontrado em data/raw")
    try:
        cena = raster.abrir_cena(f, reg["bbox"], {"p": POLS[pol]}, pipeline.RESOLUCAO_M)
        saida = pipeline.PASTA_RES / f"vista_{f.stem}_{reg['id']}_{pol}.png"
        limites, lo, hi = raster.exportar_db_png(cena, "p", saida)
    except raster.SemSobreposicao as e:
        raise HTTPException(404, str(e))
    except (raster.ProcessamentoErro, OSError) as e:
        raise HTTPException(422, str(e))
    i = pipeline.info(nome)
    return {"url": f"/api/processamento/vistas/{saida.name}", "limites": limites, "pol": cena["pol_usada"]["p"],
            "db_min": round(lo, 1), "db_max": round(hi, 1), "resolucao_m": cena["pixel_m"],
            "data": i["inicio"].isoformat() if i else None}

@router.get("/vistas/{ficheiro}")
def vista_png(ficheiro: str):
    f = pipeline.PASTA_RES / ficheiro
    if not re.fullmatch(r"vista_[\w.\-]+\.png", ficheiro) or not f.is_file():
        raise HTTPException(404, "Imagem não encontrada")
    return FileResponse(f, media_type="image/png")
