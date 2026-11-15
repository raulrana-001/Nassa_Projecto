"""Zonas húmidas e inundação (banda L): água aberta lisa reflecte o sinal para longe do radar (HH/VV muito baixo);
vegetação inundada produz dupla reflexão (HH sobe). Compara-se a primeira e a última cena da mesma geometria."""
import os
import numpy as np
from processing import comparison as cmp
from processing.raster import ProcessamentoErro

PAPEIS = {"hh": ("HHHH", "VVVV")}
LIMIAR_AGUA_DB = float(os.getenv("WET_AGUA_DB", "-18"))
LIMIAR_AUMENTO_DB = float(os.getenv("WET_AUMENTO_DB", "3"))
# 1 água nova, 2 água perdida, 3 possível vegetação inundada, 4 água permanente
PALETA = {4: (96, 165, 250, 90), 1: (37, 99, 235, 200), 2: (245, 158, 11, 190), 3: (6, 182, 212, 170)}
METODO = (f"Água = HH/VV ≤ {LIMIAR_AGUA_DB:g} dB em cada data; água nova/perdida pela diferença das máscaras; "
          f"possível vegetação inundada = subida ≥ {LIMIAR_AUMENTO_DB:g} dB fora das máscaras de água; píxeis isolados removidos.")
LIMITACOES = [
    f"O limiar de água ({LIMIAR_AGUA_DB:g} dB) é um valor de partida e deve ser calibrado localmente.",
    "Superfícies lisas (areia seca, estradas, sombras de relevo) podem ser confundidas com água; o vento pode rugosar a água.",
    "A subida de HH é compatível com vegetação inundada, mas também com crescimento da vegetação ou humidade do solo.",
]

def analisar(cenas, datas):
    a, b = cmp.db(cenas[0]["dados"]["hh"]), cmp.db(cenas[-1]["dados"]["hh"])
    d = b - a
    if not (np.isfinite(a) & np.isfinite(b)).any():
        raise ProcessamentoErro("Sem píxeis válidos na região (dados vazios ou fora da cobertura)")
    agua_a = cmp.filtro_maioria(np.isfinite(a) & (a <= LIMIAR_AGUA_DB))
    agua_b = cmp.filtro_maioria(np.isfinite(b) & (b <= LIMIAR_AGUA_DB))
    nova, perdida, perm = agua_b & ~agua_a, agua_a & ~agua_b, agua_a & agua_b
    veg = cmp.filtro_maioria(np.isfinite(d) & (d >= LIMIAR_AUMENTO_DB) & ~agua_a & ~agua_b)
    classes = np.zeros(d.shape, np.uint8)
    classes[perm], classes[veg], classes[perdida], classes[nova] = 4, 3, 2, 1
    px, valido = cenas[0]["pixel_m"], np.isfinite(d)
    ruido = cmp.ruido_robusto(d)
    var = cmp.km2(agua_b.sum(), px) - cmp.km2(agua_a.sum(), px)
    return {
        "fenomeno_nome": "zonas húmidas", "demo": False, "indicador": round(cmp.mediana(d), 1),
        "area_km2": cmp.km2(valido.sum(), px), "area_alterada_km2": cmp.km2(nova.sum() + perdida.sum(), px),
        "confianca": cmp.confianca(float(valido.mean()), len(cenas), ruido, LIMIAR_AUMENTO_DB),
        "serie": cmp.serie_temporal(cenas, "hh", datas), "metodo": METODO, "limitacoes": LIMITACOES,
        "parametros": {"polarizacao": cenas[0]["pol_usada"]["hh"], "limiar_agua_db": LIMIAR_AGUA_DB,
                       "limiar_aumento_db": LIMIAR_AUMENTO_DB, "resolucao_m": px},
        "metricas": [{"rotulo": "Água no início", "valor": f"{cmp.km2(agua_a.sum(), px)} km²"},
                     {"rotulo": "Água no fim", "valor": f"{cmp.km2(agua_b.sum(), px)} km²"},
                     {"rotulo": "Variação da água", "valor": f"{var:+.1f} km²"},
                     {"rotulo": "Possível veg. inundada", "valor": f"{cmp.km2(veg.sum(), px)} km²"}],
    }, classes
