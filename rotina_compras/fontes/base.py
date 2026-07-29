"""Contrato comum das fontes de coleta."""

from __future__ import annotations

from typing import Callable

from ..modelo import Oferta

CABECALHOS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}

TEMPO_LIMITE = 20


class FonteIndisponivel(RuntimeError):
    """A fonte não pôde ser consultada (bloqueio, credencial ausente, rede)."""


# Assinatura: (termo, limite) -> lista de ofertas, com `item` ainda vazio.
Coletor = Callable[[str, int], list[Oferta]]

_REGISTRO: dict[str, Coletor] = {}


def registrar(nome: str) -> Callable[[Coletor], Coletor]:
    def decorador(func: Coletor) -> Coletor:
        _REGISTRO[nome] = func
        return func

    return decorador


def obter(nome: str) -> Coletor:
    if nome not in _REGISTRO:
        disponiveis = ", ".join(sorted(_REGISTRO)) or "nenhuma"
        raise KeyError(f"Fonte desconhecida: {nome!r}. Disponíveis: {disponiveis}")
    return _REGISTRO[nome]


def fontes_disponiveis() -> list[str]:
    return sorted(_REGISTRO)
