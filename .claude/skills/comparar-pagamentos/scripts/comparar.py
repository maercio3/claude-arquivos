#!/usr/bin/env python3
"""
Compara pagamentos de um relatorio de software de controle com comprovantes de banco.

Entrada: dois arquivos JSON (lista de objetos):
  - pagamentos.json  -> lancamentos extraidos do relatorio do software
  - comprovantes.json -> comprovantes extraidos dos arquivos do banco

Saida:
  - <saida>.xlsx  -> planilha detalhada (Conferencia, Sem comprovante, Comprovantes extras)
  - <saida>.md    -> resumo executivo em texto

O casamento e feito por valor (chave forte) + corroboracao por nome, documento
(CPF/CNPJ, ciente de mascara) e data. Tolerancias sao configuraveis.

Schema esperado (campos ausentes viram vazio):

pagamento = {
  "valor": 360.00 ou "R$ 360,00",
  "data": "2026-07-21" ou "21/07/2026",
  "favorecido": "K CARDOSO",
  "documento": "501.621.013-68",      # CPF/CNPJ do campo "Dados", se houver
  "chave_pix": "+5586994045991",       # chave/telefone/email do campo "Dados", se houver
  "n_doc": "ref oc 3414",
  "forma": "Pix",
  "descricao": "Folha adiantamento",
  "status": "Em aberto"
}

comprovante = {
  "valor": 765.00 ou "R$ 765,00",
  "data": "2026-07-21",
  "horario": "08h44",
  "id_transacao": "E0041...",
  "recebedor_nome": "Mario Barbosa Lima",
  "recebedor_documento": "***.290.871-**",   # normalmente mascarado
  "recebedor_chave": "+5563981389094",
  "pagador_nome": "ANA K S CARDOSO LTDA",
  "arquivo": "comprovante1.png"
}
"""
import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, date
from difflib import SequenceMatcher


# --------------------------------------------------------------------------- #
# Normalizacao
# --------------------------------------------------------------------------- #
def para_centavos(valor):
    """Converte 'R$ 1.775,00', '1775.00', 1775.0 -> 177500 (int centavos)."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        return int(round(float(valor) * 100))
    s = str(valor)
    s = re.sub(r"[^\d,.\-]", "", s)
    if not s:
        return None
    # formato brasileiro: ponto = milhar, virgula = decimal
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return int(round(float(s) * 100))
    except ValueError:
        return None


def fmt_reais(centavos):
    if centavos is None:
        return ""
    return "R$ " + f"{centavos/100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def so_digitos(s):
    return re.sub(r"\D", "", str(s or ""))


def normalizar_nome(nome):
    """minusculo, sem acento, sem sufixos societarios, espacos colapsados."""
    if not nome:
        return ""
    s = unicodedata.normalize("NFKD", str(nome))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    # remove sufixos/palavras societarias que nao ajudam a distinguir
    lixo = {"ltda", "me", "epp", "eireli", "sa", "s", "a", "de", "da",
            "do", "dos", "das", "e", "cia"}
    tokens = [t for t in s.split() if t and t not in lixo]
    return " ".join(tokens)


def similaridade_nome(a, b):
    """0..1 combinando razao de sequencia e sobreposicao de tokens."""
    na, nb = normalizar_nome(a), normalizar_nome(b)
    if not na or not nb:
        return 0.0
    seq = SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    jac = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0
    return max(seq, jac)


def parse_data(valor):
    if not valor:
        return None
    if isinstance(valor, date):
        return valor
    s = str(valor).strip()
    # pega o primeiro padrao de data reconhecivel (ignora "Terca-feira," etc.)
    m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    return None


# --------------------------------------------------------------------------- #
# Casamento de documento (ciente de mascara de CPF)
# --------------------------------------------------------------------------- #
def digitos_visiveis_mascara(doc):
    """De '***.290.871-**' extrai '290871' (os grupos visiveis do meio)."""
    return so_digitos(doc)


def documento_bate(pag_doc, pag_chave, comp_doc, comp_chave):
    """
    Retorna (bate: bool, forca: 'forte'|'parcial'|'') comparando documentos/chaves.

    Trata:
      - CPF completo (relatorio) x CPF mascarado ***.NNN.NNN-** (comprovante):
        compara os 6 digitos do meio.
      - CNPJ completo dos dois lados (14 digitos).
      - Chave Pix telefone: compara os ultimos 10-11 digitos (ignora +55).
      - Chave Pix = CPF/CNPJ completo.
    """
    lados_pag = [so_digitos(pag_doc), so_digitos(pag_chave)]
    lados_comp = [so_digitos(comp_doc), so_digitos(comp_chave)]
    lados_pag = [x for x in lados_pag if x]
    lados_comp = [x for x in lados_comp if x]

    for p in lados_pag:
        for c in lados_comp:
            if not p or not c:
                continue
            # match exato completo (CNPJ, CPF completo dos dois lados, chave numerica)
            if p == c:
                return True, "forte"
            # CNPJ (14) exato
            if len(p) == 14 and len(c) == 14 and p == c:
                return True, "forte"
            # telefone: compara ultimos 10-11 digitos
            if len(p) >= 10 and len(c) >= 10:
                if p[-11:] == c[-11:] or p[-10:] == c[-10:]:
                    return True, "forte"
            # CPF completo (11) x mascara (6 digitos do meio)
            if len(p) == 11 and len(c) == 6:
                if p[3:9] == c:
                    return True, "forte"
            if len(c) == 11 and len(p) == 6:
                if c[3:9] == p:
                    return True, "forte"
            # CPF completo x chave que contem o CPF
            if len(p) == 11 and c.endswith(p):
                return True, "forte"
            if len(c) == 11 and p.endswith(c):
                return True, "forte"
    return False, ""


# --------------------------------------------------------------------------- #
# Pontuacao de candidato
# --------------------------------------------------------------------------- #
def pontuar(pag, comp, tol_centavos, tol_dias):
    pv = para_centavos(pag.get("valor"))
    cv = para_centavos(comp.get("valor"))
    if pv is None or cv is None:
        return None
    dif_valor = abs(pv - cv)
    if dif_valor > tol_centavos:
        return None  # fora da tolerancia de valor -> nao e candidato

    sim = similaridade_nome(pag.get("favorecido"), comp.get("recebedor_nome"))
    doc_ok, doc_forca = documento_bate(
        pag.get("documento"), pag.get("chave_pix"),
        comp.get("recebedor_documento"), comp.get("recebedor_chave"),
    )

    dp = parse_data(pag.get("data"))
    dc = parse_data(comp.get("data"))
    dif_dias = abs((dp - dc).days) if (dp and dc) else None

    # score: valor sempre pesa; nome e documento corroboram; data ajusta
    score = 0.0
    score += 100 if dif_valor == 0 else max(0, 40 - dif_valor / 100.0)
    score += 60 * sim
    if doc_ok:
        score += 80 if doc_forca == "forte" else 40
    if dif_dias is not None:
        if dif_dias == 0:
            score += 20
        elif dif_dias <= tol_dias:
            score += 10
        else:
            score -= 15

    detalhe = {
        "dif_valor_centavos": dif_valor,
        "sim_nome": round(sim, 3),
        "doc_ok": doc_ok,
        "doc_forca": doc_forca,
        "dif_dias": dif_dias,
        "score": round(score, 2),
    }
    return detalhe


def classificar(pag, comp, det, tol_dias):
    """Decide status e lista de divergencias de um par casado."""
    divs = []
    if det["dif_valor_centavos"] != 0:
        divs.append(f"valor difere em {fmt_reais(det['dif_valor_centavos'])}")
    if det["dif_dias"] is not None and det["dif_dias"] > tol_dias:
        divs.append(f"data difere em {det['dif_dias']} dia(s)")
    nome_ok = det["sim_nome"] >= 0.6
    if not nome_ok and not det["doc_ok"]:
        divs.append("nome e documento nao conferem")
    elif not nome_ok:
        divs.append("nome diverge (documento confere)")

    if not divs:
        return "Conferido", divs
    return "Divergente", divs


# --------------------------------------------------------------------------- #
# Motor
# --------------------------------------------------------------------------- #
def conciliar(pagamentos, comprovantes, tol_centavos, tol_dias):
    comp_usados = set()
    linhas = []

    for pag in pagamentos:
        candidatos = []
        for j, comp in enumerate(comprovantes):
            if j in comp_usados:
                continue
            det = pontuar(pag, comp, tol_centavos, tol_dias)
            if det is not None:
                candidatos.append((det["score"], j, det))
        candidatos.sort(key=lambda x: x[0], reverse=True)

        if candidatos:
            score, j, det = candidatos[0]
            comp = comprovantes[j]
            # exige um minimo de corroboracao alem do valor para casar
            corrobora = det["sim_nome"] >= 0.45 or det["doc_ok"] or det["dif_valor_centavos"] == 0
            if corrobora:
                comp_usados.add(j)
                status, divs = classificar(pag, comp, det, tol_dias)
                linhas.append({"pag": pag, "comp": comp, "status": status,
                               "divs": divs, "det": det})
                continue
        # sem candidato aceitavel
        linhas.append({"pag": pag, "comp": None, "status": "Sem comprovante",
                       "divs": [], "det": None})

    extras = [comprovantes[j] for j in range(len(comprovantes)) if j not in comp_usados]
    return linhas, extras


# --------------------------------------------------------------------------- #
# Saidas
# --------------------------------------------------------------------------- #
CORES = {
    "Conferido": "C6EFCE",
    "Divergente": "FFEB9C",
    "Sem comprovante": "FFC7CE",
    "Comprovante sem lançamento": "D9D9D9",
}


def gerar_xlsx(linhas, extras, caminho, meta):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Conferência"

    cab = ["Status", "Valor (software)", "Valor (comprovante)", "Data (software)",
           "Data (comprovante)", "Favorecido (software)", "Recebedor (comprovante)",
           "Documento (software)", "Documento (comprovante)", "N° Doc", "Forma",
           "ID transação", "Arquivo comprovante", "Divergências"]

    titulo = Font(bold=True, color="FFFFFF")
    fill_cab = PatternFill("solid", fgColor="305496")
    borda = Border(*[Side(style="thin", color="D0D0D0")] * 4)
    wrap = Alignment(vertical="top", wrap_text=True)

    ws.append(cab)
    for c in range(1, len(cab) + 1):
        cel = ws.cell(row=1, column=c)
        cel.font = titulo
        cel.fill = fill_cab
        cel.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)

    def add(row, status):
        ws.append(row)
        r = ws.max_row
        fill = PatternFill("solid", fgColor=CORES.get(status, "FFFFFF"))
        for c in range(1, len(cab) + 1):
            cel = ws.cell(row=r, column=c)
            cel.fill = fill
            cel.alignment = wrap
            cel.border = borda

    for ln in linhas:
        p = ln["pag"]
        comp = ln["comp"] or {}
        add([
            ln["status"],
            fmt_reais(para_centavos(p.get("valor"))),
            fmt_reais(para_centavos(comp.get("valor"))) if comp else "",
            p.get("data", ""),
            comp.get("data", "") if comp else "",
            p.get("favorecido", ""),
            comp.get("recebedor_nome", "") if comp else "",
            p.get("documento") or p.get("chave_pix", ""),
            (comp.get("recebedor_documento") or comp.get("recebedor_chave", "")) if comp else "",
            p.get("n_doc", ""),
            p.get("forma", ""),
            comp.get("id_transacao", "") if comp else "",
            comp.get("arquivo", "") if comp else "",
            "; ".join(ln["divs"]),
        ], ln["status"])

    for comp in extras:
        add([
            "Comprovante sem lançamento", "",
            fmt_reais(para_centavos(comp.get("valor"))), "",
            comp.get("data", ""), "", comp.get("recebedor_nome", ""), "",
            comp.get("recebedor_documento") or comp.get("recebedor_chave", ""),
            "", "", comp.get("id_transacao", ""), comp.get("arquivo", ""),
            "sem lançamento correspondente no software",
        ], "Comprovante sem lançamento")

    larguras = [20, 16, 18, 15, 16, 28, 28, 20, 20, 14, 14, 30, 24, 34]
    for i, w in enumerate(larguras, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cab))}{ws.max_row}"

    # aba resumo
    ws2 = wb.create_sheet("Resumo")
    for k, v in meta.items():
        ws2.append([k, v])
    ws2.column_dimensions["A"].width = 34
    ws2.column_dimensions["B"].width = 22
    for r in range(1, ws2.max_row + 1):
        ws2.cell(row=r, column=1).font = Font(bold=True)

    wb.save(caminho)


def gerar_md(linhas, extras, meta, caminho):
    conf = [l for l in linhas if l["status"] == "Conferido"]
    div = [l for l in linhas if l["status"] == "Divergente"]
    sem = [l for l in linhas if l["status"] == "Sem comprovante"]

    out = []
    out.append("# Resumo da Conferência de Pagamentos\n")
    for k, v in meta.items():
        out.append(f"- **{k}:** {v}")
    out.append("")
    out.append(f"## ✅ Conferidos ({len(conf)})")
    for l in conf:
        p = l["pag"]
        out.append(f"- {fmt_reais(para_centavos(p.get('valor')))} — {p.get('favorecido','')} "
                   f"({p.get('n_doc','')})")
    out.append("")
    out.append(f"## ⚠️ Divergentes ({len(div)})")
    for l in div:
        p = l["pag"]
        out.append(f"- {fmt_reais(para_centavos(p.get('valor')))} — {p.get('favorecido','')} "
                   f"({p.get('n_doc','')}): {'; '.join(l['divs'])}")
    out.append("")
    out.append(f"## ❌ Sem comprovante ({len(sem)})")
    for l in sem:
        p = l["pag"]
        out.append(f"- {fmt_reais(para_centavos(p.get('valor')))} — {p.get('favorecido','')} "
                   f"({p.get('n_doc','')})")
    out.append("")
    out.append(f"## 🔎 Comprovantes sem lançamento ({len(extras)})")
    for comp in extras:
        out.append(f"- {fmt_reais(para_centavos(comp.get('valor')))} — "
                   f"{comp.get('recebedor_nome','')} ({comp.get('arquivo','')})")
    out.append("")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("\n".join(out))


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Concilia pagamentos x comprovantes")
    ap.add_argument("pagamentos", help="JSON dos lancamentos do software")
    ap.add_argument("comprovantes", help="JSON dos comprovantes do banco")
    ap.add_argument("-o", "--saida", default="conferencia",
                    help="prefixo dos arquivos de saida (default: conferencia)")
    ap.add_argument("--tol-valor", type=float, default=0.0,
                    help="tolerancia de valor em reais (default: 0.00 = exato)")
    ap.add_argument("--tol-dias", type=int, default=3,
                    help="tolerancia de data em dias (default: 3)")
    args = ap.parse_args()

    with open(args.pagamentos, encoding="utf-8") as f:
        pagamentos = json.load(f)
    with open(args.comprovantes, encoding="utf-8") as f:
        comprovantes = json.load(f)

    tol_centavos = int(round(args.tol_valor * 100))
    linhas, extras = conciliar(pagamentos, comprovantes, tol_centavos, args.tol_dias)

    conf = sum(1 for l in linhas if l["status"] == "Conferido")
    div = sum(1 for l in linhas if l["status"] == "Divergente")
    sem = sum(1 for l in linhas if l["status"] == "Sem comprovante")
    total_pag = sum(para_centavos(l["pag"].get("valor")) or 0 for l in linhas)
    total_comp = sum(para_centavos(c.get("valor")) or 0 for c in comprovantes)

    meta = {
        "Gerado em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Lançamentos no software": len(pagamentos),
        "Comprovantes do banco": len(comprovantes),
        "Conferidos": conf,
        "Divergentes": div,
        "Sem comprovante": sem,
        "Comprovantes sem lançamento": len(extras),
        "Total software": fmt_reais(total_pag),
        "Total comprovantes": fmt_reais(total_comp),
        "Tolerância valor": fmt_reais(tol_centavos),
        "Tolerância data (dias)": args.tol_dias,
    }

    xlsx = f"{args.saida}.xlsx"
    md = f"{args.saida}.md"
    gerar_xlsx(linhas, extras, xlsx, meta)
    gerar_md(linhas, extras, meta, md)

    print(f"OK -> {xlsx}")
    print(f"OK -> {md}")
    for k, v in meta.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
