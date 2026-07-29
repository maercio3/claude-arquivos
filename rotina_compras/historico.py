"""Histórico de preços em JSONL, para detectar queda entre execuções."""

from __future__ import annotations

import json
from pathlib import Path

from .modelo import Oferta


def registrar(caminho: str | Path, ofertas: list[Oferta]) -> None:
    """Acrescenta ao histórico o melhor preço por (item, fonte) desta rodada."""
    melhores: dict[tuple[str, str], Oferta] = {}
    for oferta in ofertas:
        if oferta.preco is None:
            continue
        chave = (oferta.item, oferta.fonte)
        atual = melhores.get(chave)
        if atual is None or oferta.preco < atual.preco:
            melhores[chave] = oferta

    if not melhores:
        return

    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("a", encoding="utf-8") as arquivo:
        for oferta in melhores.values():
            arquivo.write(json.dumps(oferta.para_dict(), ensure_ascii=False) + "\n")


def melhores_anteriores(caminho: str | Path) -> dict[str, float]:
    """Menor preço já registrado para cada item, em execuções passadas."""
    caminho = Path(caminho)
    if not caminho.exists():
        return {}

    minimos: dict[str, float] = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha:
            continue
        try:
            registro = json.loads(linha)
        except json.JSONDecodeError:
            continue  # linha corrompida não invalida o histórico inteiro
        item, preco = registro.get("item"), registro.get("preco")
        if not item or preco is None:
            continue
        if item not in minimos or preco < minimos[item]:
            minimos[item] = float(preco)
    return minimos
