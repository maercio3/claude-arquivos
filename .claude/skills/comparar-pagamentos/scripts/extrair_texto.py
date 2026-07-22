#!/usr/bin/env python3
"""
Extrai texto de um PDF (relatorio do software ou comprovante do banco).

Uso:
    python extrair_texto.py arquivo.pdf
    python extrair_texto.py arquivo.pdf --tabelas   # tenta extrair tabelas tambem

Serve para PDFs com camada de texto. Para comprovantes que sao imagem/print
(PNG/JPG ou PDF escaneado), NAO use este script: leia o arquivo diretamente
com visao (a ferramenta Read do Claude), que enxerga o conteudo da imagem.

Requer pdfplumber (pip install pdfplumber). O SKILL.md explica o fallback caso
a lib nao esteja instalada.
"""
import argparse
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--tabelas", action="store_true",
                    help="imprime tambem as tabelas detectadas por pagina")
    args = ap.parse_args()

    try:
        import pdfplumber
    except ImportError:
        sys.exit("pdfplumber nao instalado. Rode: pip install pdfplumber")

    with pdfplumber.open(args.pdf) as pdf:
        print(f"# {args.pdf} — {len(pdf.pages)} pagina(s)\n")
        for i, page in enumerate(pdf.pages, start=1):
            print(f"===== PAGINA {i} =====")
            texto = page.extract_text() or "(sem texto — possivelmente imagem)"
            print(texto)
            if args.tabelas:
                for t_idx, tabela in enumerate(page.extract_tables(), start=1):
                    print(f"\n--- TABELA {t_idx} (pagina {i}) ---")
                    for linha in tabela:
                        print(" | ".join("" if c is None else str(c) for c in linha))
            print()


if __name__ == "__main__":
    main()
