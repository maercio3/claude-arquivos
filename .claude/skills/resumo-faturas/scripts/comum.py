"""Funções compartilhadas pelos scripts de fatura.

Mantém em um lugar só o que os três scripts precisam concordar: o schema do
CSV de lançamentos, como um valor em reais vira float e como um texto vira
chave comparável (sem acento, sem caixa).
"""

from __future__ import annotations

import csv
import datetime as _dt
import re
import unicodedata

COLUNAS = [
    "data",
    "descricao",
    "estabelecimento",
    "valor",
    "moeda_origem",
    "valor_origem",
    "cartao",
    "portador",
    "parcela",
    "tipo",
    "titularidade",
    "categoria",
    "centro_custo",
    "confianca",
    "regra",
    "arquivo_origem",
    "obs",
]

COLUNAS_FATURA = [
    "arquivo_origem",
    "banco",
    "cartao",
    "portador",
    "vencimento",
    "periodo_inicio",
    "periodo_fim",
    "total_fatura",
]

TIPOS = {
    "compra",
    "parcela",
    "estorno",
    "pagamento",
    "encargo",
    "anuidade",
    "iof",
    "assinatura",
    "saque",
    "ajuste",
}

# Tipos que não são consumo do titular e por isso ficam de fora dos totais
# gerenciais (o pagamento da fatura anterior não é despesa do mês).
TIPOS_NAO_DESPESA = {"pagamento"}

MESES = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}


def sem_acento(texto: str) -> str:
    """Minúsculas e sem acento — a forma canônica para comparar textos."""
    if texto is None:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def parse_valor(bruto) -> float:
    """Converte valor de fatura em float.

    Aceita '1.234,56', '1234.56', 'R$ 1.234,56', '1.234,56 D', '-89,90' e
    '89,90-' (sinal ao final, comum em extrato). Despesa positiva, crédito
    negativo.
    """
    if bruto is None or bruto == "":
        return 0.0
    if isinstance(bruto, (int, float)):
        return round(float(bruto), 2)

    texto = str(bruto).strip()
    negativo = texto.startswith("-") or texto.endswith("-")
    # marcador de crédito usado por alguns bancos
    if re.search(r"\bC\b\s*$", texto):
        negativo = True
    texto = re.sub(r"[^0-9,.]", "", texto)
    if not texto:
        return 0.0

    if "," in texto and "." in texto:
        # 1.234,56 (pt-BR) ou 1,234.56 (en) — decide pelo separador mais à direita
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")

    try:
        valor = float(texto)
    except ValueError:
        return 0.0
    return round(-abs(valor) if negativo else valor, 2)


def parse_data(bruto, ano_padrao: int | None = None) -> str:
    """Devolve a data em ISO (YYYY-MM-DD) ou '' se não der para entender.

    Faturas costumam trazer '12/03', '12/03/2026' ou '12 MAR'. Quando o ano não
    vem na linha, usa `ano_padrao` (normalmente o ano do vencimento da fatura).
    """
    if not bruto:
        return ""
    texto = sem_acento(bruto).replace(".", "/").replace("-", "/").strip()
    ano_padrao = ano_padrao or _dt.date.today().year

    m = re.match(r"^(\d{4})/(\d{1,2})/(\d{1,2})$", texto)
    if m:
        a, mes, d = (int(x) for x in m.groups())
        return _iso(a, mes, d)

    m = re.match(r"^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?$", texto)
    if m:
        d, mes, a = int(m.group(1)), int(m.group(2)), m.group(3)
        ano = ano_padrao if a is None else (2000 + int(a) if len(a) == 2 else int(a))
        return _iso(ano, mes, d)

    m = re.match(r"^(\d{1,2})\s*/?\s*([a-z]{3})[a-z]*(?:\s*/?\s*(\d{2,4}))?$", texto)
    if m:
        d = int(m.group(1))
        mes = MESES.get(m.group(2), 0)
        a = m.group(3)
        ano = ano_padrao if a is None else (2000 + int(a) if len(a) == 2 else int(a))
        if mes:
            return _iso(ano, mes, d)

    return ""


def _iso(ano: int, mes: int, dia: int) -> str:
    try:
        return _dt.date(ano, mes, dia).isoformat()
    except ValueError:
        return ""


def parse_parcela(bruto) -> tuple[int, int] | None:
    """'3/10' -> (3, 10). Devolve None quando não é parcelado."""
    if not bruto:
        return None
    m = re.search(r"(\d{1,2})\s*(?:/|de)\s*(\d{1,2})", str(bruto))
    if not m:
        return None
    atual, total = int(m.group(1)), int(m.group(2))
    if total < 2 or atual > total:
        return None
    return atual, total


def brl(valor: float) -> str:
    """1234.5 -> 'R$ 1.234,50'"""
    sinal = "-" if valor < 0 else ""
    inteiro, centavos = divmod(round(abs(valor) * 100), 100)
    milhar = f"{inteiro:,}".replace(",", ".")
    return f"{sinal}R$ {milhar},{centavos:02d}"


def ler_lancamentos(caminho: str) -> list[dict]:
    """Lê o CSV de lançamentos já com valor em float e data em ISO."""
    linhas = []
    with open(caminho, newline="", encoding="utf-8-sig") as fh:
        for i, bruta in enumerate(csv.DictReader(fh), start=2):
            linha = {c: (bruta.get(c) or "").strip() for c in COLUNAS}
            linha["valor"] = parse_valor(bruta.get("valor"))
            linha["valor_origem"] = parse_valor(bruta.get("valor_origem")) or ""
            linha["data"] = parse_data(bruta.get("data")) or (bruta.get("data") or "").strip()
            linha["cartao"] = re.sub(r"\D", "", linha["cartao"])[-4:]
            linha["_linha"] = i
            linhas.append(linha)
    return linhas


def escrever_lancamentos(caminho: str, linhas: list[dict]) -> None:
    with open(caminho, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUNAS, extrasaction="ignore")
        w.writeheader()
        for linha in linhas:
            saida = dict(linha)
            if isinstance(saida.get("valor"), float):
                saida["valor"] = f"{saida['valor']:.2f}"
            w.writerow(saida)


def ler_faturas(caminho: str) -> list[dict]:
    faturas = []
    with open(caminho, newline="", encoding="utf-8-sig") as fh:
        for bruta in csv.DictReader(fh):
            fatura = {c: (bruta.get(c) or "").strip() for c in COLUNAS_FATURA}
            fatura["total_fatura"] = parse_valor(bruta.get("total_fatura"))
            fatura["cartao"] = re.sub(r"\D", "", fatura["cartao"])[-4:]
            faturas.append(fatura)
    return faturas


def carregar_config(caminho: str | None) -> dict:
    """Config é opcional: sem ela os scripts ainda rodam, só sem regras."""
    if not caminho:
        return {}
    try:
        import yaml
    except ImportError:
        raise SystemExit("Falta o pacote PyYAML: pip install pyyaml")
    try:
        with open(caminho, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except FileNotFoundError:
        return {}


def despesas(linhas: list[dict]) -> list[dict]:
    """Só o que é consumo do período — sem pagamento de fatura anterior."""
    return [l for l in linhas if l.get("tipo") not in TIPOS_NAO_DESPESA]
