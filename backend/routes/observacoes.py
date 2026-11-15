from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from services import nisar_service, regioes

router = APIRouter(tags=["Observações"])

@router.get("/observacoes")
def listar_observacoes(regiao: Optional[str] = None, banda: str = Query("L", pattern="^[LS]$")):
    if regiao and not regioes.existe(regiao):
        raise HTTPException(422, "Região desconhecida")
    try:
        return nisar_service.listar_observacoes(regiao, banda)
    except nisar_service.NisarIndisponivel as e:
        raise HTTPException(502, str(e))
