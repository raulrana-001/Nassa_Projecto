"""Teste AO VIVO da ligação ao ASF DAAC (precisa de internet). Executar dentro de backend/:
    python scripts/testar_nisar.py
Mostra se o ASF responde, quantos produtos GCOV existem sobre cada região e as chaves reais devolvidas
(para confirmar que os nomes dos campos coincidem com os esperados pelo serviço)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import nisar_service as n, regioes

print("Modo:", n.MODO)
print("Saúde ASF:", json.dumps(n.saude())[:200])
for r in regioes.REGIOES:
    try:
        t = n.contar(r["bbox"], "2026-06-17", "2026-11-14")
        print(f"{r['nome']:<16} GCOV desde 2026-06-17: {t}")
    except n.NisarIndisponivel as e:
        print(f"{r['nome']:<16} ERRO: {e}")
r = regioes.REGIOES[-1]
dados = n._get(n.ASF_BUSCA, n._params(r["bbox"], "2026-06-17", "2026-11-14", "GCOV", "geojson", 1)).json()
if dados.get("features"):
    print("Chaves de properties:", sorted(dados["features"][0]["properties"].keys()))
    print("Normalizado:", json.dumps(n._normalizar(dados["features"][0]), ensure_ascii=False, indent=2))
else:
    print("Sem resultados para Luanda nesse período.")
