"""Descarga de produtos NISAR (HDF5) do ASF DAAC para data/raw. Exige EARTHDATA_TOKEN (token Earthdata Login,
gerado em https://urs.earthdata.nasa.gov/profile). O token nunca é guardado em ficheiros nem devolvido pela API."""
import os
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.orm import Session
from database.connection import SessionLocal
from database.models import Descarga

PASTA = Path(os.getenv("DATA_RAW_DIR", Path(__file__).resolve().parents[2] / "data" / "raw"))
MAX_MB = float(os.getenv("MAX_DOWNLOAD_MB", "2000"))
HOSTS_OK = (".asf.alaska.edu", ".earthdatacloud.nasa.gov", ".earthdata.nasa.gov")

class DescargaInvalida(Exception):
    pass

def token() -> str | None:
    return os.getenv("EARTHDATA_TOKEN") or None

def validar(url: str, tamanho_bytes: int | None) -> None:
    u = urlparse(url)
    if u.scheme != "https" or not (u.hostname or "").endswith(HOSTS_OK):
        raise DescargaInvalida("URL não permitida: só se descarregam ficheiros de servidores ASF/NASA Earthdata por HTTPS.")
    if not token():
        raise DescargaInvalida("Falta o token Earthdata Login: defina a variável de ambiente EARTHDATA_TOKEN e reinicie o backend.")
    if tamanho_bytes and tamanho_bytes / 1e6 > MAX_MB:
        raise DescargaInvalida(f"Ficheiro com {tamanho_bytes/1e6:.0f} MB excede o limite de {MAX_MB:.0f} MB (MAX_DOWNLOAD_MB).")

def criar(db: Session, url: str) -> Descarga:
    d = Descarga(url=url, nome=url.rstrip("/").rsplit("/", 1)[-1])
    db.add(d); db.commit(); db.refresh(d)
    return d

def executar(descarga_id: int) -> None:
    db = SessionLocal()
    try:
        d = db.get(Descarga, descarga_id)
        d.estado = "a_descarregar"; db.commit()
        try:
            import asf_search as asf  # dependência oficial do ASF
            PASTA.mkdir(parents=True, exist_ok=True)
            sessao = asf.ASFSession().auth_with_token(token())
            asf.download_urls(urls=[d.url], path=str(PASTA), session=sessao)
            f = PASTA / d.nome
            if not f.exists():
                raise FileNotFoundError(f"Descarga terminou mas {d.nome} não foi encontrado em {PASTA}")
            d.caminho, d.bytes, d.estado = str(f), f.stat().st_size, "concluida"
        except Exception as e:
            d.estado, d.mensagem = "erro", str(e)[:500]
        db.commit()
    finally:
        db.close()
