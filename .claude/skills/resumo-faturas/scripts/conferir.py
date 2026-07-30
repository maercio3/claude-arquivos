#!/usr/bin/env python3
"""Confere a extração antes de classificar.

O objetivo é um só: descobrir se a extração perdeu ou inventou lançamento.
A soma dos lançamentos de cada arquivo tem que bater com o total impresso na
fatura. Quando não bate, quase sempre é linha perdida em quebra de página do
PDF ou uma linha de 'saldo anterior' contada como compra.

Uso:
    python3 conferir.py --lancamentos lancamentos.csv [--faturas faturas.csv]
                        [--tolerancia 0.05] [--json]

Sai com código 1 se houver erro que invalide o fechamento.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comum import (  # noqa: E402
    TIPOS,
    brl,
    ler_faturas,
    ler_lancamentos,
    parse_parcela,
    sem_acento,
)

# Textos que nunca deveriam virar lançamento de compra — se aparecerem como
# `compra`, a extração pegou uma linha de cabeçalho/resumo da fatura.
RUIDO = [
    "saldo anterior",
    "total desta fatura",
    "total da fatura",
    "limite disponivel",
    "limite total",
    "valor minimo",
    "pagamento minimo",
    "proximas faturas",
    "resumo da fatura",
    "encargos do proximo periodo",
]


def conferir(lancamentos, faturas, tolerancia):
    erros, avisos, info = [], [], []

    if not lancamentos:
        erros.append("Nenhum lançamento lido — a extração falhou.")
        return erros, avisos, info

    # --- integridade linha a linha ---------------------------------------
    for l in lancamentos:
        ref = f"linha {l['_linha']} ({l.get('descricao', '')[:40]})"
        if not l.get("data"):
            erros.append(f"{ref}: data ausente ou ilegível.")
        elif len(l["data"]) != 10:
            erros.append(f"{ref}: data '{l['data']}' não está em YYYY-MM-DD.")
        if l.get("valor") == 0:
            avisos.append(f"{ref}: valor zero — confira se a linha é lançamento mesmo.")
        if not l.get("descricao"):
            erros.append(f"{ref}: descrição vazia.")
        if not l.get("cartao"):
            avisos.append(f"{ref}: sem os 4 dígitos do cartão — vai atrapalhar a classificação.")
        tipo = sem_acento(l.get("tipo"))
        if tipo and tipo not in TIPOS:
            erros.append(f"{ref}: tipo '{l['tipo']}' fora da lista permitida ({', '.join(sorted(TIPOS))}).")
        if l.get("parcela") and not parse_parcela(l["parcela"]):
            avisos.append(f"{ref}: parcela '{l['parcela']}' não está no formato 3/10.")

        desc = sem_acento(l.get("descricao"))
        if tipo in ("compra", "parcela", "") and any(r in desc for r in RUIDO):
            erros.append(f"{ref}: parece linha de resumo da fatura, não uma compra. Remova.")

    # --- duplicidades ------------------------------------------------------
    vistos = collections.defaultdict(list)
    for l in lancamentos:
        chave = (l.get("data"), round(l.get("valor", 0), 2), sem_acento(l.get("descricao"))[:30])
        vistos[chave].append(l["_linha"])
    for (data, valor, desc), linhas in vistos.items():
        if len(linhas) > 1 and valor:
            avisos.append(
                f"{len(linhas)}x o mesmo lançamento em {data}, {brl(valor)}, '{desc}' "
                f"(linhas {', '.join(map(str, linhas))}) — duplicidade de extração ou cobrança repetida?"
            )

    # --- fechamento por arquivo -------------------------------------------
    if faturas:
        soma = collections.defaultdict(float)
        for l in lancamentos:
            soma[l.get("arquivo_origem", "")] += l.get("valor", 0)

        for f in faturas:
            arq = f["arquivo_origem"]
            extraido = round(soma.get(arq, 0.0), 2)
            declarado = round(f["total_fatura"], 2)
            dif = round(extraido - declarado, 2)
            if arq not in soma:
                erros.append(f"'{arq}': declarada em faturas.csv mas sem nenhum lançamento.")
            elif abs(dif) <= tolerancia:
                info.append(f"'{arq}': fecha. {brl(extraido)} = total da fatura.")
            else:
                erros.append(
                    f"'{arq}': NÃO fecha. Extraído {brl(extraido)} vs fatura {brl(declarado)} "
                    f"→ diferença de {brl(dif)}. "
                    + ("Faltam lançamentos." if dif < 0 else "Há lançamento a mais ou linha de resumo contada como compra.")
                )

        declarados = {f["arquivo_origem"] for f in faturas}
        for arq in soma:
            if arq not in declarados:
                avisos.append(f"'{arq}': tem lançamentos mas não está em faturas.csv — total não conferido.")
    else:
        avisos.append("Sem faturas.csv: o fechamento não foi conferido contra o total impresso.")

    total = round(sum(l.get("valor", 0) for l in lancamentos), 2)
    info.append(f"{len(lancamentos)} lançamentos, soma {brl(total)}.")
    return erros, avisos, info


def main():
    p = argparse.ArgumentParser(description="Confere a extração de faturas.")
    p.add_argument("--lancamentos", required=True)
    p.add_argument("--faturas")
    p.add_argument("--tolerancia", type=float, default=0.05,
                   help="diferença aceitável por fatura, em reais (padrão 0,05)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    lancamentos = ler_lancamentos(args.lancamentos)
    faturas = ler_faturas(args.faturas) if args.faturas else []
    erros, avisos, info = conferir(lancamentos, faturas, args.tolerancia)

    if args.json:
        print(json.dumps({"erros": erros, "avisos": avisos, "info": info,
                          "ok": not erros}, ensure_ascii=False, indent=2))
    else:
        for i in info:
            print(f"  · {i}")
        for a in avisos:
            print(f"  ! {a}")
        for e in erros:
            print(f"  ✗ {e}")
        print()
        print("Fechamento OK." if not erros
              else f"{len(erros)} problema(s) a resolver antes de classificar.")

    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
