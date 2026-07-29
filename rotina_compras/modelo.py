"""Estruturas de dados compartilhadas pela rotina."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


def agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Oferta:
    """Uma oferta encontrada por alguma fonte para um item da watchlist."""

    item: str
    fonte: str
    titulo: str
    preco: float | None
    url: str = ""
    vendedor: str | None = None
    frete_gratis: bool | None = None
    avaliacao: float | None = None
    moeda: str = "BRL"
    coletado_em: str = field(default_factory=agora_iso)

    def para_dict(self) -> dict:
        return asdict(self)


@dataclass
class ResumoItem:
    """O que a rotina apurou para um item da watchlist numa execução."""

    item: str
    preco_alvo: float | None
    ofertas: list[Oferta]
    erros: dict[str, str] = field(default_factory=dict)
    preco_anterior: float | None = None

    @property
    def melhor(self) -> Oferta | None:
        com_preco = [o for o in self.ofertas if o.preco is not None]
        return min(com_preco, key=lambda o: o.preco) if com_preco else None

    @property
    def atingiu_alvo(self) -> bool:
        melhor = self.melhor
        return (
            melhor is not None
            and self.preco_alvo is not None
            and melhor.preco <= self.preco_alvo
        )

    @property
    def variacao(self) -> float | None:
        """Variação percentual do melhor preço contra a execução anterior."""
        melhor = self.melhor
        if melhor is None or not self.preco_anterior:
            return None
        return (melhor.preco - self.preco_anterior) / self.preco_anterior * 100
