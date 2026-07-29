"""Coleta por busca web, para as lojas sem API pública utilizável.

Shopee e Shein bloqueiam acesso automatizado às próprias páginas de busca, então
aqui a rotina consulta um buscador e lê título/descrição dos resultados. O preço
sai do trecho indexado: é uma aproximação e pode estar defasado em relação à
página da loja — sempre confira no link antes de comprar.

Provedores (`PROVEDOR_BUSCA`):
  - `duckduckgo` (padrão): sem chave, resultados do HTML público.
  - `serpapi`: exige `SERPAPI_KEY`, dados melhores e habilita o Google Shopping
    de verdade (com preço estruturado em vez de extraído do texto).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

import requests

from ..modelo import Oferta
from ..precos import extrair_preco
from .base import CABECALHOS, TEMPO_LIMITE, FonteIndisponivel, registrar

URL_DUCKDUCKGO = "https://html.duckduckgo.com/html/"
URL_SERPAPI = "https://serpapi.com/search"


@dataclass
class ResultadoWeb:
    titulo: str
    url: str
    trecho: str = ""
    preco: float | None = None


class _LeitorDuckDuckGo(HTMLParser):
    """Extrai os pares título/trecho da página de resultados do DuckDuckGo."""

    def __init__(self) -> None:
        super().__init__()
        self.resultados: list[ResultadoWeb] = []
        self._em_titulo = False
        self._em_trecho = False
        self._titulo: list[str] = []
        self._trecho: list[str] = []
        self._url = ""

    def handle_starttag(self, tag, atributos):
        atributos = dict(atributos)
        classes = (atributos.get("class") or "").split()
        if tag == "a" and "result__a" in classes:
            self._descarregar()
            self._em_titulo = True
            self._url = _desembrulhar(atributos.get("href", ""))
        elif "result__snippet" in classes:
            self._em_trecho = True

    def handle_endtag(self, tag):
        if self._em_titulo and tag == "a":
            self._em_titulo = False
        elif self._em_trecho and tag in ("a", "div", "span", "td"):
            self._em_trecho = False

    def handle_data(self, dados):
        if self._em_titulo:
            self._titulo.append(dados)
        elif self._em_trecho:
            self._trecho.append(dados)

    def _descarregar(self) -> None:
        titulo = unescape("".join(self._titulo)).strip()
        if titulo and self._url:
            self.resultados.append(
                ResultadoWeb(
                    titulo=titulo,
                    url=self._url,
                    trecho=unescape("".join(self._trecho)).strip(),
                )
            )
        self._titulo, self._trecho, self._url = [], [], ""

    def close(self):
        super().close()
        self._descarregar()


def _desembrulhar(href: str) -> str:
    """Converte o link de redirecionamento do DuckDuckGo na URL real."""
    if not href:
        return ""
    if href.startswith("//"):
        href = "https:" + href
    partes = urlparse(href)
    if "duckduckgo.com" in partes.netloc and partes.path.startswith("/l/"):
        destino = parse_qs(partes.query).get("uddg", [""])[0]
        return destino or href
    return href


def _buscar_duckduckgo(consulta: str, limite: int) -> list[ResultadoWeb]:
    try:
        resposta = requests.post(
            URL_DUCKDUCKGO,
            data={"q": consulta, "kl": "br-pt"},
            headers=CABECALHOS,
            timeout=TEMPO_LIMITE,
        )
    except requests.RequestException as erro:
        raise FonteIndisponivel(f"falha de rede no DuckDuckGo: {erro}") from erro

    if resposta.status_code == 202 or resposta.status_code == 429:
        raise FonteIndisponivel(
            f"DuckDuckGo limitou a consulta (HTTP {resposta.status_code}) — "
            "reduza a watchlist ou configure SERPAPI_KEY."
        )
    if resposta.status_code >= 400:
        raise FonteIndisponivel(f"HTTP {resposta.status_code} no DuckDuckGo")

    leitor = _LeitorDuckDuckGo()
    leitor.feed(resposta.text)
    leitor.close()
    return leitor.resultados[:limite]


def _buscar_serpapi(consulta: str, limite: int, motor: str) -> list[ResultadoWeb]:
    chave = os.environ.get("SERPAPI_KEY", "").strip()
    if not chave:
        raise FonteIndisponivel("SERPAPI_KEY não definida")

    parametros = {
        "q": consulta,
        "engine": motor,
        "api_key": chave,
        "hl": "pt-br",
        "gl": "br",
        "google_domain": "google.com.br",
        "num": max(1, min(limite, 20)),
    }
    try:
        resposta = requests.get(URL_SERPAPI, params=parametros, timeout=TEMPO_LIMITE)
    except requests.RequestException as erro:
        raise FonteIndisponivel(f"falha de rede na SerpApi: {erro}") from erro
    if resposta.status_code >= 400:
        raise FonteIndisponivel(f"HTTP {resposta.status_code} na SerpApi")

    dados = resposta.json()
    if motor == "google_shopping":
        brutos = dados.get("shopping_results", [])
        return [
            ResultadoWeb(
                titulo=r.get("title", ""),
                url=r.get("product_link") or r.get("link", ""),
                trecho=r.get("source", ""),
                preco=r.get("extracted_price"),
            )
            for r in brutos[:limite]
        ]
    return [
        ResultadoWeb(
            titulo=r.get("title", ""),
            url=r.get("link", ""),
            trecho=r.get("snippet", ""),
        )
        for r in dados.get("organic_results", [])[:limite]
    ]


def buscar_na_web(consulta: str, limite: int, motor: str = "google") -> list[ResultadoWeb]:
    provedor = os.environ.get("PROVEDOR_BUSCA", "duckduckgo").lower()
    if provedor == "serpapi":
        return _buscar_serpapi(consulta, limite, motor)
    if provedor == "duckduckgo":
        if motor == "google_shopping":
            # O DuckDuckGo não expõe o Google Shopping; cai para a busca comum.
            return _buscar_duckduckgo(consulta, limite)
        return _buscar_duckduckgo(consulta, limite)
    raise FonteIndisponivel(f"PROVEDOR_BUSCA desconhecido: {provedor!r}")


def _dominio(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _coletar_loja(
    termo: str, limite: int, fonte: str, dominios: tuple[str, ...]
) -> list[Oferta]:
    consulta = f"{termo} preço site:{dominios[0]}"
    resultados = buscar_na_web(consulta, limite * 3)
    permitidos = {d.removeprefix("www.") for d in dominios}

    ofertas: list[Oferta] = []
    for resultado in resultados:
        dominio = _dominio(resultado.url)
        if not any(dominio == p or dominio.endswith("." + p) for p in permitidos):
            continue
        preco = resultado.preco
        if preco is None:
            preco = extrair_preco(resultado.trecho) or extrair_preco(resultado.titulo)
        ofertas.append(
            Oferta(
                item="",
                fonte=fonte,
                titulo=_limpar(resultado.titulo),
                preco=preco,
                url=resultado.url,
                vendedor=dominio,
            )
        )
        if len(ofertas) >= limite:
            break
    return ofertas


def _limpar(titulo: str) -> str:
    return re.sub(r"\s+", " ", titulo).strip()


@registrar("shopee")
def buscar_shopee(termo: str, limite: int = 8) -> list[Oferta]:
    return _coletar_loja(termo, limite, "shopee", ("shopee.com.br",))


@registrar("shein")
def buscar_shein(termo: str, limite: int = 8) -> list[Oferta]:
    return _coletar_loja(termo, limite, "shein", ("br.shein.com", "shein.com.br"))


@registrar("google_shopping")
def buscar_google_shopping(termo: str, limite: int = 8) -> list[Oferta]:
    """Comparativo aberto de lojas — o 'pesquisar no Chrome' da rotina.

    Com SERPAPI_KEY usa o Google Shopping e traz preço estruturado; sem ela,
    cai para a busca web comum e o preço vem do texto indexado.
    """
    resultados = buscar_na_web(f"{termo} preço comprar", limite * 2, motor="google_shopping")
    ofertas: list[Oferta] = []
    for resultado in resultados:
        preco = resultado.preco
        if preco is None:
            preco = extrair_preco(resultado.trecho) or extrair_preco(resultado.titulo)
        ofertas.append(
            Oferta(
                item="",
                fonte="google_shopping",
                titulo=_limpar(resultado.titulo),
                preco=preco,
                url=resultado.url,
                vendedor=resultado.trecho or _dominio(resultado.url),
            )
        )
        if len(ofertas) >= limite:
            break
    return ofertas
