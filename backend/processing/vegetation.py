"""Vegetação (banda L): a polarização cruzada HV é sensível à estrutura/biomassa lenhosa (dispersão de volume).
Uma descida forte de HV entre duas datas, com a mesma geometria, é compatível com perda de cobertura."""
import os
import numpy as np
from processing import comparison as cmp
from processing.raster import ProcessamentoErro

PAPEIS = {"hv": ("HVHV", "VHVH")}
LIMIAR_DB = float(os.getenv("VEG_LIMIAR_DB", "3"))
PALETA = {1: (220, 38, 38, 170), 2: (34, 197, 94, 170)}   # 1 = possível perda (vermelho), 2 = possível aumento (verde)
METODO = ("Diferença do retroescalonamento HV (gamma0, dB) entre a primeira e a última cena da mesma geometria; "
          f"perda = descida ≥ {LIMIAR_DB:g} dB, filtrada para remover píxeis isolados.")
LIMITACOES = [
    "O HV também varia com humidade do solo/vegetação e estação; duas datas não separam variação sazonal de mudança permanente.",
    "Queimadas e outras perdas de biomassa também reduzem o HV: sem dados de referência não se distingue desflorestação.",
    f"O limiar de {LIMIAR_DB:g} dB é um valor de partida e deve ser calibrado localmente.",
]

def analisar(cenas, datas):
    d = cmp.diferenca_db(cenas[0]["dados"]["hv"], cenas[-1]["dados"]["hv"])
    valido = np.isfinite(d)
    if not valido.any():
        raise ProcessamentoErro("Sem píxeis válidos na região (dados vazios ou fora da cobertura)")
    px = cenas[0]["pixel_m"]
    perda = cmp.filtro_maioria((d <= -LIMIAR_DB) & valido)
    ganho = cmp.filtro_maioria((d >= LIMIAR_DB) & valido)
    classes = np.zeros(d.shape, np.uint8); classes[ganho] = 2; classes[perda] = 1
    ruido = cmp.ruido_robusto(d)
    return {
        "fenomeno_nome": "vegetação", "demo": False, "indicador": round(cmp.mediana(d), 1),
        "area_km2": cmp.km2(valido.sum(), px), "area_alterada_km2": cmp.km2(perda.sum(), px),
        "confianca": cmp.confianca(float(valido.mean()), len(cenas), ruido, LIMIAR_DB),
        "serie": cmp.serie_temporal(cenas, "hv", datas), "metodo": METODO, "limitacoes": LIMITACOES,
        "parametros": {"polarizacao": cenas[0]["pol_usada"]["hv"], "limiar_db": LIMIAR_DB, "resolucao_m": px},
        "metricas": [{"rotulo": "Possível perda", "valor": f"{cmp.km2(perda.sum(), px)} km²"},
                     {"rotulo": "Possível aumento", "valor": f"{cmp.km2(ganho.sum(), px)} km²"},
                     {"rotulo": "Ruído (MAD)", "valor": f"{ruido:.1f} dB"}],
    }, classes
