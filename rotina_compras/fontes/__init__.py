"""Fontes de coleta da rotina.

Importar este pacote registra todas as fontes disponíveis.
"""

from . import busca_web, mercado_livre  # noqa: F401  (registram-se ao importar)
from .base import FonteIndisponivel, fontes_disponiveis, obter, registrar

__all__ = ["FonteIndisponivel", "fontes_disponiveis", "obter", "registrar"]
