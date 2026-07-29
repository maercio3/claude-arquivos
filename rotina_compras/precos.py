"""Extração e formatação de preços em real."""

from __future__ import annotations

import re

# Captura "R$ 1.234,56", "R$1234,56", "R$ 1.234" e "R$ 99".
_PADRAO_BRL = re.compile(r"R\$\s*(\d[\d.]*(?:,\d{1,2})?)", re.IGNORECASE)
_MILHAR = re.compile(r"^\d{1,3}(\.\d{3})+$")


def normalizar(bruto: str) -> float | None:
    """Converte um número em formato pt-BR para float."""
    bruto = bruto.strip()
    if not bruto:
        return None
    if "," in bruto:
        bruto = bruto.replace(".", "").replace(",", ".")
    elif _MILHAR.match(bruto):
        bruto = bruto.replace(".", "")
    try:
        return round(float(bruto), 2)
    except ValueError:
        return None


def extrair_preco(texto: str) -> float | None:
    """Primeiro preço em reais encontrado no texto, ou None."""
    if not texto:
        return None
    achado = _PADRAO_BRL.search(texto)
    return normalizar(achado.group(1)) if achado else None


def formatar(valor: float | None) -> str:
    if valor is None:
        return "—"
    inteiro, centavos = f"{valor:,.2f}".split(".")
    return f"R$ {inteiro.replace(',', '.')},{centavos}"
