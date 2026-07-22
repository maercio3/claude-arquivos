#!/usr/bin/env python3
"""
Anexa comprovantes aos lançamentos correspondentes no Mais Controle ERP,
via automação de navegador (Playwright).

Segurança:
  - As credenciais NUNCA ficam no código nem em arquivo versionado. São lidas
    das variáveis de ambiente MAISCONTROLE_USER e MAISCONTROLE_PASS, fornecidas
    na hora de rodar.
  - A sessão do navegador é persistida em ./sessao/ (fora do Git) só para não
    refazer login/2FA a cada item; apague essa pasta para "deslogar".

2FA/CAPTCHA:
  - O script preenche usuário e senha e então PAUSA, esperando você concluir o
    segundo fator/captcha na janela do navegador e apertar Enter no terminal.

Entrada:
  - plano.json: lista de itens a anexar, tipicamente derivada da conferência
    (skill comparar-pagamentos). Cada item:
      {
        "n_doc": "ref oc 3414",           # identificador para achar o lançamento
        "valor": "R$ 360,00",             # usado como reforço/validação
        "favorecido": "K CARDOSO",        # usado como reforço/validação
        "arquivo": "/caminho/comprovante.png"  # arquivo a anexar (deve existir)
      }
  - config.json (opcional): URLs e seletores da tela. Um modelo é criado com
    --init-config. Os seletores marcados como "CONFIRMAR" devem ser ajustados
    na calibração (primeira execução guiada).

Uso típico:
  export MAISCONTROLE_USER="..."; export MAISCONTROLE_PASS="..."
  python anexar.py --plano plano.json --config config.json
  python anexar.py --plano plano.json --config config.json --dry-run   # sem salvar
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path


CONFIG_MODELO = {
    "url_login": "https://app.maiscontroleerp.com.br/",
    "url_pagamentos": "",  # se souber a URL direta de Financeiro>Pagamentos, coloque aqui
    "headless": False,     # SEMPRE False quando houver 2FA/captcha (precisa ver a tela)
    "seletores": {
        # Cada entrada aceita uma lista de tentativas; a 1a que existir na tela é usada.
        # Use rótulos/texto visíveis quando possível — são mais estáveis que classes CSS.
        "campo_usuario": ["input[name=email]", "input[type=email]", "#email", "#usuario"],
        "campo_senha": ["input[name=senha]", "input[type=password]", "#senha", "#password"],
        "botao_entrar": ["button:has-text('Entrar')", "button[type=submit]", "text=Entrar"],
        # navegacao ate a lista de pagamentos (CONFIRMAR na calibracao):
        "menu_financeiro": ["text=Financeiro"],
        "menu_pagamentos": ["text=Pagamentos", "text=Contas a Pagar"],
        # busca de um lançamento pelo N° Doc / texto:
        "campo_busca": ["input[type=search]", "input[placeholder*='Pesquis']", "input[placeholder*='Buscar']"],
        # abrir o lançamento encontrado (CONFIRMAR):
        "abrir_lancamento": ["text={busca}"],
        # campo de anexo dentro do lançamento (CONFIRMAR):
        "aba_arquivos": ["text=Arquivos", "text=Anexos", "text=Anexar"],
        "input_arquivo": ["input[type=file]"],
        "botao_salvar": ["button:has-text('Salvar')", "button:has-text('Gravar')", "text=Salvar"],
    },
    "tempo_espera_ms": 15000,
}


def carregar_json(caminho):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def primeiro_visivel(page, tentativas, timeout=3000, subst=None):
    """Retorna o primeiro locator que existe/está visível dentre as tentativas."""
    for sel in tentativas:
        if subst:
            for k, v in subst.items():
                sel = sel.replace("{" + k + "}", v)
        loc = page.locator(sel).first
        try:
            loc.wait_for(state="visible", timeout=timeout)
            return loc
        except Exception:
            continue
    return None


def logar(page, cfg):
    user = os.environ.get("MAISCONTROLE_USER")
    pwd = os.environ.get("MAISCONTROLE_PASS")
    if not user or not pwd:
        sys.exit("Defina MAISCONTROLE_USER e MAISCONTROLE_PASS no ambiente antes de rodar.")

    page.goto(cfg["url_login"], wait_until="domcontentloaded")
    sel = cfg["seletores"]

    campo_user = primeiro_visivel(page, sel["campo_usuario"], timeout=8000)
    if campo_user:
        campo_user.fill(user)
        campo_senha = primeiro_visivel(page, sel["campo_senha"], timeout=8000)
        if campo_senha:
            campo_senha.fill(pwd)
        botao = primeiro_visivel(page, sel["botao_entrar"], timeout=5000)
        if botao:
            botao.click()
    else:
        print("[!] Não encontrei o campo de usuário automaticamente — faça o login manualmente na janela.")

    # PAUSA para 2FA / captcha / confirmação
    print("\n==============================================================")
    print(" Conclua o LOGIN + 2FA/CAPTCHA na janela do navegador.")
    print(" Quando estiver DENTRO do sistema, volte aqui e aperte Enter.")
    print("==============================================================")
    try:
        input()
    except EOFError:
        # sem terminal interativo: espera fixa como fallback
        print("[i] Sem terminal interativo; aguardando 60s para o login manual...")
        time.sleep(60)


def anexar_um(page, cfg, item, dry_run):
    sel = cfg["seletores"]
    busca = str(item.get("n_doc") or item.get("valor") or "").strip()
    arquivo = item.get("arquivo", "")

    if not arquivo or not Path(arquivo).exists():
        return {"item": busca, "ok": False, "motivo": f"arquivo não encontrado: {arquivo}"}

    # se houver URL direta de pagamentos, vá para ela; senão navegue pelos menus
    if cfg.get("url_pagamentos"):
        page.goto(cfg["url_pagamentos"], wait_until="domcontentloaded")
    else:
        fin = primeiro_visivel(page, sel["menu_financeiro"], timeout=5000)
        if fin:
            fin.click()
        pag = primeiro_visivel(page, sel["menu_pagamentos"], timeout=5000)
        if pag:
            pag.click()

    # buscar o lançamento
    campo_busca = primeiro_visivel(page, sel["campo_busca"], timeout=8000)
    if campo_busca:
        campo_busca.fill(busca)
        campo_busca.press("Enter")
        page.wait_for_timeout(1500)

    alvo = primeiro_visivel(page, sel["abrir_lancamento"], timeout=6000, subst={"busca": busca})
    if not alvo:
        return {"item": busca, "ok": False, "motivo": "lançamento não localizado na busca"}
    alvo.click()
    page.wait_for_timeout(1000)

    # abrir aba/área de arquivos, se houver
    aba = primeiro_visivel(page, sel["aba_arquivos"], timeout=4000)
    if aba:
        aba.click()
        page.wait_for_timeout(500)

    # anexar o arquivo
    input_file = primeiro_visivel(page, sel["input_arquivo"], timeout=6000)
    if not input_file:
        return {"item": busca, "ok": False, "motivo": "campo de anexo (input[type=file]) não encontrado"}
    input_file.set_input_files(arquivo)
    page.wait_for_timeout(1000)

    if dry_run:
        return {"item": busca, "ok": True, "motivo": "dry-run: anexado mas NÃO salvo"}

    salvar = primeiro_visivel(page, sel["botao_salvar"], timeout=5000)
    if salvar:
        salvar.click()
        page.wait_for_timeout(1500)
        return {"item": busca, "ok": True, "motivo": "anexado e salvo"}
    return {"item": busca, "ok": False, "motivo": "anexei mas não achei o botão Salvar — verifique manualmente"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plano", help="JSON com os itens a anexar")
    ap.add_argument("--config", default="config.json", help="JSON de configuração (URLs/seletores)")
    ap.add_argument("--init-config", action="store_true", help="cria um config.json modelo e sai")
    ap.add_argument("--dry-run", action="store_true", help="anexa mas não clica em Salvar")
    ap.add_argument("--sessao", default="sessao", help="pasta do perfil do navegador (fora do Git)")
    args = ap.parse_args()

    if args.init_config:
        with open(args.config, "w", encoding="utf-8") as f:
            json.dump(CONFIG_MODELO, f, ensure_ascii=False, indent=2)
        print(f"Modelo criado em {args.config}. Ajuste os seletores 'CONFIRMAR' na calibração.")
        return

    if not args.plano:
        sys.exit("Informe --plano plano.json (ou use --init-config para gerar o modelo).")

    cfg = carregar_json(args.config) if Path(args.config).exists() else CONFIG_MODELO
    plano = carregar_json(args.plano)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("Playwright não instalado. Rode: pip install playwright  (o Chromium já existe neste ambiente).")

    resultados = []
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            args.sessao,
            headless=cfg.get("headless", False),
            accept_downloads=True,
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        logar(page, cfg)

        for item in plano:
            try:
                res = anexar_um(page, cfg, item, args.dry_run)
            except Exception as e:
                res = {"item": item.get("n_doc") or item.get("valor"), "ok": False, "motivo": f"erro: {e}"}
            estado = "OK " if res["ok"] else "FALHA"
            print(f"[{estado}] {res['item']}: {res['motivo']}")
            resultados.append(res)

        ctx.close()

    with open("resultado_anexos.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    ok = sum(1 for r in resultados if r["ok"])
    print(f"\nConcluído: {ok}/{len(resultados)} anexados. Detalhes em resultado_anexos.json")


if __name__ == "__main__":
    main()
