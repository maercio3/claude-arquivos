"""Ponto de entrada da rotina de compras."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from .config import WatchlistInvalida, carregar
from .entrega import EmailNaoConfigurado, enviar_email, salvar
from .fontes.base import fontes_disponiveis
from .historico import melhores_anteriores, registrar
from .relatorio import gerar_html, gerar_markdown, titulo_do_dia
from .rotina import PAUSA_ENTRE_CONSULTAS, executar, todas_ofertas

RAIZ = Path(__file__).resolve().parent.parent


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rotina-compras",
        description="Pesquisa preços no Mercado Livre, Shopee, Shein e Google Shopping.",
    )
    parser.add_argument(
        "--watchlist",
        default=str(RAIZ / "config" / "watchlist.yml"),
        help="arquivo YAML com os itens a monitorar",
    )
    parser.add_argument(
        "--saida",
        default=str(RAIZ / "relatorios"),
        help="pasta onde salvar o relatório em Markdown",
    )
    parser.add_argument(
        "--historico",
        default=str(RAIZ / "dados" / "historico.jsonl"),
        help="arquivo JSONL com o histórico de preços",
    )
    parser.add_argument(
        "--fontes",
        nargs="+",
        choices=fontes_disponiveis(),
        help="restringe as fontes desta execução",
    )
    parser.add_argument(
        "--email",
        action="store_true",
        help="envia o relatório por e-mail (exige as variáveis SMTP_*)",
    )
    parser.add_argument(
        "--sem-historico",
        action="store_true",
        help="não grava esta execução no histórico",
    )
    parser.add_argument(
        "--pausa",
        type=float,
        default=PAUSA_ENTRE_CONSULTAS,
        help="segundos de espera entre consultas (padrão: %(default)s)",
    )
    parser.add_argument("-v", "--verboso", action="store_true", help="log detalhado")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = montar_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verboso else logging.WARNING,
        format="%(levelname)s %(message)s",
    )

    try:
        watchlist = carregar(args.watchlist)
    except WatchlistInvalida as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 2

    minimos = {} if args.sem_historico else melhores_anteriores(args.historico)
    resumos = executar(
        watchlist,
        fontes_ativas=tuple(args.fontes) if args.fontes else None,
        minimos_anteriores=minimos,
        pausa=args.pausa,
    )

    agora = datetime.now()
    markdown = gerar_markdown(resumos, agora)
    destino = Path(args.saida) / f"{agora:%Y-%m-%d}.md"
    salvar(destino, markdown)
    print(markdown)
    print(f"\n[relatório salvo em {destino}]", file=sys.stderr)

    if not args.sem_historico:
        registrar(args.historico, todas_ofertas(resumos))

    if args.email:
        alvos = [r.item for r in resumos if r.atingiu_alvo]
        assunto = titulo_do_dia(agora)
        if alvos:
            assunto += f" — {len(alvos)} no alvo"
        try:
            para = enviar_email(assunto, gerar_html(resumos, agora), markdown)
            print(f"[e-mail enviado para {para}]", file=sys.stderr)
        except EmailNaoConfigurado as erro:
            print(f"erro: e-mail não configurado ({erro})", file=sys.stderr)
            return 3
        except Exception as erro:
            print(f"erro ao enviar e-mail: {erro}", file=sys.stderr)
            return 3

    sem_nada = all(not r.ofertas for r in resumos)
    return 1 if sem_nada else 0


if __name__ == "__main__":
    raise SystemExit(main())
