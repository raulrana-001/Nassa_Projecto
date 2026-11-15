"""Integração NISAR via ASF DAAC (API de pesquisa pública, sem autenticação para pesquisar).

Modos (variável NISAR_MODE):
  auto (omissão)  tenta o ASF; se estiver inacessível, devolve exemplos DEMO (marcados demo=True)
  asf             só dados reais; se o ASF falhar, a API devolve erro 502
  demo            só exemplos simulados (útil sem internet)

Pesquisar não exige conta. DESCARREGAR exige um token Earthdata Login (EARTHDATA_TOKEN).
Banda L: ASF DAAC (integrada). Banda S: ISRO Bhoonidhi (NÃO integrada)."""
import logging
import os
from datetime import date, timedelta

import httpx

from services import regioes

log = logging.getLogger("terrawatch.nisar")
MODO = os.getenv("NISAR_MODE", "auto").lower()
ASF_BUSCA = "https://api.daac.asf.alaska.edu/services/search/param"
ASF_SAUDE = "https://api.daac.asf.alaska.edu/health"
TIMEOUT = float(os.getenv("NISAR_TIMEOUT", "30"))
PRODUTO_OMISSAO = "GCOV"
_TRANSPORT = None  # permite injectar um transporte falso nos testes

class NisarIndisponivel(Exception):
    """O serviço do ASF não respondeu como esperado."""

# Níveis de processamento (keyword processingLevel do ASF para o dataset NISAR)
PRODUTOS = {
    "GCOV": {"nome": "Covariância polarimétrica geocodificada", "nivel": "L2",
             "uso": "Retroescalonamento (gamma0) corrigido do terreno: o mais adequado para vegetação e zonas húmidas."},
    "GSLC": {"nome": "SLC geocodificado", "nivel": "L2", "uso": "Dados complexos geocodificados (coerência, InSAR)."},
    "RSLC": {"nome": "SLC em coordenadas radar", "nivel": "L1", "uso": "Dados complexos em geometria radar."},
    "RIFG": {"nome": "Interferograma (radar)", "nivel": "L1", "uso": "Interferometria."},
    "RUNW": {"nome": "Interferograma desenrolado (radar)", "nivel": "L1", "uso": "Deslocamento do terreno."},
    "ROFF": {"nome": "Deslocamentos de píxel (radar)", "nivel": "L1", "uso": "Movimentos de grande amplitude."},
    "GUNW": {"nome": "Interferograma desenrolado geocodificado", "nivel": "L2", "uso": "Deslocamento do terreno."},
    "GOFF": {"nome": "Deslocamentos de píxel geocodificados", "nivel": "L2", "uso": "Movimentos de grande amplitude."},
    "SME2": {"nome": "Humidade do solo", "nivel": "L3", "uso": "Humidade do solo (confirmar maturidade na colecção)."},
}
LIMITACOES = [
    "A existência de produtos no catálogo não garante que sejam adequados à análise: confirme a maturidade (Beta, Provisório, Validado) nos metadados da colecção ASF.",
    "Banda S (ISRO) não está integrada: só se consulta a banda L através do ASF DAAC.",
    "As caixas das regiões são aproximadas e não correspondem aos limites administrativos oficiais.",
]

def _wkt(bbox):
    w, s, e, n = bbox
    return f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"

def _params(bbox, di, df, produto, saida, limite=None):
    p = {"dataset": "NISAR", "processingLevel": produto, "intersectsWith": _wkt(bbox),
         "start": f"{di}T00:00:00Z", "end": f"{df}T23:59:59Z", "output": saida}
    if limite:
        p["maxResults"] = limite
    return p

def _get(url, params=None):
    try:
        with httpx.Client(timeout=TIMEOUT, transport=_TRANSPORT, headers={"User-Agent": "TerraWatch-Angola/0.1"}) as c:
            r = c.get(url, params=params)
    except httpx.HTTPError as e:
        raise NisarIndisponivel(f"Sem ligação ao ASF DAAC: {e}") from e
    if r.status_code != 200:
        raise NisarIndisponivel(f"ASF DAAC respondeu {r.status_code}: {r.text[:200]}")
    return r

def saude() -> dict:
    return _get(ASF_SAUDE).json()

def contar(bbox, di, df, produto=PRODUTO_OMISSAO) -> int:
    texto = _get(ASF_BUSCA, _params(bbox, di, df, produto, "count")).text.strip()
    try:
        return int(texto)
    except ValueError as e:
        raise NisarIndisponivel(f"Resposta inesperada do ASF (count): {texto[:100]}") from e

def _primeiro(p: dict, *chaves):
    for k in chaves:
        if p.get(k) not in (None, ""):
            return p[k]
    return None

def _normalizar(feature: dict) -> dict:
    p = feature.get("properties", {}) or {}
    n = _primeiro(p, "bytes")
    try:
        mb = round(int(n) / 1e6, 1)
    except (TypeError, ValueError):
        mb = None
    urls = [u for u in [p.get("url"), *(p.get("additionalUrls") or [])] if isinstance(u, str)]
    h5 = next((u for u in urls if u.endswith(".h5") and "QA_STATS" not in u), None)
    url = h5 or p.get("url")
    return {"id": _primeiro(p, "fileID", "sceneName", "fileName"),
            "nome": url.rsplit("/", 1)[-1] if h5 else _primeiro(p, "fileName", "sceneName", "fileID"),
            "inicio": _primeiro(p, "startTime"), "fim": _primeiro(p, "stopTime"),
            "produto": _primeiro(p, "processingLevel"), "url": url,
            "tamanho_mb": mb, "bytes": int(n) if str(n).isdigit() else None,
            "direcao": _primeiro(p, "flightDirection"),
            "polarizacao": _primeiro(p, "polarization", "mainBandPolarization"),
            "orbita": _primeiro(p, "pathNumber", "relativeOrbit"), "quadro": _primeiro(p, "frameNumber"),
            "centro": {"lat": p.get("centerLat"), "lng": p.get("centerLon")}}

def procurar(bbox, di, df, produto=PRODUTO_OMISSAO, limite=20) -> list[dict]:
    dados = _get(ASF_BUSCA, _params(bbox, di, df, produto, "geojson", limite)).json()
    if not isinstance(dados, dict):
        raise NisarIndisponivel("Resposta inesperada do ASF (geojson)")
    itens = [_normalizar(f) for f in dados.get("features", [])]
    return sorted(itens, key=lambda x: x["inicio"] or "", reverse=True)

def _demo_itens(produto):
    return [{"id": f"EXEMPLO_{produto}_{i}", "nome": f"EXEMPLO_{produto}_{d}.h5", "inicio": f"{d}T08:00:00Z", "fim": f"{d}T08:00:30Z",
             "produto": produto, "url": None, "tamanho_mb": None, "bytes": None, "direcao": None, "polarizacao": None,
             "orbita": None, "quadro": None, "centro": {"lat": None, "lng": None}}
            for i, d in enumerate(("2026-09-18", "2026-06-04", "2026-03-12"), 1)]

def disponibilidade(regiao: str, di: str, df: str, produto=PRODUTO_OMISSAO, limite=20) -> dict:
    reg = regioes.obter(regiao)
    base = {"regiao": regiao, "bbox": reg["bbox"], "periodo": {"inicio": di, "fim": df}, "produto": produto, "banda": "L",
            "limitacoes": LIMITACOES}
    if MODO != "demo":
        try:
            total = contar(reg["bbox"], di, df, produto)
            itens = procurar(reg["bbox"], di, df, produto, limite) if total else []
            return {**base, "demo": False, "origem": "ASF DAAC (consulta real)", "modo": MODO,
                    "total": total, "mostrados": len(itens), "produtos": itens}
        except NisarIndisponivel as e:
            if MODO == "asf":
                raise
            log.warning("ASF indisponível, a usar DEMO: %s", e)
    itens = _demo_itens(produto)
    return {**base, "demo": True, "origem": "DEMONSTRAÇÃO — exemplos simulados, não são produtos reais", "modo": MODO,
            "total": len(itens), "mostrados": len(itens), "produtos": itens}

def listar_observacoes(regiao: str | None, banda: str) -> list[dict]:
    """Formato esperado pelo front end: lista de {produto, data, banda, qualidade, demo}."""
    if banda == "S" and MODO != "demo":
        return []  # banda S só existe na ISRO Bhoonidhi (não integrada)
    fim = date.today(); inicio = fim - timedelta(days=365)
    reg = regioes.obter(regiao) if regiao else None
    bbox = reg["bbox"] if reg else regioes.ANGOLA_BBOX
    if MODO != "demo":
        try:
            itens = procurar(bbox, inicio.isoformat(), fim.isoformat(), PRODUTO_OMISSAO, 10)
            return [{"produto": f"NISAR {i['produto'] or PRODUTO_OMISSAO} · {i['nome']}", "data": (i["inicio"] or "")[:10],
                     "banda": "L", "qualidade": "ver metadados ASF", "demo": False, "url": i["url"],
                     "tamanho_mb": i["tamanho_mb"]} for i in itens]
        except NisarIndisponivel as e:
            if MODO == "asf":
                raise
            log.warning("ASF indisponível, a usar DEMO: %s", e)
    return [{"produto": "Produto SAR NISAR (exemplo)", "data": d, "banda": banda, "qualidade": "não validada", "demo": True}
            for d in ("2026-03-12", "2026-06-04", "2026-09-18")]
