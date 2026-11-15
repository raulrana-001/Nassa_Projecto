from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from database.connection import Base

def _agora():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Analise(Base):
    """Uma tarefa de análise e o seu resultado/metadados."""
    __tablename__ = "analises"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    regiao: Mapped[str] = mapped_column(String(80))
    fenomeno: Mapped[str] = mapped_column(String(30))
    data_inicial: Mapped[str] = mapped_column(String(10))
    data_final: Mapped[str] = mapped_column(String(10))
    banda: Mapped[str] = mapped_column(String(2))
    estado: Mapped[str] = mapped_column(String(20), default="em_processamento")
    mensagem: Mapped[str | None] = mapped_column(Text, nullable=True)
    resultado: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    demo: Mapped[bool] = mapped_column(Boolean, default=True)
    criada: Mapped[datetime] = mapped_column(DateTime, default=_agora)


class Descarga(Base):
    """Descarga de um produto NISAR para data/raw."""
    __tablename__ = "descargas"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(20), default="pendente")  # pendente | a_descarregar | concluida | erro
    caminho: Mapped[str | None] = mapped_column(Text, nullable=True)
    bytes: Mapped[int | None] = mapped_column(nullable=True)
    mensagem: Mapped[str | None] = mapped_column(Text, nullable=True)
    criada: Mapped[datetime] = mapped_column(DateTime, default=_agora)
