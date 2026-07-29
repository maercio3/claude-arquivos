"""Coleta no Mercado Livre pela API oficial.

A busca (`/sites/MLB/search`) hoje exige um access token do Mercado Livre.
Gere um em https://developers.mercadolivre.com.br e exporte em
`ML_ACCESS_TOKEN`. Sem o token a fonte se declara indisponível em vez de
devolver resultado silenciosamente vazio.
"""

from __future__ import annotations

import os

import requests

from ..modelo import Oferta
from .base import CABECALHOS, TEMPO_LIMITE, FonteIndisponivel, registrar

URL_BUSCA = "https://api.mercadolibre.com/sites/{site}/search"
SITE_PADRAO = "MLB"  # Brasil


def _token() -> str:
    token = os.environ.get("ML_ACCESS_TOKEN", "").strip()
    if not token:
        raise FonteIndisponivel(
            "ML_ACCESS_TOKEN não definido — a API de busca do Mercado Livre "
            "exige autenticação."
        )
    return token


def _vendedor(resultado: dict) -> str | None:
    loja = resultado.get("official_store_name")
    if loja:
        return loja
    vendedor = resultado.get("seller") or {}
    return vendedor.get("nickname") or None


@registrar("mercado_livre")
def buscar(termo: str, limite: int = 8) -> list[Oferta]:
    parametros = {"q": termo, "limit": max(1, min(limite, 50))}
    cabecalhos = {**CABECALHOS, "Authorization": f"Bearer {_token()}"}
    site = os.environ.get("ML_SITE", SITE_PADRAO)

    try:
        resposta = requests.get(
            URL_BUSCA.format(site=site),
            params=parametros,
            headers=cabecalhos,
            timeout=TEMPO_LIMITE,
        )
    except requests.RequestException as erro:
        raise FonteIndisponivel(f"falha de rede: {erro}") from erro

    if resposta.status_code in (401, 403):
        raise FonteIndisponivel(
            f"API do Mercado Livre recusou a credencial (HTTP {resposta.status_code}) "
            "— o token pode ter expirado."
        )
    if resposta.status_code >= 400:
        raise FonteIndisponivel(f"HTTP {resposta.status_code} na API do Mercado Livre")

    try:
        dados = resposta.json()
    except ValueError as erro:
        raise FonteIndisponivel("resposta da API não é JSON") from erro

    return [_para_oferta(r) for r in dados.get("results", [])[:limite]]


def _para_oferta(resultado: dict) -> Oferta:
    frete = (resultado.get("shipping") or {}).get("free_shipping")
    return Oferta(
        item="",
        fonte="mercado_livre",
        titulo=resultado.get("title", "").strip(),
        preco=resultado.get("price"),
        url=resultado.get("permalink", ""),
        vendedor=_vendedor(resultado),
        frete_gratis=bool(frete) if frete is not None else None,
        moeda=resultado.get("currency_id", "BRL"),
    )
