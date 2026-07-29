"""Leitura da watchlist."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

FONTES_PADRAO = ("mercado_livre", "shopee", "shein", "google_shopping")
MAX_RESULTADOS_PADRAO = 6


@dataclass
class ItemWatchlist:
    nome: str
    termos: str
    preco_alvo: float | None = None
    fontes: tuple[str, ...] = FONTES_PADRAO
    max_resultados: int = MAX_RESULTADOS_PADRAO


@dataclass
class Watchlist:
    itens: list[ItemWatchlist] = field(default_factory=list)

    def __iter__(self):
        return iter(self.itens)

    def __len__(self):
        return len(self.itens)


class WatchlistInvalida(ValueError):
    pass


def carregar(caminho: str | Path) -> Watchlist:
    caminho = Path(caminho)
    if not caminho.exists():
        raise WatchlistInvalida(f"watchlist não encontrada: {caminho}")

    dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
    padroes = dados.get("padroes") or {}
    fontes_padrao = tuple(padroes.get("fontes") or FONTES_PADRAO)
    max_padrao = int(padroes.get("max_resultados") or MAX_RESULTADOS_PADRAO)

    brutos = dados.get("itens")
    if not brutos:
        raise WatchlistInvalida(f"nenhum item em {caminho} (chave 'itens' vazia)")

    itens: list[ItemWatchlist] = []
    for posicao, bruto in enumerate(brutos, start=1):
        if not isinstance(bruto, dict):
            raise WatchlistInvalida(f"item #{posicao} deveria ser um mapa YAML")
        nome = str(bruto.get("nome") or "").strip()
        termos = str(bruto.get("termos") or nome).strip()
        if not nome or not termos:
            raise WatchlistInvalida(f"item #{posicao} precisa de 'nome' (e 'termos')")
        alvo = bruto.get("preco_alvo")
        itens.append(
            ItemWatchlist(
                nome=nome,
                termos=termos,
                preco_alvo=float(alvo) if alvo is not None else None,
                fontes=tuple(bruto.get("fontes") or fontes_padrao),
                max_resultados=int(bruto.get("max_resultados") or max_padrao),
            )
        )
    return Watchlist(itens=itens)
