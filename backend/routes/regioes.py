from fastapi import APIRouter
from services.regioes import REGIOES

router = APIRouter(tags=["Regiões"])

@router.get("/regioes")
def listar_regioes():
    return REGIOES
