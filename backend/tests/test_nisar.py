"""Testes com respostas simuladas do ASF (sem internet). Executar: python -m pytest -q"""
import httpx
from fastapi.testclient import TestClient
from services import nisar_service as n
from main import app

FEATURE = {"type": "Feature", "geometry": None, "properties": {
    "fileID": "NISAR_L2_PR_GCOV_X-GCOV", "fileName": "NISAR_L2_PR_GCOV_X.h5", "sceneName": "NISAR_L2_PR_GCOV_X",
    "url": "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/X/NISAR_L2_PR_GCOV_X.h5", "startTime": "2026-10-25T04:00:00Z",
    "stopTime": "2026-10-25T04:00:30Z", "processingLevel": "GCOV", "bytes": "123456789", "flightDirection": "DESCENDING",
    "polarization": "HH+HV", "pathNumber": "72", "frameNumber": "79", "centerLat": "-8.9", "centerLon": "13.3"}}

def handler(req: httpx.Request):
    q = req.url.params
    if req.url.path.endswith("/health"):
        return httpx.Response(200, json={"api": "ok"})
    assert q["dataset"] == "NISAR" and q["processingLevel"] == "GCOV" and q["intersectsWith"].startswith("POLYGON((")
    if q["output"] == "count":
        return httpx.Response(200, text="2\n")
    older = {**FEATURE, "properties": {**FEATURE["properties"], "startTime": "2026-09-01T04:00:00Z", "fileName": "OLD.h5"}}
    return httpx.Response(200, json={"type": "FeatureCollection", "features": [older, FEATURE]})

def setup_function(_):
    n._TRANSPORT = httpx.MockTransport(handler); n.MODO = "asf"

def test_disponibilidade_real_ordenada_e_normalizada():
    d = n.disponibilidade("Luanda", "2026-06-17", "2026-11-14")
    assert d["demo"] is False and d["total"] == 2 and d["produtos"][0]["nome"] == "NISAR_L2_PR_GCOV_X.h5"
    p = d["produtos"][0]
    assert p["tamanho_mb"] == 123.5 and p["bytes"] == 123456789 and p["orbita"] == "72"

def test_observacoes_formato_do_frontend():
    o = n.listar_observacoes("Luanda", "L")
    assert o[0]["banda"] == "L" and o[0]["demo"] is False and o[0]["data"] == "2026-10-25"
    assert n.listar_observacoes("Luanda", "S") == []

def test_falha_em_modo_asf_e_fallback_em_auto():
    n._TRANSPORT = httpx.MockTransport(lambda r: httpx.Response(503, text="down"))
    try:
        n.disponibilidade("Luanda", "2026-06-17", "2026-11-14"); assert False
    except n.NisarIndisponivel:
        pass
    n.MODO = "auto"
    d = n.disponibilidade("Luanda", "2026-06-17", "2026-11-14")
    assert d["demo"] is True and "DEMONSTRAÇÃO" in d["origem"]

def test_endpoints_e_descarga_segura(monkeypatch):
    monkeypatch.delenv("EARTHDATA_TOKEN", raising=False)
    with TestClient(app) as c:
        r = c.get("/api/nisar/disponibilidade", params={"regiao": "Luanda", "dataInicial": "2026-06-17", "dataFinal": "2026-11-14"})
        assert r.status_code == 200 and r.json()["total"] == 2
        assert c.get("/api/nisar/disponibilidade", params={"regiao": "X", "dataInicial": "2026-06-17", "dataFinal": "2026-11-14"}).status_code == 422
        assert c.get("/api/nisar/produtos").json()["recomendado"] == "GCOV"
        assert c.get("/api/nisar/estado").json()["token_configurado"] is False
        url = FEATURE["properties"]["url"]
        assert c.post("/api/nisar/descargas", json={"url": url}).status_code == 400          # sem token
        monkeypatch.setenv("EARTHDATA_TOKEN", "x")
        assert c.post("/api/nisar/descargas", json={"url": "https://evil.example.com/a.h5"}).status_code == 400  # host não permitido
        assert c.post("/api/nisar/descargas", json={"url": url, "bytes": 99_000_000_000}).status_code == 400    # demasiado grande
