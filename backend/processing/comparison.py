"""Ferramentas comuns de comparação SAR (em dB) e resultados DEMO determinísticos."""
import numpy as np

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago"]

def resultado_demo(regiao, fenomeno, di, df, nome_fenomeno) -> dict:
    seed = sum(ord(c) for c in regiao + fenomeno + di + df)
    serie = [{"m": m, "v": round(((seed * (i + 3)) % 90) / 20 - 2.2, 1)} for i, m in enumerate(MESES)]
    return {"indicador": round(serie[-1]["v"] - serie[0]["v"], 1), "area_km2": 200 + seed % 900,
            "confianca": "Baixa", "serie": serie, "fenomeno_nome": nome_fenomeno, "demo": True}

def db(lin):
    with np.errstate(divide="ignore", invalid="ignore"):
        return 10 * np.log10(np.where(lin > 0, lin, np.nan))

def diferenca_db(antes, depois):
    return db(depois) - db(antes)

def mediana(x) -> float:
    v = np.asarray(x)[np.isfinite(x)]
    return float(np.median(v)) if v.size else float("nan")

def ruido_robusto(d) -> float:
    """Dispersão robusta (1,4826·MAD) da diferença: mede ruído/speckle residual na janela."""
    v = d[np.isfinite(d)]
    return float(1.4826 * np.median(np.abs(v - np.median(v)))) if v.size else float("nan")

def filtro_maioria(mascara, minimo=5):
    """Remove píxeis isolados (ruído sal-e-pimenta): mantém um píxel só se ≥ `minimo` dos 9 vizinhos (3×3) estiverem marcados."""
    h, w = mascara.shape
    p = np.pad(mascara.astype(np.uint8), 1)
    s = np.zeros((h, w), np.uint8)
    for i in range(3):
        for j in range(3):
            s += p[i:i + h, j:j + w]
    return mascara & (s >= minimo)

def confianca(frac_valida, n_cenas, ruido_db, limiar_db) -> str:
    """Conservadora: nunca 'Alta' sem validação com dados de referência."""
    if frac_valida < 0.6 or not np.isfinite(ruido_db) or ruido_db > limiar_db / 2:
        return "Baixa"
    return "Média" if n_cenas >= 3 else "Baixa"

def serie_temporal(cenas, papel, datas):
    return [{"m": d.strftime("%d/%m/%y"), "v": round(mediana(db(c["dados"][papel])), 1)} for c, d in zip(cenas, datas)]

def km2(n_pixeis, pixel_m) -> float:
    return round(float(n_pixeis) * (pixel_m / 1000.0) ** 2, 1)
