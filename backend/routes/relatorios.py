from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import Analise
from services import analysis_service as svc

router = APIRouter(tags=["Relatórios"])

LIMITACOES = [
    "Uma alteração no sinal SAR não prova, por si só, desflorestação, incêndio ou inundação.",
    "O sinal depende da humidade do solo, do tipo e densidade da vegetação, da geometria de aquisição, do ruído e da qualidade do produto.",
    "Os resultados são indicadores compatíveis com alterações e requerem validação com dados de referência ou no terreno.",
]

@router.get("/relatorios/{id}")
def relatorio(id: int, db: Session = Depends(get_db)):
    a = db.get(Analise, id)
    if not a:
        raise HTTPException(404, "Análise não encontrada")
    if a.estado != "concluida":
        raise HTTPException(409, f"Análise no estado '{a.estado}'")
    d = svc.para_dict(a)
    return {
        "titulo": f"Análise #{a.id} — {a.regiao}",
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "regiao": a.regiao, "fenomeno": d.get("fenomeno_nome", a.fenomeno),
        "periodo": {"inicio": a.data_inicial, "fim": a.data_final}, "banda": a.banda,
        "resultados": {k: d.get(k) for k in ("indicador", "area_km2", "area_alterada_km2", "confianca", "serie", "metricas")},
        "origem_dados": ("DEMONSTRAÇÃO — dados simulados, não são observações reais" if a.demo
                         else "Produtos NISAR L2 GCOV (ASF DAAC): " + ", ".join(d.get("produtos", []))),
        "produtos": d.get("produtos"), "periodo_efectivo": d.get("periodo_efectivo"), "parametros": d.get("parametros"),
        "metodologia": d.get("metodo") or "Comparação do sinal SAR entre o início e o fim do período na região seleccionada.",
        "limitacoes": LIMITACOES + (d.get("limitacoes") or []), "demo": a.demo,
    }
