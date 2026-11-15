"""Contratos da API (Pydantic). Os nomes dos campos coincidem com os usados pelo frontend (JS/api.js)."""
from datetime import date
from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator

class AnaliseIn(BaseModel):
    regiao: str
    fenomeno: Literal["vegetacao", "zonas_humidas"]
    dataInicial: date
    dataFinal: date
    banda: Literal["L", "S"] = "L"

    @model_validator(mode="after")
    def validar_datas(self):
        if self.dataInicial >= self.dataFinal:
            raise ValueError("dataInicial tem de ser anterior a dataFinal")
        return self

class PontoSerie(BaseModel):
    m: str
    v: float

class AnaliseOut(BaseModel):
    id: int
    regiao: str
    fenomeno: str
    dataInicial: str
    dataFinal: str
    banda: str
    estado: str                      # em_processamento | concluida | erro
    demo: bool = True
    mensagem: Optional[str] = None
    indicador: Optional[float] = None
    area_km2: Optional[float] = None
    area_alterada_km2: Optional[float] = None
    metodo: Optional[str] = None
    metricas: Optional[list[dict]] = None
    parametros: Optional[dict] = None
    produtos: Optional[list[str]] = None
    periodo_efectivo: Optional[dict] = None
    limitacoes: Optional[list[str]] = None
    pilha: Optional[dict] = None
    cobertura_regiao_pct: Optional[float] = None
    mapa_url: Optional[str] = None
    mapa_limites: Optional[list[list[float]]] = None
    confianca: Optional[str] = None
    serie: Optional[list[PontoSerie]] = None
    fenomeno_nome: Optional[str] = None


class DescargaIn(BaseModel):
    url: str
    bytes: Optional[int] = None   # tamanho indicado pela pesquisa; usado para respeitar MAX_DOWNLOAD_MB

class DescargaOut(BaseModel):
    id: int
    nome: str
    estado: str
    caminho: Optional[str] = None
    bytes: Optional[int] = None
    mensagem: Optional[str] = None


class PrepararIn(BaseModel):
    regiao: str
    dataInicial: date
    dataFinal: date
    maxCenas: int = Field(3, ge=2, le=12)
    descarregar: bool = False
