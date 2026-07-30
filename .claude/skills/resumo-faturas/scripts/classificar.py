#!/usr/bin/env python3
"""Classifica lançamentos em PF/PJ, categoria e centro de custo.

Três camadas, da mais forte para a mais fraca: o cartão dá o padrão, as regras
de estabelecimento podem sobrepor esse padrão quando o sinal é forte, e as obras
entram por apelido na descrição. Quando cartão e regra discordam sem que uma
delas seja forte, o script não escolhe — marca confiança baixa e manda para
revisão humana. Chutar aqui é pior que perguntar.

Uso:
    python3 classificar.py --lancamentos lancamentos.csv --config config.yaml
                           [--inplace | --saida saida.csv] [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comum import (  # noqa: E402
    TIPOS_NAO_DESPESA,
    brl,
    carregar_config,
    despesas,
    escrever_lancamentos,
    ler_lancamentos,
    sem_acento,
)

TIPOS_FINANCEIROS = {"encargo", "anuidade", "iof", "ajuste"}


def indexar_cartoes(config):
    idx = {}
    for c in config.get("cartoes") or []:
        final = re.sub(r"\D", "", str(c.get("final", "")))[-4:]
        if final:
            idx[final] = c
    return idx


def compilar_regras(config):
    regras = []
    for i, r in enumerate(config.get("regras") or []):
        padrao = r.get("match")
        if not padrao:
            continue
        try:
            rx = re.compile(sem_acento(padrao))
        except re.error as e:
            print(f"  ! regra {i} ignorada, regex inválida ({e}): {padrao}", file=sys.stderr)
            continue
        regras.append({
            "rx": rx,
            "fonte": padrao,
            "categoria": r.get("categoria"),
            "titularidade": (r.get("titularidade") or "").upper() or None,
            "centro_custo": r.get("centro_custo"),
            "forca": (r.get("forca") or "fraca").lower(),
        })
    return regras


def achar_obra(texto, obras):
    """Procura apelido de obra na descrição. Só serve para gasto PJ."""
    alvo = sem_acento(texto)
    for o in obras:
        for apelido in (o.get("apelidos") or []) + [o.get("codigo", ""), o.get("nome", "")]:
            apelido = sem_acento(apelido)
            if apelido and len(apelido) >= 3 and apelido in alvo:
                return o.get("codigo")
    return None


def classificar_um(l, cartoes, regras, obras, limite_revisao):
    alvo = sem_acento(l.get("estabelecimento") or l.get("descricao"))
    cartao = cartoes.get(l.get("cartao", ""), {})
    padrao_cartao = (cartao.get("titularidade_padrao") or "").upper() or None

    # Pagamento da fatura anterior não é consumo — não há o que classificar, e
    # mandá-lo para revisão só gera ruído (e um valor negativo enorme na lista).
    if l.get("tipo") in TIPOS_NAO_DESPESA:
        l["titularidade"] = padrao_cartao or ""
        l["categoria"] = "Pagamento de fatura"
        l["centro_custo"] = ""
        l["confianca"] = "alta"
        l["regra"] = "pagamento da fatura anterior, fora dos totais de gasto"
        return l

    # regra vencedora: a primeira forte; senão a primeira fraca
    regra = next((r for r in regras if r["forca"] == "forte" and r["rx"].search(alvo)), None)
    if regra is None:
        regra = next((r for r in regras if r["rx"].search(alvo)), None)

    titularidade, confianca, motivo = None, "baixa", []

    if regra and regra["titularidade"]:
        if regra["forca"] == "forte":
            titularidade = regra["titularidade"]
            confianca = "alta"
            motivo.append(f"regra forte '{regra['fonte']}'")
            if padrao_cartao and padrao_cartao != titularidade:
                motivo.append(f"contraria o padrão do cartão ({padrao_cartao})")
        elif padrao_cartao is None:
            titularidade = regra["titularidade"]
            confianca = "media"
            motivo.append(f"regra '{regra['fonte']}' (cartão sem padrão)")
        elif padrao_cartao == regra["titularidade"]:
            titularidade = padrao_cartao
            confianca = "alta"
            motivo.append("cartão e regra concordam")
        else:
            # discordância sem sinal forte: quem decide é o humano
            titularidade = padrao_cartao
            confianca = "baixa"
            motivo.append(
                f"cartão diz {padrao_cartao} e a regra '{regra['fonte']}' diz "
                f"{regra['titularidade']} — confirmar")
    elif padrao_cartao:
        titularidade = padrao_cartao
        confianca = "media"
        motivo.append(f"padrão do cartão {l.get('cartao')}")
    else:
        motivo.append("sem regra e sem padrão de cartão")

    # Encargo, anuidade e IOF são do dono do cartão, não do estabelecimento.
    if l.get("tipo") in TIPOS_FINANCEIROS and padrao_cartao:
        titularidade = padrao_cartao
        confianca = "alta"
        motivo = [f"encargo do cartão {l.get('cartao')}"]

    categoria = (regra or {}).get("categoria") or l.get("categoria") or ""
    if not categoria and l.get("tipo") in TIPOS_FINANCEIROS:
        categoria = "Financeiro do cartão"
    if not categoria:
        categoria = "A classificar"
        confianca = "baixa"

    centro = l.get("centro_custo") or ""
    if titularidade == "PJ" and not centro:
        centro = (
            (regra or {}).get("centro_custo")
            or achar_obra(f"{l.get('descricao')} {l.get('obs')}", obras)
            or cartao.get("centro_custo_padrao")
            or ""
        )
    if titularidade == "PF":
        centro = ""

    # Valor alto sem classificação forte precisa passar por olho humano: o
    # erro caro está sempre no topo da lista, não na cauda.
    if titularidade and confianca == "media" and abs(l.get("valor", 0)) >= limite_revisao:
        confianca = "baixa"
        motivo.append(f"acima de {brl(limite_revisao)}, revisão obrigatória")

    l["titularidade"] = titularidade or ""
    l["categoria"] = categoria
    l["centro_custo"] = centro
    l["confianca"] = confianca
    l["regra"] = "; ".join(motivo)
    return l


def main():
    p = argparse.ArgumentParser(description="Classifica lançamentos de fatura.")
    p.add_argument("--lancamentos", required=True)
    p.add_argument("--config")
    p.add_argument("--saida")
    p.add_argument("--inplace", action="store_true")
    p.add_argument("--reclassificar", action="store_true",
                   help="refaz também o que já estava classificado")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    config = carregar_config(args.config)
    cartoes = indexar_cartoes(config)
    regras = compilar_regras(config)
    obras = [o for o in (config.get("obras") or []) if o.get("status", "ativa") != "encerrada"]
    limite = float((config.get("relatorio") or {}).get("limite_revisao_obrigatoria", 500) or 0)

    linhas = ler_lancamentos(args.lancamentos)
    for l in linhas:
        if l.get("titularidade") and not args.reclassificar:
            l["confianca"] = l.get("confianca") or "alta"
            l["regra"] = l.get("regra") or "já classificado na origem"
            continue
        classificar_um(l, cartoes, regras, obras, limite)

    destino = args.lancamentos if args.inplace else (args.saida or args.lancamentos)
    escrever_lancamentos(destino, linhas)

    # Totais gerenciais olham só o consumo do período, igual ao relatório.
    gastos = despesas(linhas)
    revisar = [l for l in gastos if l["confianca"] == "baixa" or not l["titularidade"]]
    resumo = {
        "total_lancamentos": len(linhas),
        "pj": round(sum(l["valor"] for l in gastos if l["titularidade"] == "PJ"), 2),
        "pf": round(sum(l["valor"] for l in gastos if l["titularidade"] == "PF"), 2),
        "a_revisar": len(revisar),
        "valor_a_revisar": round(sum(l["valor"] for l in revisar), 2),
        "arquivo": destino,
    }

    if args.json:
        # Agrupado por estabelecimento: é assim que as dúvidas devem ser
        # perguntadas ao usuário — uma pergunta por fornecedor, não por linha.
        grupos = {}
        for l in revisar:
            chave = (l.get("estabelecimento") or l.get("descricao"))[:40]
            g = grupos.setdefault(chave, {"estabelecimento": chave, "ocorrencias": 0,
                                          "valor": 0.0, "cartoes": set(), "motivo": l["regra"]})
            g["ocorrencias"] += 1
            g["valor"] = round(g["valor"] + l["valor"], 2)
            g["cartoes"].add(l.get("cartao"))
        for g in grupos.values():
            g["cartoes"] = sorted(x for x in g["cartoes"] if x)
        resumo["revisar"] = sorted(grupos.values(), key=lambda g: -abs(g["valor"]))
        print(json.dumps(resumo, ensure_ascii=False, indent=2))
    else:
        print(f"  · {resumo['total_lancamentos']} lançamentos classificados → {destino}")
        print(f"  · PJ {brl(resumo['pj'])}  ·  PF {brl(resumo['pf'])}")
        if revisar:
            print(f"  ! {len(revisar)} lançamento(s) para revisar, {brl(resumo['valor_a_revisar'])}")
            print("    Rode com --json para a lista agrupada por estabelecimento.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
