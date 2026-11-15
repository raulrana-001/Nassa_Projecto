"""Testes com produtos GCOV SINTÉTICOS (mesma estrutura HDF5 documentada), sem internet."""
import h5py
import numpy as np
import pytest
from fastapi.testclient import TestClient
from pyproj import Transformer

from main import app
from processing import raster
from services import nisar_download as dl, pipeline, regioes

EPSG, PASSO = 32733, 200.0

def _grelha():
    t = Transformer.from_crs(4326, EPSG, always_xy=True)
    xs, ys = t.transform([12.5, 14.5], [-10.0, -8.2])
    x = np.arange(min(xs), max(xs), PASSO); y = np.arange(max(ys), min(ys), -PASSO)
    cx, cy = t.transform(13.45, -9.1)
    return x, y, int(np.argmin(abs(y - cy))), int(np.argmin(abs(x - cx)))

def _bloco(a, ci, cj, di, dj, valor_db=None, delta=None):
    s = (slice(ci + di, ci + di + 30), slice(cj + dj, cj + dj + 30))
    if valor_db is not None: a[s] = valor_db
    if delta is not None: a[s] += delta

def criar_gcov(pasta, t0, crid="X05009", orbita="172", segunda=False, semente=1):
    x, y, ci, cj = _grelha(); rng = np.random.default_rng(semente)
    hv = -18 + rng.normal(0, .5, (len(y), len(x))); hh = -10 + rng.normal(0, .5, hv.shape)
    _bloco(hh, ci, cj, -60, -60, valor_db=-24)                    # água permanente
    if segunda:
        _bloco(hh, ci, cj, -60, 30, valor_db=-24)                 # água nova
        _bloco(hv, ci, cj, 30, -60, delta=-6)                     # perda de vegetação (HV -6 dB)
        _bloco(hh, ci, cj, 30, 30, delta=+6)                      # vegetação inundada (HH +6 dB)
    nome = f"NISAR_L2_PR_GCOV_006_{orbita}_A_008_2005_DHDH_A_{t0}T040000_{t0}T040030_{crid}_N_F_J_001.h5"
    with h5py.File(pasta / nome, "w") as f:
        g = f.create_group("science/LSAR/GCOV/grids/frequencyA")
        g["HHHH"] = (10 ** (hh / 10)).astype("f4"); g["HVHV"] = (10 ** (hv / 10)).astype("f4")
        g["xCoordinates"], g["yCoordinates"] = x, y
        g["xCoordinateSpacing"], g["yCoordinateSpacing"] = PASSO, -PASSO
        g["projection"] = np.uint32(EPSG)
    return nome

@pytest.fixture()
def dados(tmp_path, monkeypatch):
    monkeypatch.setattr(dl, "PASTA", tmp_path); monkeypatch.setattr(pipeline, "PASTA_RES", tmp_path / "res")
    criar_gcov(tmp_path, "20260701", semente=1)
    criar_gcov(tmp_path, "20260815", semente=2)
    criar_gcov(tmp_path, "20261001", semente=3, segunda=True)
    criar_gcov(tmp_path, "20260701", crid="X05007", semente=9)           # versão antiga (deve ser ignorada)
    criar_gcov(tmp_path, "20260801", orbita="999", semente=4)            # outra geometria, só 1 cena
    return tmp_path

def test_vegetacao_detecta_o_bloco_e_ignora_ruido(dados):
    r = pipeline.processar("Luanda", "vegetacao", "2026-06-01", "2026-11-01", 1)
    assert r["demo"] is False and len(r["produtos"]) == 3 and all("X05007" not in p for p in r["produtos"])
    assert 25 <= r["area_alterada_km2"] <= 45            # bloco de 30×30 px a 200 m = 36 km²
    assert abs(r["indicador"]) < 0.5 and r["confianca"] in ("Baixa", "Média") and len(r["serie"]) == 3
    assert r["pilha"]["orbita"] == "172" and (dados / "res" / "analise_1.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

def test_zonas_humidas_agua_nova_e_veg_inundada(dados):
    r = pipeline.processar("Luanda", "zonas_humidas", "2026-06-01", "2026-11-01", 2)
    m = {x["rotulo"]: float(x["valor"].split()[0]) for x in r["metricas"]}
    assert 25 <= m["Variação da água"] <= 45 and 25 <= m["Possível veg. inundada"] <= 45
    assert 25 <= m["Água no início"] <= 45               # só a água permanente existe no início

def test_sem_dados_locais(tmp_path, monkeypatch):
    monkeypatch.setattr(dl, "PASTA", tmp_path)
    with pytest.raises(pipeline.SemDadosLocais):
        pipeline.processar("Luanda", "vegetacao", "2026-06-01", "2026-11-01", 3)

def test_regiao_fora_da_cobertura(dados):
    with pytest.raises((raster.SemSobreposicao, pipeline.SemDadosLocais)):
        pipeline.processar("Cuando Cubango", "vegetacao", "2026-06-01", "2026-11-01", 4)

def test_api_analise_real_e_mapa(dados):
    with TestClient(app) as c:
        b = {"regiao": "Luanda", "fenomeno": "vegetacao", "dataInicial": "2026-06-01", "dataFinal": "2026-11-01", "banda": "L"}
        id_ = c.post("/api/analises", json=b).json()["id"]
        a = c.get(f"/api/analises/{id_}").json()
        assert a["estado"] == "concluida" and a["demo"] is False and a["mapa_url"] == f"/api/analises/{id_}/mapa.png"
        assert c.get(a["mapa_url"]).headers["content-type"] == "image/png" and len(a["mapa_limites"]) == 2
        assert c.get(f"/api/relatorios/{id_}").json()["origem_dados"].startswith("Produtos NISAR")
        assert len(c.get("/api/processamento/dados-locais").json()["produtos"]) == 5
        b2 = {**b, "regiao": "Moxico"}                       # sem dados locais → DEMO com explicação
        a2 = c.get(f"/api/analises/{c.post('/api/analises', json=b2).json()['id']}").json()
        assert a2["demo"] is True and "DEMO" in a2["mensagem"] and a2["mapa_url"] is None

def test_vista_sar_png(dados):
    with TestClient(app) as c:
        nome = sorted(p.name for p in dados.glob("*20260701*X05009*.h5"))[0]
        r = c.get("/api/processamento/vista", params={"nome": nome, "regiao": "Luanda", "pol": "HV"})
        assert r.status_code == 200, r.text
        v = r.json(); assert v["pol"] == "HVHV" and v["db_min"] < v["db_max"] and len(v["limites"]) == 2
        png = c.get(v["url"]); assert png.headers["content-type"] == "image/png" and png.content[:8] == b"\x89PNG\r\n\x1a\n"
        assert c.get("/api/processamento/vista", params={"nome": "../x.h5", "regiao": "Luanda"}).status_code == 404
        assert c.get("/api/processamento/vista", params={"nome": nome, "regiao": "Moxico"}).status_code == 404   # não cobre
        assert c.get("/api/processamento/vistas/..%2Fsegredo").status_code in (404, 422)
        assert c.get("/api/processamento/vista", params={"nome": nome, "regiao": "Luanda", "pol": "HH"}).status_code == 200
