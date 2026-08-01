#!/usr/bin/env python3
"""Alterna a senha do Wi-Fi entre duas senhas fixas (A e B).

O script nao mexe no roteador: ele guarda qual das duas senhas esta valendo,
mostra a proxima e so registra a troca depois que voce confirma que aplicou no
painel. Assim o estado nunca fica mentindo sobre a rede real.

Uso tipico:
    python3 wifi_toggle.py init --ssid CasaWiFi --painel-url http://192.168.0.1
    python3 wifi_toggle.py status
    python3 wifi_toggle.py trocar
    python3 wifi_toggle.py confirmar
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

SLOTS = ("a", "b")
HISTORICO_MAX = 50


# --------------------------------------------------------------------------
# Caminhos e IO
# --------------------------------------------------------------------------

def base_dir() -> Path:
    """Diretorio de dados. WIFI_TOGGLE_HOME permite testar sem tocar no real."""
    env = os.environ.get("WIFI_TOGGLE_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".config" / "wifi-toggle-senha"


def config_path() -> Path:
    return base_dir() / "config.json"


def state_path() -> Path:
    return base_dir() / "state.json"


def _ler_json(caminho: Path) -> dict:
    with caminho.open(encoding="utf-8") as fh:
        return json.load(fh)


def _escrever_json_seguro(caminho: Path, dados: dict) -> None:
    """Grava com permissao 600 (dono apenas) — o arquivo guarda senhas."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(caminho.parent, 0o700)
    tmp = caminho.with_suffix(caminho.suffix + ".tmp")
    with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w",
                   encoding="utf-8") as fh:
        json.dump(dados, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, caminho)
    os.chmod(caminho, 0o600)


def agora() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def erro(msg: str, codigo: int = 1) -> None:
    print(f"Erro: {msg}", file=sys.stderr)
    raise SystemExit(codigo)


# --------------------------------------------------------------------------
# Config e estado
# --------------------------------------------------------------------------

def carregar_config() -> dict:
    caminho = config_path()
    if not caminho.exists():
        erro(f"config nao encontrada em {caminho}. Rode `init` primeiro.", 2)
    cfg = _ler_json(caminho)
    for slot in SLOTS:
        if not cfg.get("senhas", {}).get(slot, {}).get("senha"):
            erro(f"config sem a senha do slot {slot.upper()}. Rode `init` de novo.", 2)
    return cfg


def carregar_estado() -> dict:
    caminho = state_path()
    if not caminho.exists():
        return {"ativa": "a", "alterada_em": None, "pendente": None, "historico": []}
    return _ler_json(caminho)


def salvar_estado(estado: dict) -> None:
    estado["historico"] = estado.get("historico", [])[-HISTORICO_MAX:]
    _escrever_json_seguro(state_path(), estado)


def rotulo(cfg: dict, slot: str) -> str:
    return cfg["senhas"][slot].get("rotulo") or f"senha {slot.upper()}"


def senha(cfg: dict, slot: str) -> str:
    return cfg["senhas"][slot]["senha"]


def outro(slot: str) -> str:
    return "b" if slot == "a" else "a"


def wifi_uri(cfg: dict, slot: str) -> str:
    """String padrao de QR code de Wi-Fi (WPA)."""
    def esc(v: str) -> str:
        for ch in ("\\", ";", ",", ":", '"'):
            v = v.replace(ch, "\\" + ch)
        return v
    return f"WIFI:T:WPA;S:{esc(cfg['ssid'])};P:{esc(senha(cfg, slot))};;"


# --------------------------------------------------------------------------
# Saida
# --------------------------------------------------------------------------

def responder(dados: dict, texto: list[str], como_json: bool) -> None:
    if como_json:
        print(json.dumps(dados, ensure_ascii=False, indent=2))
    else:
        print("\n".join(texto))


def passos(cfg: dict, slot_destino: str) -> list[str]:
    """Passo a passo para aplicar a senha no painel do roteador."""
    modelo = cfg.get("modelo_roteador") or "seu roteador"
    url = cfg.get("painel_url") or "o endereco do painel (geralmente http://192.168.0.1)"
    caminho_menu = cfg.get("caminho_menu") or "Wireless / Wi-Fi > Seguranca (WPA2/WPA3)"
    return [
        f"1. Abra {url} no navegador e entre no painel do {modelo}.",
        f"2. Va em: {caminho_menu}.",
        f"3. Troque a senha da rede '{cfg['ssid']}' para: {senha(cfg, slot_destino)}",
        "4. Salve e espere o roteador aplicar (alguns reiniciam o radio; a rede cai por alguns segundos).",
        "5. Reconecte um aparelho para confirmar que a senha nova funciona.",
        "6. Volte aqui e confirme a troca para eu registrar o estado.",
    ]


# --------------------------------------------------------------------------
# Comandos
# --------------------------------------------------------------------------

def cmd_init(args) -> None:
    caminho = config_path()
    if caminho.exists() and not args.force:
        erro(f"ja existe config em {caminho}. Use --force para sobrescrever.", 3)

    def pedir_senha(slot: str, valor: str | None) -> str:
        if valor:
            return valor
        if not sys.stdin.isatty():
            erro(f"faltou --senha-{slot} (sem terminal para perguntar).", 4)
        while True:
            v = getpass.getpass(f"Senha do slot {slot.upper()} (nao aparece na tela): ")
            if len(v) >= 8:
                return v
            print("A senha WPA2 precisa de pelo menos 8 caracteres.")

    senha_a = pedir_senha("a", args.senha_a)
    senha_b = pedir_senha("b", args.senha_b)

    if senha_a == senha_b:
        erro("as duas senhas sao iguais — nao haveria troca nenhuma.", 5)
    for nome, valor in (("A", senha_a), ("B", senha_b)):
        if len(valor) < 8:
            erro(f"a senha {nome} tem menos de 8 caracteres e o WPA2 nao aceita.", 5)

    cfg = {
        "ssid": args.ssid,
        "painel_url": args.painel_url,
        "modelo_roteador": args.modelo,
        "caminho_menu": args.caminho_menu,
        "senhas": {
            "a": {"rotulo": args.rotulo_a, "senha": senha_a},
            "b": {"rotulo": args.rotulo_b, "senha": senha_b},
        },
        "criada_em": agora(),
    }
    _escrever_json_seguro(caminho, cfg)

    estado = {
        "ativa": args.ativa,
        "alterada_em": agora(),
        "pendente": None,
        "historico": [{"quando": agora(), "evento": "init", "para": args.ativa}],
    }
    salvar_estado(estado)

    texto = [
        f"Config criada em {caminho} (permissao 600).",
        f"Rede: {cfg['ssid']} | slot ativo agora: {args.ativa.upper()} ({rotulo(cfg, args.ativa)})",
        "Rode `trocar` quando quiser alternar para a outra senha.",
    ]
    responder({"ok": True, "config": str(caminho), "ativa": args.ativa}, texto, args.json)


def cmd_config(args) -> None:
    """Ajusta campos nao secretos sem exigir redigitar as senhas."""
    cfg = carregar_config()
    campos = {
        "ssid": args.ssid,
        "painel_url": args.painel_url,
        "modelo_roteador": args.modelo,
        "caminho_menu": args.caminho_menu,
    }
    alterados = {k: v for k, v in campos.items() if v is not None}
    cfg.update(alterados)
    for slot, novo in (("a", args.rotulo_a), ("b", args.rotulo_b)):
        if novo is not None:
            cfg["senhas"][slot]["rotulo"] = novo
            alterados[f"rotulo_{slot}"] = novo
    for slot, nova in (("a", args.senha_a), ("b", args.senha_b)):
        if nova is not None:
            if len(nova) < 8:
                erro(f"a senha {slot.upper()} tem menos de 8 caracteres e o WPA2 nao aceita.", 5)
            cfg["senhas"][slot]["senha"] = nova
            alterados[f"senha_{slot}"] = "(atualizada)"
    if senha(cfg, "a") == senha(cfg, "b"):
        erro("as duas senhas ficariam iguais — nao haveria troca nenhuma.", 5)

    if not alterados:
        responder({"ok": True, "alterados": {}}, ["Nada para alterar."], args.json)
        return

    cfg["atualizada_em"] = agora()
    _escrever_json_seguro(config_path(), cfg)
    texto = ["Config atualizada:"] + [f"  {k} = {v}" for k, v in alterados.items()]
    responder({"ok": True, "alterados": alterados}, texto, args.json)


def cmd_status(args) -> None:
    cfg = carregar_config()
    estado = carregar_estado()
    ativa = estado.get("ativa", "a")
    pendente = estado.get("pendente")

    dados = {
        "ssid": cfg["ssid"],
        "ativa": ativa,
        "rotulo_ativa": rotulo(cfg, ativa),
        "alterada_em": estado.get("alterada_em"),
        "pendente": pendente,
        "proxima": outro(pendente["para"] if pendente else ativa),
        "senha_ativa": senha(cfg, ativa) if args.revelar else None,
    }
    texto = [
        f"Rede: {cfg['ssid']}",
        f"Senha ativa: slot {ativa.upper()} ({rotulo(cfg, ativa)})",
        f"Desde: {estado.get('alterada_em') or 'nunca registrado'}",
    ]
    if args.revelar:
        texto.append(f"Senha: {senha(cfg, ativa)}")
    if pendente:
        texto.append(
            f"ATENCAO: existe troca pendente para o slot {pendente['para'].upper()} "
            f"({rotulo(cfg, pendente['para'])}), iniciada em {pendente['quando']}."
        )
        texto.append("Rode `confirmar` se ja aplicou no painel, ou `cancelar` se desistiu.")
    else:
        texto.append(
            f"Proxima troca vai para o slot {outro(ativa).upper()} ({rotulo(cfg, outro(ativa))})."
        )
    responder(dados, texto, args.json)


def cmd_trocar(args) -> None:
    cfg = carregar_config()
    estado = carregar_estado()
    pendente = estado.get("pendente")

    if pendente and not args.reiniciar:
        destino = pendente["para"]
        texto = [
            f"Ja havia uma troca pendente para o slot {destino.upper()} "
            f"({rotulo(cfg, destino)}), aberta em {pendente['quando']}.",
            "Repetindo os passos (nada foi alterado no estado):",
            *passos(cfg, destino),
        ]
    else:
        destino = args.para or outro(estado.get("ativa", "a"))
        if destino not in SLOTS:
            erro(f"slot invalido: {destino}. Use 'a' ou 'b'.", 6)
        if destino == estado.get("ativa"):
            erro(f"o slot {destino.upper()} ja e o ativo — nao ha o que trocar.", 6)
        pendente = {"para": destino, "de": estado.get("ativa", "a"), "quando": agora()}
        estado["pendente"] = pendente
        salvar_estado(estado)
        texto = [
            f"Trocar a senha da rede '{cfg['ssid']}' para o slot {destino.upper()} "
            f"({rotulo(cfg, destino)}):",
            "",
            *passos(cfg, destino),
        ]

    dados = {
        "ok": True,
        "destino": destino,
        "rotulo_destino": rotulo(cfg, destino),
        "senha_destino": senha(cfg, destino),
        "wifi_uri": wifi_uri(cfg, destino),
        "passos": passos(cfg, destino),
        "pendente": pendente,
    }
    texto += ["", f"QR code (string padrao Wi-Fi): {wifi_uri(cfg, destino)}"]
    responder(dados, texto, args.json)


def cmd_confirmar(args) -> None:
    cfg = carregar_config()
    estado = carregar_estado()
    pendente = estado.get("pendente")

    if not pendente and not args.para:
        erro("nao ha troca pendente. Rode `trocar` primeiro (ou use --para a|b).", 7)

    destino = args.para or pendente["para"]
    if destino not in SLOTS:
        erro(f"slot invalido: {destino}. Use 'a' ou 'b'.", 6)

    anterior = estado.get("ativa", "a")
    estado["ativa"] = destino
    estado["alterada_em"] = agora()
    estado["pendente"] = None
    estado.setdefault("historico", []).append(
        {"quando": agora(), "evento": "troca", "de": anterior, "para": destino}
    )
    salvar_estado(estado)

    texto = [
        f"Registrado: a rede '{cfg['ssid']}' esta agora com o slot {destino.upper()} "
        f"({rotulo(cfg, destino)}).",
        f"Na proxima vez que rodar `trocar`, volta para o slot {outro(destino).upper()} "
        f"({rotulo(cfg, outro(destino))}).",
    ]
    responder(
        {"ok": True, "ativa": destino, "anterior": anterior, "alterada_em": estado["alterada_em"]},
        texto,
        args.json,
    )


def cmd_cancelar(args) -> None:
    estado = carregar_estado()
    if not estado.get("pendente"):
        responder({"ok": True, "cancelado": False}, ["Nao havia troca pendente."], args.json)
        return
    pendente = estado["pendente"]
    estado["pendente"] = None
    estado.setdefault("historico", []).append(
        {"quando": agora(), "evento": "cancelada", "para": pendente["para"]}
    )
    salvar_estado(estado)
    texto = [
        f"Troca pendente para o slot {pendente['para'].upper()} cancelada. "
        f"O estado continua no slot {estado.get('ativa', 'a').upper()}."
    ]
    responder({"ok": True, "cancelado": True, "ativa": estado.get("ativa")}, texto, args.json)


def cmd_mostrar(args) -> None:
    cfg = carregar_config()
    estado = carregar_estado()
    slot = args.slot or estado.get("ativa", "a")
    if slot not in SLOTS:
        erro(f"slot invalido: {slot}. Use 'a' ou 'b'.", 6)
    texto = [
        f"Slot {slot.upper()} ({rotulo(cfg, slot)}) da rede '{cfg['ssid']}': {senha(cfg, slot)}",
        f"QR code (string padrao Wi-Fi): {wifi_uri(cfg, slot)}",
    ]
    responder(
        {"slot": slot, "rotulo": rotulo(cfg, slot), "senha": senha(cfg, slot),
         "wifi_uri": wifi_uri(cfg, slot)},
        texto,
        args.json,
    )


def cmd_historico(args) -> None:
    estado = carregar_estado()
    itens = estado.get("historico", [])[-args.n:]
    if not itens:
        responder({"historico": []}, ["Sem historico ainda."], args.json)
        return
    def linha(i: dict) -> str:
        base = f"{i['quando']} — {i['evento']}"
        if i.get("de") and i.get("para"):
            return f"{base}: {i['de'].upper()} -> {i['para'].upper()}"
        if i.get("para"):
            return f"{base}: slot {i['para'].upper()}"
        return base

    texto = [linha(i) for i in itens]
    responder({"historico": itens}, texto, args.json)


def cmd_doctor(args) -> None:
    problemas: list[str] = []
    caminho = config_path()
    if not caminho.exists():
        problemas.append(f"config nao existe em {caminho} — rode `init`.")
    else:
        modo = stat.S_IMODE(caminho.stat().st_mode)
        if modo & 0o077:
            problemas.append(
                f"config com permissao {oct(modo)} — outros usuarios conseguem ler as senhas. "
                f"Corrija com: chmod 600 {caminho}"
            )
    for pai in [base_dir(), *base_dir().parents]:
        if (pai / ".git").exists():
            problemas.append(
                f"o diretorio de dados esta dentro do repositorio git {pai} — "
                "as senhas podem acabar commitadas. Mova para fora ou ignore no .gitignore."
            )
            break
    texto = problemas or ["Tudo certo: config presente, permissao restrita, fora de repositorio git."]
    responder({"ok": not problemas, "problemas": problemas}, texto, args.json)


# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Alterna a senha do Wi-Fi entre duas senhas fixas.")
    p.add_argument("--json", action="store_true", help="saida em JSON")
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init", help="cria a config com as duas senhas")
    i.add_argument("--ssid", required=True)
    i.add_argument("--painel-url", default=None, help="ex: http://192.168.0.1")
    i.add_argument("--modelo", default=None, help="ex: TP-Link Archer C6")
    i.add_argument("--caminho-menu", default=None, help="caminho do menu no painel")
    i.add_argument("--senha-a", default=None, help="omita para digitar sem eco no terminal")
    i.add_argument("--senha-b", default=None)
    i.add_argument("--rotulo-a", default="senha principal")
    i.add_argument("--rotulo-b", default="senha alternativa")
    i.add_argument("--ativa", choices=SLOTS, default="a", help="qual senha esta valendo hoje")
    i.add_argument("--force", action="store_true")
    i.set_defaults(func=cmd_init)

    g = sub.add_parser("config", help="ajusta campos da config sem mexer no estado")
    g.add_argument("--ssid", default=None)
    g.add_argument("--painel-url", default=None)
    g.add_argument("--modelo", default=None)
    g.add_argument("--caminho-menu", default=None)
    g.add_argument("--rotulo-a", default=None)
    g.add_argument("--rotulo-b", default=None)
    g.add_argument("--senha-a", default=None, help="troca a senha do slot A")
    g.add_argument("--senha-b", default=None, help="troca a senha do slot B")
    g.set_defaults(func=cmd_config)

    s = sub.add_parser("status", help="mostra qual senha esta ativa")
    s.add_argument("--revelar", action="store_true", help="mostra a senha em texto")
    s.set_defaults(func=cmd_status)

    t = sub.add_parser("trocar", help="abre uma troca para a outra senha")
    t.add_argument("--para", choices=SLOTS, default=None)
    t.add_argument("--reiniciar", action="store_true", help="descarta a pendencia anterior")
    t.set_defaults(func=cmd_trocar)

    c = sub.add_parser("confirmar", help="registra que a troca foi aplicada no roteador")
    c.add_argument("--para", choices=SLOTS, default=None)
    c.set_defaults(func=cmd_confirmar)

    x = sub.add_parser("cancelar", help="descarta a troca pendente")
    x.set_defaults(func=cmd_cancelar)

    m = sub.add_parser("mostrar", help="mostra a senha de um slot")
    m.add_argument("--slot", choices=SLOTS, default=None)
    m.set_defaults(func=cmd_mostrar)

    h = sub.add_parser("historico", help="ultimas trocas registradas")
    h.add_argument("-n", type=int, default=10)
    h.set_defaults(func=cmd_historico)

    d = sub.add_parser("doctor", help="checa config, permissoes e riscos")
    d.set_defaults(func=cmd_doctor)

    return p


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
