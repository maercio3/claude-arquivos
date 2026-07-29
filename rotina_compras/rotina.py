"""Orquestração: percorre a watchlist, consulta as fontes, monta os resumos."""

from __future__ import annotations

import logging
import time

from . import fontes as _fontes  # noqa: F401  (registra as fontes)
from .config import ItemWatchlist, Watchlist
from .fontes.base import FonteIndisponivel, obter
from .modelo import Oferta, ResumoItem

log = logging.getLogger(__name__)

PAUSA_ENTRE_CONSULTAS = 1.5  # segundos, para não martelar os buscadores


def coletar_item(
    item: ItemWatchlist,
    fontes_ativas: tuple[str, ...] | None = None,
    pausa: float = PAUSA_ENTRE_CONSULTAS,
) -> ResumoItem:
    resumo = ResumoItem(item=item.nome, preco_alvo=item.preco_alvo, ofertas=[])
    escolhidas = [f for f in item.fontes if not fontes_ativas or f in fontes_ativas]

    for posicao, nome_fonte in enumerate(escolhidas):
        if posicao and pausa:
            time.sleep(pausa)
        try:
            coletor = obter(nome_fonte)
        except KeyError as erro:
            resumo.erros[nome_fonte] = str(erro)
            continue

        try:
            ofertas = coletor(item.termos, item.max_resultados)
        except FonteIndisponivel as erro:
            log.warning("%s / %s: %s", item.nome, nome_fonte, erro)
            resumo.erros[nome_fonte] = str(erro)
            continue
        except Exception as erro:  # uma fonte quebrada não derruba a rotina
            log.exception("%s / %s: erro inesperado", item.nome, nome_fonte)
            resumo.erros[nome_fonte] = f"erro inesperado: {erro}"
            continue

        for oferta in ofertas:
            oferta.item = item.nome
        resumo.ofertas.extend(ofertas)

    return resumo


def executar(
    watchlist: Watchlist,
    fontes_ativas: tuple[str, ...] | None = None,
    minimos_anteriores: dict[str, float] | None = None,
    pausa: float = PAUSA_ENTRE_CONSULTAS,
) -> list[ResumoItem]:
    minimos_anteriores = minimos_anteriores or {}
    resumos: list[ResumoItem] = []
    for item in watchlist:
        log.info("Consultando %s…", item.nome)
        resumo = coletar_item(item, fontes_ativas, pausa)
        resumo.preco_anterior = minimos_anteriores.get(item.nome)
        resumos.append(resumo)
    return resumos


def todas_ofertas(resumos: list[ResumoItem]) -> list[Oferta]:
    return [oferta for resumo in resumos for oferta in resumo.ofertas]
