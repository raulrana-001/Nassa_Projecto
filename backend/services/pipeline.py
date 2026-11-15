"""Orquestra o processamento real: encontra, nos ficheiros locais (data/raw), as cenas GCOV da mesma geometria
(órbita, direcção, quadro) que cobrem a região no período, aplica o método do fenómeno e gera o mapa."""
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from processing import raster, vegetation, wetlands
from processing.raster import ProcessamentoErro
from services import nisar_download as dl, regioes

log = logging.getLogger("terrawatch.pipeline")
PASTA_RES = Path(os.getenv("DATA_RESULTS_DIR", Path(__file__).resolve().parents[2] / "data" / "results"))
MAX_CENAS = int(os.getenv("MAX_CENAS", "12"))
RESOLUCAO_M = float(os.getenv("RESOLUCAO_M", "100"))
MOTORES = {"vegetacao": vegetation, "zonas_humidas": wetlands}
# NISAR_L2_PR_GCOV_<ciclo>_<órbita>_<A|D>_<quadro>_..._<início>_<fim>_<CRID>_...
NOME = re.compile(r"GCOV_(\d{3})_(\d{3})_([AD])_(\d{3})_.*?_(\d{8}T\d{6})_(\d{8}T\d{6})_(X\d{5})")

class SemDadosLocais(ProcessamentoErro):
    pass

def info(nome: str) -> dict | None:
    m = NOME.search(nome)
    if not m:
        return None
    _, orbita, direccao, quadro, t0, _, crid = m.groups()
    return {"pilha": (orbita, direccao, quadro), "inicio": datetime.strptime(t0, "%Y%m%dT%H%M%S"),
            "crid": crid, "chave": nome[:m.start(7)]}

def ficheiros(pasta) -> list[Path]:
    return sorted(p for p in Path(pasta).glob("*.h5") if "GCOV" in p.name and "QA_STATS" not in p.name)

def _intersecta(a, b) -> float:
    iw = min(a[2], b[2]) - max(a[0], b[0]); ih = min(a[3], b[3]) - max(a[1], b[1])
    return max(0.0, iw) * max(0.0, ih)

def _cobertura(pegada, bbox) -> float:
    return _intersecta(pegada, bbox) / ((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))

def pilhas_locais(bbox, di: str, df: str, pasta) -> dict:
    ini, fim = datetime.fromisoformat(di), datetime.fromisoformat(df) + timedelta(days=1)
    versoes = {}
    for p in ficheiros(pasta):                       # mantém só a versão (CRID) mais recente de cada produto
        i = info(p.name)
        if i and ini <= i["inicio"] < fim and not (i["chave"] in versoes and versoes[i["chave"]][0]["crid"] >= i["crid"]):
            versoes[i["chave"]] = (i, p)
    pilhas = {}
    for i, p in versoes.values():
        try:
            pg = raster.pegada(p)
        except (OSError, ProcessamentoErro) as e:
            log.warning("Ficheiro ignorado %s: %s", p.name, e); continue
        if _intersecta(pg, bbox) > 0:
            pilhas.setdefault(i["pilha"], []).append({"caminho": p, "inicio": i["inicio"], "pegada": pg})
    for lista in pilhas.values():
        lista.sort(key=lambda c: c["inicio"])
    return pilhas

def amostrar(lista, maximo=MAX_CENAS):
    if len(lista) <= maximo:
        return lista
    return [lista[i] for i in sorted(set(np.linspace(0, len(lista) - 1, maximo).round().astype(int)))]

def processar(regiao: str, fenomeno: str, di: str, df: str, analise_id: int, pasta=None) -> dict:
    reg, pasta = regioes.obter(regiao), pasta or dl.PASTA
    pilhas = {k: v for k, v in pilhas_locais(reg["bbox"], di, df, pasta).items() if len(v) >= 2}
    if not pilhas:
        raise SemDadosLocais(f"Não há pelo menos 2 produtos GCOV da mesma geometria em {pasta} para {regiao} entre {di} e {df}. "
                             "Use POST /api/processamento/preparar para ver e descarregar os dados.")
    (orbita, direccao, quadro), lista = max(pilhas.items(), key=lambda kv: (len(kv[1]), _cobertura(kv[1][0]["pegada"], reg["bbox"])))
    lista, motor = amostrar(lista), MOTORES[fenomeno]
    cenas = [raster.abrir_cena(c["caminho"], reg["bbox"], motor.PAPEIS, RESOLUCAO_M) for c in lista]
    raster.verificar_grelhas(cenas)
    datas = [c["inicio"] for c in lista]
    res, classes = motor.analisar(cenas, datas)
    limites = raster.exportar_png(cenas[0], classes, motor.PALETA, PASTA_RES / f"analise_{analise_id}.png")
    res.update({"produtos": [Path(c["caminho"]).name for c in lista], "mapa_limites": limites,
                "mapa_url": f"/api/analises/{analise_id}/mapa.png",
                "periodo_efectivo": {"inicio": datas[0].date().isoformat(), "fim": datas[-1].date().isoformat()},
                "pilha": {"orbita": orbita, "direccao": direccao, "quadro": quadro},
                "cobertura_regiao_pct": round(100 * _cobertura(lista[0]["pegada"], reg["bbox"]), 1)})
    return res
