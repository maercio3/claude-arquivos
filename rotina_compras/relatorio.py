"""Montagem do relatório em Markdown e HTML."""

from __future__ import annotations

from datetime import datetime
from html import escape

from .modelo import ResumoItem
from .precos import formatar

ROTULOS = {
    "mercado_livre": "Mercado Livre",
    "shopee": "Shopee",
    "shein": "Shein",
    "google_shopping": "Google Shopping",
}


def rotulo(fonte: str) -> str:
    return ROTULOS.get(fonte, fonte.replace("_", " ").title())


def _destaque(resumo: ResumoItem) -> str:
    marcas = []
    if resumo.atingiu_alvo:
        marcas.append("🎯 abaixo do alvo")
    variacao = resumo.variacao
    if variacao is not None and variacao <= -5:
        marcas.append(f"📉 {abs(variacao):.0f}% menor que o mínimo anterior")
    elif variacao is not None and variacao >= 10:
        marcas.append(f"📈 {variacao:.0f}% acima do mínimo anterior")
    return " · ".join(marcas)


def titulo_do_dia(momento: datetime | None = None) -> str:
    momento = momento or datetime.now()
    return f"Rotina de compras — {momento.strftime('%d/%m/%Y')}"


def gerar_markdown(resumos: list[ResumoItem], momento: datetime | None = None) -> str:
    linhas = [f"# {titulo_do_dia(momento)}", ""]

    achados = [r for r in resumos if r.atingiu_alvo]
    if achados:
        linhas.append("## 🎯 Bateram o preço-alvo")
        linhas.append("")
        for resumo in achados:
            melhor = resumo.melhor
            linhas.append(
                f"- **{resumo.item}** — {formatar(melhor.preco)} "
                f"em {rotulo(melhor.fonte)} (alvo {formatar(resumo.preco_alvo)}) "
                f"— [ver]({melhor.url})"
            )
        linhas.append("")

    for resumo in resumos:
        linhas.append(f"## {resumo.item}")
        marcas = _destaque(resumo)
        alvo = (
            f"Alvo: {formatar(resumo.preco_alvo)}"
            if resumo.preco_alvo is not None
            else "Sem preço-alvo"
        )
        linhas.append(f"_{alvo}_" + (f" — {marcas}" if marcas else ""))
        linhas.append("")

        if resumo.ofertas:
            linhas.append("| Loja | Produto | Preço | Vendedor |")
            linhas.append("| --- | --- | ---: | --- |")
            ordenadas = sorted(
                resumo.ofertas, key=lambda o: (o.preco is None, o.preco or 0)
            )
            for oferta in ordenadas:
                titulo = oferta.titulo[:70] + ("…" if len(oferta.titulo) > 70 else "")
                nome = f"[{titulo}]({oferta.url})" if oferta.url else titulo
                extra = " 🚚" if oferta.frete_gratis else ""
                linhas.append(
                    f"| {rotulo(oferta.fonte)} | {nome} | "
                    f"{formatar(oferta.preco)}{extra} | {oferta.vendedor or '—'} |"
                )
            linhas.append("")
        else:
            linhas.append("_Nenhuma oferta encontrada._")
            linhas.append("")

        if resumo.erros:
            for fonte, erro in resumo.erros.items():
                linhas.append(f"> ⚠️ {rotulo(fonte)}: {erro}")
            linhas.append("")

    linhas.append("---")
    linhas.append(
        "_Preços de Shopee, Shein e Google Shopping vêm do texto indexado pelo "
        "buscador e podem estar defasados. Confira na página da loja antes de comprar._"
    )
    return "\n".join(linhas)


def gerar_html(resumos: list[ResumoItem], momento: datetime | None = None) -> str:
    partes = [
        "<div style=\"font-family:-apple-system,Segoe UI,Roboto,sans-serif;"
        "max-width:720px;color:#1a1a1a\">",
        f"<h1 style=\"font-size:20px\">{escape(titulo_do_dia(momento))}</h1>",
    ]

    for resumo in resumos:
        partes.append(f"<h2 style=\"font-size:16px;margin-bottom:2px\">{escape(resumo.item)}</h2>")
        marcas = _destaque(resumo)
        if marcas:
            partes.append(
                f"<p style=\"margin:0 0 8px;color:#0a7a35;font-size:13px\">{escape(marcas)}</p>"
            )
        if not resumo.ofertas:
            partes.append("<p style=\"color:#666;font-size:13px\">Nenhuma oferta encontrada.</p>")
            continue

        partes.append(
            "<table style=\"border-collapse:collapse;width:100%;font-size:13px\">"
            "<tr style=\"text-align:left;background:#f4f4f5\">"
            "<th style=\"padding:6px\">Loja</th><th style=\"padding:6px\">Produto</th>"
            "<th style=\"padding:6px;text-align:right\">Preço</th></tr>"
        )
        ordenadas = sorted(resumo.ofertas, key=lambda o: (o.preco is None, o.preco or 0))
        for oferta in ordenadas:
            titulo = escape(oferta.titulo[:70])
            link = (
                f"<a href=\"{escape(oferta.url, quote=True)}\" style=\"color:#1155cc\">{titulo}</a>"
                if oferta.url
                else titulo
            )
            partes.append(
                "<tr style=\"border-top:1px solid #e4e4e7\">"
                f"<td style=\"padding:6px\">{escape(rotulo(oferta.fonte))}</td>"
                f"<td style=\"padding:6px\">{link}</td>"
                f"<td style=\"padding:6px;text-align:right;white-space:nowrap\">"
                f"{escape(formatar(oferta.preco))}</td></tr>"
            )
        partes.append("</table>")

    partes.append(
        "<p style=\"color:#71717a;font-size:11px;margin-top:20px\">Preços de Shopee, "
        "Shein e Google Shopping vêm do texto indexado pelo buscador e podem estar "
        "defasados. Confira na loja antes de comprar.</p></div>"
    )
    return "\n".join(partes)
