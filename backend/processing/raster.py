"""Leitura e preparação de produtos NISAR GCOV (HDF5) — sem GDAL/rasterio.
Estrutura usada (confirmada na documentação ASF): /science/LSAR/GCOV/grids/frequencyA/{HHHH,HVHV,...}
(potência linear gamma0, float32, NaN = inválido), xCoordinates, yCoordinates, xCoordinateSpacing,
yCoordinateSpacing e projection (código EPSG)."""
import struct
import zlib
from pathlib import Path

import h5py
import numpy as np
from pyproj import Transformer

GRADE = "science/LSAR/GCOV/grids/frequencyA"

class ProcessamentoErro(Exception):
    pass

class SemSobreposicao(ProcessamentoErro):
    pass

def _grade(f):
    try:
        g = f[GRADE]
        return (g, g["xCoordinates"][:], g["yCoordinates"][:], float(g["xCoordinateSpacing"][()]),
                float(g["yCoordinateSpacing"][()]), int(g["projection"][()]))
    except KeyError as e:
        raise ProcessamentoErro(f"Estrutura GCOV inesperada (falta {e})") from e

def pegada(caminho) -> list[float]:
    """Caixa [oeste, sul, este, norte] (graus) do produto, a partir dos vectores de coordenadas."""
    with h5py.File(caminho, "r") as f:
        _, x, y, _, _, epsg = _grade(f)
    lon, lat = Transformer.from_crs(epsg, 4326, always_xy=True).transform(
        [x.min(), x.max(), x.max(), x.min()], [y.min(), y.min(), y.max(), y.max()])
    return [min(lon), min(lat), max(lon), max(lat)]

def _faixa(coords, vmin, vmax):
    idx = np.flatnonzero((coords >= vmin) & (coords <= vmax))
    return None if idx.size == 0 else (int(idx[0]), int(idx[-1]) + 1)

def _ler_reduzido(ds, r0, r1, c0, c1, fator):
    """Lê a janela por faixas e faz multilook (média em potência linear) por blocos fator×fator."""
    nr, nc = (r1 - r0) // fator, (c1 - c0) // fator
    if nr < 1 or nc < 1:
        raise SemSobreposicao("A região é demasiado pequena para a resolução pedida")
    soma = np.zeros((nr, nc), np.float64); cont = np.zeros((nr, nc), np.int32)
    passo = max(1, 512 // fator) * fator
    for a in range(0, nr * fator, passo):
        b = min(a + passo, nr * fator); h = (b - a) // fator
        bloco = ds[r0 + a:r0 + b, c0:c0 + nc * fator].astype(np.float32)
        ok = np.isfinite(bloco) & (bloco > 0)
        bloco = np.where(ok, bloco, 0)
        soma[a // fator:a // fator + h] = bloco.reshape(h, fator, nc, fator).sum(axis=(1, 3))
        cont[a // fator:a // fator + h] = ok.reshape(h, fator, nc, fator).sum(axis=(1, 3))
    return np.where(cont >= max(1, fator * fator // 2), soma / np.maximum(cont, 1), np.nan).astype(np.float32)

def abrir_cena(caminho, bbox, papeis: dict, resolucao_m=100.0) -> dict:
    """papeis: {papel: (nomes de datasets candidatos)}. Devolve a janela da região já reduzida."""
    caminho = Path(caminho)
    with h5py.File(caminho, "r") as f:
        g, x, y, dx, dy, epsg = _grade(f)
        w, s, e, n = bbox
        px, py = Transformer.from_crs(4326, epsg, always_xy=True).transform(
            [w, e, e, w, (w + e) / 2, (w + e) / 2], [s, s, n, n, s, n])
        cols, lins = _faixa(x, min(px), max(px)), _faixa(y, min(py), max(py))
        if cols is None or lins is None:
            raise SemSobreposicao(f"{caminho.name} não cobre a região")
        fator = max(1, int(round(resolucao_m / abs(dx))))
        (c0, c1), (r0, r1) = cols, lins
        dados, usadas = {}, {}
        for papel, nomes in papeis.items():
            nome = next((k for k in nomes if k in g), None)
            if nome is None:
                raise ProcessamentoErro(f"{caminho.name} não contém a polarização {'/'.join(nomes)}")
            dados[papel], usadas[papel] = _ler_reduzido(g[nome], r0, r1, c0, c1, fator), nome
    nc, nr = (c1 - c0) // fator, (r1 - r0) // fator
    return {"caminho": str(caminho), "dados": dados, "pol_usada": usadas, "epsg": epsg, "pixel_m": abs(dx) * fator,
            "x": x[c0:c0 + nc * fator].reshape(nc, fator).mean(1), "y": y[r0:r0 + nr * fator].reshape(nr, fator).mean(1)}

def verificar_grelhas(cenas):
    r = cenas[0]
    for c in cenas[1:]:
        if (c["epsg"] != r["epsg"] or c["x"].shape != r["x"].shape or c["y"].shape != r["y"].shape
                or abs(c["x"][0] - r["x"][0]) > r["pixel_m"] / 2 or abs(c["y"][0] - r["y"][0]) > r["pixel_m"] / 2):
            raise ProcessamentoErro("As cenas não partilham a mesma grelha (órbita/quadro diferentes?)")

def _png(rgba: np.ndarray) -> bytes:
    h, w, _ = rgba.shape
    raw = b"".join(b"\x00" + rgba[i].tobytes() for i in range(h))
    def bloco(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + bloco(b"IDAT", zlib.compress(raw, 6)) + bloco(b"IEND", b""))

def _amostragem(cena, forma, max_lado):
    """Índices (linha, coluna) da grelha UTM da cena para cada píxel de uma grelha lon/lat regular."""
    x, y, epsg = cena["x"], cena["y"], cena["epsg"]
    dxr, dyr = x[1] - x[0], y[1] - y[0]
    lon, lat = Transformer.from_crs(epsg, 4326, always_xy=True).transform(
        [x.min(), x.max(), x.max(), x.min()], [y.min(), y.min(), y.max(), y.max()])
    w, e, s, n = min(lon), max(lon), min(lat), max(lat)
    h, wd = forma
    k = min(1.0, max_lado / max(h, wd)); nh, nw = max(2, int(h * k)), max(2, int(wd * k))
    LON, LAT = np.meshgrid(np.linspace(w, e, nw), np.linspace(n, s, nh))
    X, Y = Transformer.from_crs(4326, epsg, always_xy=True).transform(LON, LAT)
    col, lin = np.rint((X - x[0]) / dxr).astype(int), np.rint((Y - y[0]) / dyr).astype(int)
    dentro = (col >= 0) & (col < wd) & (lin >= 0) & (lin < h)
    return col, lin, dentro, [[float(s), float(w)], [float(n), float(e)]]

def exportar_png(cena, classes, paleta, saida, max_lado=1200):
    """Grelha de classes (uint8, 0 = transparente) -> PNG em lon/lat para o Leaflet. Devolve [[sul, oeste], [norte, este]]."""
    col, lin, dentro, limites = _amostragem(cena, classes.shape, max_lado)
    cls = np.zeros(col.shape, np.uint8); cls[dentro] = classes[lin[dentro], col[dentro]]
    rgba = np.zeros((*col.shape, 4), np.uint8)
    for k_, cor in paleta.items():
        rgba[cls == k_] = cor
    Path(saida).parent.mkdir(parents=True, exist_ok=True)
    Path(saida).write_bytes(_png(rgba))
    return limites

def exportar_db_png(cena, papel, saida, max_lado=1200):
    """Imagem SAR em escala de cinzentos: dB do retroescalonamento, contraste entre os percentis 2 e 98.
    Devolve (limites, db_min, db_max)."""
    db = 10 * np.log10(np.where(cena["dados"][papel] > 0, cena["dados"][papel], np.nan))
    ok = np.isfinite(db)
    if not ok.any():
        raise ProcessamentoErro("Sem píxeis válidos na região")
    lo, hi = np.percentile(db[ok], [2, 98])
    cinza = np.clip((np.nan_to_num(db, nan=lo) - lo) / max(hi - lo, 1e-6), 0, 1)
    col, lin, dentro, limites = _amostragem(cena, db.shape, max_lado)
    g = np.zeros(col.shape, np.uint8); v = np.zeros(col.shape, bool)
    g[dentro] = (cinza[lin[dentro], col[dentro]] * 255).astype(np.uint8); v[dentro] = ok[lin[dentro], col[dentro]]
    rgba = np.stack([g, g, g, np.where(v, 255, 0).astype(np.uint8)], axis=-1)
    Path(saida).parent.mkdir(parents=True, exist_ok=True)
    Path(saida).write_bytes(_png(np.ascontiguousarray(rgba)))
    return limites, float(lo), float(hi)
