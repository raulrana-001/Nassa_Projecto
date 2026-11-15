"""Planeia que produtos NISAR são precisos para uma análise: consulta o ASF e escolhe a pilha (mesma órbita,
direcção e quadro) com mais cenas no período. Não descarrega nada por si."""
import numpy as np
from services import nisar_service as nisar, nisar_download as dl, pipeline, regioes

class SemPilha(Exception):
    pass

def planear(regiao: str, di: str, df: str, max_cenas: int = 3) -> dict:
    if nisar.MODO == "demo":
        raise nisar.NisarIndisponivel("NISAR_MODE=demo: sem acesso ao ASF")
    reg = regioes.obter(regiao)
    pilhas = {}
    for it in nisar.procurar(reg["bbox"], di, df, "GCOV", 100):
        i = pipeline.info(it["nome"] or "")
        if i and (it["nome"] or "").endswith(".h5"):
            ant = pilhas.setdefault(i["pilha"], {}).get(i["chave"])
            if not ant or ant[0]["crid"] < i["crid"]:
                pilhas[i["pilha"]][i["chave"]] = (i, it)
    cand = {k: sorted(v.values(), key=lambda t: t[0]["inicio"]) for k, v in pilhas.items()}
    cand = {k: v for k, v in cand.items() if len(v) >= 2}
    if not cand:
        raise SemPilha("O ASF não tem 2 ou mais produtos GCOV da mesma geometria sobre esta região neste período.")
    (orbita, direccao, quadro), lista = max(cand.items(), key=lambda kv: len(kv[1]))
    idx = sorted(set(np.linspace(0, len(lista) - 1, min(len(lista), max_cenas)).round().astype(int)))
    cenas = [{"nome": it["nome"], "url": it["url"], "inicio": it["inicio"], "tamanho_mb": it["tamanho_mb"], "bytes": it["bytes"],
              "local": (dl.PASTA / it["nome"]).exists()} for _, it in (lista[j] for j in idx)]
    falta = [c["tamanho_mb"] for c in cenas if not c["local"]]
    return {"regiao": regiao, "pilha": {"orbita": orbita, "direccao": direccao, "quadro": quadro},
            "cenas_disponiveis_na_pilha": len(lista), "cenas": cenas,
            "total_a_descarregar_mb": round(sum(m or 0 for m in falta), 1),
            "tamanho_desconhecido": any(m is None for m in falta), "token_configurado": bool(dl.token())}
