#!/usr/bin/env python3
"""Alterna a senha do Wi-Fi entre duas senhas fixas (A e B), em uma ou varias redes.

Cada rede cadastrada tem seu proprio par de senhas e seu proprio estado, entao
trocar a senha de casa nao mexe na do escritorio.

O script nao acessa o roteador: ele guarda qual das duas senhas esta valendo,
mostra a proxima e so registra a troca depois que voce confirma que aplicou no
painel. Assim o estado nunca fica mentindo sobre a rede real.

Uso tipico:
    python3 wifi_toggle.py init --rede casa --ssid CasaWiFi
    python3 wifi_toggle.py redes
    python3 wifi_toggle.py trocar --rede casa
    python3 wifi_toggle.py confirmar --rede casa
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import stat
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

SLOTS = ("a", "b")
VERSAO = 2
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


def apelido_de(texto: str) -> str:
    """Transforma um SSID em um apelido curto e digitavel (CasaWiFi -> casawifi)."""
    limpo = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    limpo = re.sub(r"[^A-Za-z0-9]+", "-", limpo).strip("-").lower()
    return limpo or "rede"


# --------------------------------------------------------------------------
# Config, estado e migracao
# --------------------------------------------------------------------------

def _migrar_v1(cfg: dict, estado: dict) -> tuple[dict, dict]:
    """Converte o formato antigo (uma rede so, campos na raiz) para o de varias."""
    chave = apelido_de(cfg.get("ssid", "rede"))
    nova_cfg = {
        "versao": VERSAO,
        "rede_padrao": chave,
        "redes": {
            chave: {
                "ssid": cfg.get("ssid"),
                "painel_url": cfg.get("painel_url"),
                "modelo_roteador": cfg.get("modelo_roteador"),
                "caminho_menu": cfg.get("caminho_menu"),
                "senhas": cfg.get("senhas", {}),
                "criada_em": cfg.get("criada_em") or agora(),
            }
        },
    }
    novo_estado = {
        "versao": VERSAO,
        "redes": {
            chave: {
                "ativa": estado.get("ativa", "a"),
                "alterada_em": estado.get("alterada_em"),
                "pendente": estado.get("pendente"),
                "historico": estado.get("historico", []),
            }
        },
    }
    return nova_cfg, novo_estado


def carregar_tudo(exigir_config: bool = True) -> tuple[dict, dict]:
    caminho = config_path()
    if not caminho.exists():
        if exigir_config:
            erro(f"config nao encontrada em {caminho}. Rode `init` primeiro.", 2)
        return {"versao": VERSAO, "rede_padrao": None, "redes": {}}, {"versao": VERSAO, "redes": {}}

    cfg = _ler_json(caminho)
    estado = _ler_json(state_path()) if state_path().exists() else {}

    if "redes" not in cfg:  # formato antigo
        cfg, estado = _migrar_v1(cfg, estado)
        _escrever_json_seguro(caminho, cfg)
        _escrever_json_seguro(state_path(), estado)

    estado.setdefault("versao", VERSAO)
    estado.setdefault("redes", {})
    return cfg, estado


def salvar_config(cfg: dict) -> None:
    _escrever_json_seguro(config_path(), cfg)


def salvar_estado(estado: dict) -> None:
    for st in estado.get("redes", {}).values():
        st["historico"] = st.get("historico", [])[-HISTORICO_MAX:]
    _escrever_json_seguro(state_path(), estado)


def resolver_rede(cfg: dict, pedido: str | None) -> str:
    """Aceita o apelido ou o proprio SSID; sem pedido, usa a padrao ou a unica."""
    redes = cfg.get("redes", {})
    if not redes:
        erro("nenhuma rede cadastrada. Rode `init` primeiro.", 2)

    if pedido:
        alvo = pedido.strip().lower()
        for chave in redes:
            if chave.lower() == alvo:
                return chave
        por_ssid = [k for k, r in redes.items() if (r.get("ssid") or "").lower() == alvo]
        if len(por_ssid) == 1:
            return por_ssid[0]
        if len(por_ssid) > 1:
            erro(f"mais de uma rede usa o SSID '{pedido}': {', '.join(por_ssid)}. "
                 "Use o apelido.", 8)
        erro(f"rede '{pedido}' nao encontrada. Cadastradas: {', '.join(redes)}.", 8)

    if len(redes) == 1:
        return next(iter(redes))
    padrao = cfg.get("rede_padrao")
    if padrao in redes:
        return padrao
    erro(f"ha {len(redes)} redes cadastradas e nenhuma padrao definida. "
         f"Use --rede com uma destas: {', '.join(redes)}.", 8)


def estado_da_rede(estado: dict, chave: str) -> dict:
    st = estado.setdefault("redes", {}).setdefault(
        chave, {"ativa": "a", "alterada_em": None, "pendente": None, "historico": []}
    )
    st.setdefault("historico", [])
    return st


def rede_cfg(cfg: dict, chave: str) -> dict:
    return cfg["redes"][chave]


def rotulo(rede: dict, slot: str) -> str:
    return rede["senhas"][slot].get("rotulo") or f"senha {slot.upper()}"


def senha(rede: dict, slot: str) -> str:
    return rede["senhas"][slot]["senha"]


def outro(slot: str) -> str:
    return "b" if slot == "a" else "a"


def wifi_uri(rede: dict, slot: str) -> str:
    """String padrao de QR code de Wi-Fi (WPA)."""
    def esc(v: str) -> str:
        for ch in ("\\", ";", ",", ":", '"'):
            v = v.replace(ch, "\\" + ch)
        return v
    return f"WIFI:T:WPA;S:{esc(rede['ssid'])};P:{esc(senha(rede, slot))};;"


def validar_par(senha_a: str, senha_b: str) -> None:
    if senha_a == senha_b:
        erro("as duas senhas sao iguais — nao haveria troca nenhuma.", 5)
    for nome, valor in (("A", senha_a), ("B", senha_b)):
        if len(valor) < 8:
            erro(f"a senha {nome} tem menos de 8 caracteres e o WPA2 nao aceita.", 5)


# --------------------------------------------------------------------------
# Saida
# --------------------------------------------------------------------------

def responder(dados: dict, texto: list[str], como_json: bool) -> None:
    if como_json:
        print(json.dumps(dados, ensure_ascii=False, indent=2))
    else:
        print("\n".join(texto))


def passos(rede: dict, slot_destino: str) -> list[str]:
    """Passo a passo para aplicar a senha no painel do roteador."""
    modelo = rede.get("modelo_roteador") or "seu roteador"
    url = rede.get("painel_url") or "o endereco do painel (geralmente http://192.168.0.1)"
    caminho_menu = rede.get("caminho_menu") or "Wireless / Wi-Fi > Seguranca (WPA2/WPA3)"
    return [
        f"1. Abra {url} no navegador e entre no painel do {modelo}.",
        f"2. Va em: {caminho_menu}.",
        f"3. Troque a senha da rede '{rede['ssid']}' para: {senha(rede, slot_destino)}",
        "4. Salve e espere o roteador aplicar (alguns reiniciam o radio; a rede cai por alguns segundos).",
        "5. Reconecte um aparelho para confirmar que a senha nova funciona.",
        "6. Volte aqui e confirme a troca para eu registrar o estado.",
    ]


def cabecalho(cfg: dict, chave: str) -> str:
    rede = rede_cfg(cfg, chave)
    return f"Rede: {rede['ssid']} (apelido: {chave})"


# --------------------------------------------------------------------------
# Comandos
# --------------------------------------------------------------------------

def cmd_init(args) -> None:
    cfg, estado = carregar_tudo(exigir_config=False)
    chave = (args.rede or apelido_de(args.ssid)).strip().lower()
    if chave in cfg.get("redes", {}) and not args.force:
        erro(f"a rede '{chave}' ja esta cadastrada. Use --force para recriar, "
             "`config` para so ajustar campos, ou --rede com outro apelido.", 3)

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
    validar_par(senha_a, senha_b)

    cfg.setdefault("versao", VERSAO)
    cfg.setdefault("redes", {})
    cfg["redes"][chave] = {
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
    if args.padrao or not cfg.get("rede_padrao") or len(cfg["redes"]) == 1:
        cfg["rede_padrao"] = chave
    salvar_config(cfg)

    estado.setdefault("redes", {})[chave] = {
        "ativa": args.ativa,
        "alterada_em": agora(),
        "pendente": None,
        "historico": [{"quando": agora(), "evento": "init", "para": args.ativa}],
    }
    salvar_estado(estado)

    rede = rede_cfg(cfg, chave)
    texto = [
        f"Rede '{args.ssid}' cadastrada com o apelido '{chave}' em {config_path()} (permissao 600).",
        f"Slot ativo agora: {args.ativa.upper()} ({rotulo(rede, args.ativa)})",
    ]
    if cfg["rede_padrao"] == chave and len(cfg["redes"]) > 1:
        texto.append(f"Esta rede virou a padrao (usada quando voce nao passar --rede).")
    elif len(cfg["redes"]) > 1:
        texto.append(f"Rede padrao continua sendo '{cfg['rede_padrao']}'. "
                     f"Para trocar esta aqui, use --rede {chave}.")
    texto.append("Rode `trocar` quando quiser alternar para a outra senha.")
    responder(
        {"ok": True, "rede": chave, "ssid": args.ssid, "ativa": args.ativa,
         "rede_padrao": cfg["rede_padrao"], "config": str(config_path())},
        texto, args.json,
    )


def cmd_redes(args) -> None:
    cfg, estado = carregar_tudo()
    itens = []
    texto = []
    for chave, rede in cfg["redes"].items():
        st = estado_da_rede(estado, chave)
        ativa = st.get("ativa", "a")
        padrao = chave == cfg.get("rede_padrao")
        itens.append({
            "rede": chave,
            "ssid": rede.get("ssid"),
            "padrao": padrao,
            "ativa": ativa,
            "rotulo_ativa": rotulo(rede, ativa),
            "alterada_em": st.get("alterada_em"),
            "pendente": st.get("pendente"),
        })
        linha = (f"{'*' if padrao else ' '} {chave} — {rede.get('ssid')} | "
                 f"slot {ativa.upper()} ({rotulo(rede, ativa)})")
        if st.get("pendente"):
            linha += f" | TROCA PENDENTE para {st['pendente']['para'].upper()}"
        texto.append(linha)
    if texto:
        texto.append("")
        texto.append("(* = rede padrao, usada quando voce nao passa --rede)")
    else:
        texto = ["Nenhuma rede cadastrada. Rode `init`."]
    responder({"redes": itens, "rede_padrao": cfg.get("rede_padrao")}, texto, args.json)


def cmd_padrao(args) -> None:
    cfg, _ = carregar_tudo()
    chave = resolver_rede(cfg, args.rede)
    cfg["rede_padrao"] = chave
    salvar_config(cfg)
    texto = [f"Rede padrao agora e '{chave}' ({rede_cfg(cfg, chave)['ssid']})."]
    responder({"ok": True, "rede_padrao": chave}, texto, args.json)


def cmd_remover(args) -> None:
    cfg, estado = carregar_tudo()
    chave = resolver_rede(cfg, args.rede)
    if not args.confirmar:
        erro(f"remover '{chave}' apaga as duas senhas e o historico dela. "
             "Repita com --confirmar se e isso mesmo.", 9)
    ssid = rede_cfg(cfg, chave).get("ssid")
    del cfg["redes"][chave]
    estado.get("redes", {}).pop(chave, None)
    if cfg.get("rede_padrao") not in cfg["redes"]:
        cfg["rede_padrao"] = next(iter(cfg["redes"]), None)
    salvar_config(cfg)
    salvar_estado(estado)
    texto = [f"Rede '{chave}' ({ssid}) removida."]
    if cfg.get("rede_padrao"):
        texto.append(f"Rede padrao agora e '{cfg['rede_padrao']}'.")
    responder({"ok": True, "removida": chave, "rede_padrao": cfg.get("rede_padrao")},
              texto, args.json)


def cmd_config(args) -> None:
    """Ajusta campos de uma rede sem exigir redigitar as senhas."""
    cfg, _ = carregar_tudo()
    chave = resolver_rede(cfg, args.rede)
    rede = rede_cfg(cfg, chave)

    campos = {
        "ssid": args.ssid,
        "painel_url": args.painel_url,
        "modelo_roteador": args.modelo,
        "caminho_menu": args.caminho_menu,
    }
    alterados = {k: v for k, v in campos.items() if v is not None}
    rede.update(alterados)
    for slot, novo in (("a", args.rotulo_a), ("b", args.rotulo_b)):
        if novo is not None:
            rede["senhas"][slot]["rotulo"] = novo
            alterados[f"rotulo_{slot}"] = novo
    for slot, nova in (("a", args.senha_a), ("b", args.senha_b)):
        if nova is not None:
            rede["senhas"][slot]["senha"] = nova
            alterados[f"senha_{slot}"] = "(atualizada)"
    if args.senha_a is not None or args.senha_b is not None:
        validar_par(senha(rede, "a"), senha(rede, "b"))

    if not alterados:
        responder({"ok": True, "rede": chave, "alterados": {}},
                  [f"Nada para alterar em '{chave}'."], args.json)
        return

    rede["atualizada_em"] = agora()
    salvar_config(cfg)
    texto = [f"Config da rede '{chave}' atualizada:"] + [f"  {k} = {v}" for k, v in alterados.items()]
    responder({"ok": True, "rede": chave, "alterados": alterados}, texto, args.json)


def cmd_status(args) -> None:
    cfg, estado = carregar_tudo()
    chave = resolver_rede(cfg, args.rede)
    rede = rede_cfg(cfg, chave)
    st = estado_da_rede(estado, chave)
    ativa = st.get("ativa", "a")
    pendente = st.get("pendente")

    dados = {
        "rede": chave,
        "ssid": rede["ssid"],
        "ativa": ativa,
        "rotulo_ativa": rotulo(rede, ativa),
        "alterada_em": st.get("alterada_em"),
        "pendente": pendente,
        "proxima": outro(pendente["para"] if pendente else ativa),
        "senha_ativa": senha(rede, ativa) if args.revelar else None,
        "total_redes": len(cfg["redes"]),
        "rede_padrao": cfg.get("rede_padrao"),
    }
    texto = [
        cabecalho(cfg, chave),
        f"Senha ativa: slot {ativa.upper()} ({rotulo(rede, ativa)})",
        f"Desde: {st.get('alterada_em') or 'nunca registrado'}",
    ]
    if args.revelar:
        texto.append(f"Senha: {senha(rede, ativa)}")
    if pendente:
        texto.append(
            f"ATENCAO: existe troca pendente para o slot {pendente['para'].upper()} "
            f"({rotulo(rede, pendente['para'])}), iniciada em {pendente['quando']}."
        )
        texto.append("Rode `confirmar` se ja aplicou no painel, ou `cancelar` se desistiu.")
    else:
        texto.append(
            f"Proxima troca vai para o slot {outro(ativa).upper()} ({rotulo(rede, outro(ativa))})."
        )
    if len(cfg["redes"]) > 1 and not args.rede:
        texto.append(f"(usando a rede padrao '{chave}'; ha {len(cfg['redes'])} cadastradas — "
                     "veja `redes`)")
    responder(dados, texto, args.json)


def cmd_trocar(args) -> None:
    cfg, estado = carregar_tudo()
    chave = resolver_rede(cfg, args.rede)
    rede = rede_cfg(cfg, chave)
    st = estado_da_rede(estado, chave)
    pendente = st.get("pendente")

    if pendente and not args.reiniciar:
        destino = pendente["para"]
        texto = [
            cabecalho(cfg, chave),
            f"Ja havia uma troca pendente para o slot {destino.upper()} "
            f"({rotulo(rede, destino)}), aberta em {pendente['quando']}.",
            "Repetindo os passos (nada foi alterado no estado):",
            *passos(rede, destino),
        ]
    else:
        destino = args.para or outro(st.get("ativa", "a"))
        if destino == st.get("ativa"):
            erro(f"o slot {destino.upper()} ja e o ativo na rede '{chave}' — "
                 "nao ha o que trocar.", 6)
        pendente = {"para": destino, "de": st.get("ativa", "a"), "quando": agora()}
        st["pendente"] = pendente
        salvar_estado(estado)
        texto = [
            cabecalho(cfg, chave),
            f"Trocar a senha para o slot {destino.upper()} ({rotulo(rede, destino)}):",
            "",
            *passos(rede, destino),
        ]

    dados = {
        "ok": True,
        "rede": chave,
        "ssid": rede["ssid"],
        "destino": destino,
        "rotulo_destino": rotulo(rede, destino),
        "senha_destino": senha(rede, destino),
        "wifi_uri": wifi_uri(rede, destino),
        "passos": passos(rede, destino),
        "pendente": pendente,
    }
    texto += ["", f"QR code (string padrao Wi-Fi): {wifi_uri(rede, destino)}"]
    responder(dados, texto, args.json)


def cmd_confirmar(args) -> None:
    cfg, estado = carregar_tudo()
    chave = resolver_rede(cfg, args.rede)
    rede = rede_cfg(cfg, chave)
    st = estado_da_rede(estado, chave)
    pendente = st.get("pendente")

    if not pendente and not args.para:
        erro(f"nao ha troca pendente na rede '{chave}'. "
             "Rode `trocar` primeiro (ou use --para a|b).", 7)

    destino = args.para or pendente["para"]
    anterior = st.get("ativa", "a")
    st["ativa"] = destino
    st["alterada_em"] = agora()
    st["pendente"] = None
    st["historico"].append({"quando": agora(), "evento": "troca", "de": anterior, "para": destino})
    salvar_estado(estado)

    texto = [
        f"Registrado: a rede '{rede['ssid']}' esta agora com o slot {destino.upper()} "
        f"({rotulo(rede, destino)}).",
        f"Na proxima vez que rodar `trocar` nela, volta para o slot {outro(destino).upper()} "
        f"({rotulo(rede, outro(destino))}).",
    ]
    responder({"ok": True, "rede": chave, "ativa": destino, "anterior": anterior,
               "alterada_em": st["alterada_em"]}, texto, args.json)


def cmd_cancelar(args) -> None:
    cfg, estado = carregar_tudo()
    chave = resolver_rede(cfg, args.rede)
    st = estado_da_rede(estado, chave)
    if not st.get("pendente"):
        responder({"ok": True, "rede": chave, "cancelado": False},
                  [f"Nao havia troca pendente na rede '{chave}'."], args.json)
        return
    pendente = st["pendente"]
    st["pendente"] = None
    st["historico"].append({"quando": agora(), "evento": "cancelada", "para": pendente["para"]})
    salvar_estado(estado)
    texto = [
        f"Troca pendente para o slot {pendente['para'].upper()} cancelada na rede '{chave}'. "
        f"O estado continua no slot {st.get('ativa', 'a').upper()}."
    ]
    responder({"ok": True, "rede": chave, "cancelado": True, "ativa": st.get("ativa")},
              texto, args.json)


def cmd_mostrar(args) -> None:
    cfg, estado = carregar_tudo()
    chave = resolver_rede(cfg, args.rede)
    rede = rede_cfg(cfg, chave)
    st = estado_da_rede(estado, chave)
    slot = args.slot or st.get("ativa", "a")
    texto = [
        f"Slot {slot.upper()} ({rotulo(rede, slot)}) da rede '{rede['ssid']}': {senha(rede, slot)}",
        f"QR code (string padrao Wi-Fi): {wifi_uri(rede, slot)}",
    ]
    responder({"rede": chave, "slot": slot, "rotulo": rotulo(rede, slot),
               "senha": senha(rede, slot), "wifi_uri": wifi_uri(rede, slot)}, texto, args.json)


def cmd_historico(args) -> None:
    cfg, estado = carregar_tudo()
    chave = resolver_rede(cfg, args.rede)
    itens = estado_da_rede(estado, chave).get("historico", [])[-args.n:]
    if not itens:
        responder({"rede": chave, "historico": []},
                  [f"Sem historico ainda na rede '{chave}'."], args.json)
        return

    def linha(i: dict) -> str:
        base = f"{i['quando']} — {i['evento']}"
        if i.get("de") and i.get("para"):
            return f"{base}: {i['de'].upper()} -> {i['para'].upper()}"
        if i.get("para"):
            return f"{base}: slot {i['para'].upper()}"
        return base

    responder({"rede": chave, "historico": itens},
              [f"Historico da rede '{chave}':"] + [linha(i) for i in itens], args.json)


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
        cfg, estado = carregar_tudo()
        if len(cfg.get("redes", {})) > 1 and cfg.get("rede_padrao") not in cfg["redes"]:
            problemas.append("ha varias redes e nenhuma padrao definida — "
                             "use `padrao --rede NOME` ou passe --rede sempre.")
        for chave, st in estado.get("redes", {}).items():
            if st.get("pendente"):
                problemas.append(
                    f"a rede '{chave}' tem uma troca pendente desde {st['pendente']['quando']} — "
                    "confirme ou cancele para o estado voltar a refletir a realidade."
                )
        orfas = set(estado.get("redes", {})) - set(cfg.get("redes", {}))
        if orfas:
            problemas.append(f"estado com redes que nao existem mais na config: {', '.join(orfas)}.")

    for pai in [base_dir(), *base_dir().parents]:
        if (pai / ".git").exists():
            problemas.append(
                f"o diretorio de dados esta dentro do repositorio git {pai} — "
                "as senhas podem acabar commitadas. Mova para fora ou ignore no .gitignore."
            )
            break

    texto = problemas or ["Tudo certo: config presente, permissao restrita, "
                          "sem pendencias e fora de repositorio git."]
    responder({"ok": not problemas, "problemas": problemas}, texto, args.json)


# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Alterna a senha do Wi-Fi entre duas senhas fixas.")
    p.add_argument("--json", action="store_true", help="saida em JSON")
    sub = p.add_subparsers(dest="cmd", required=True)

    # parent com --rede para os comandos que operam em uma rede
    uma_rede = argparse.ArgumentParser(add_help=False)
    uma_rede.add_argument("--rede", default=None,
                          help="apelido ou SSID da rede (padrao: a rede padrao)")

    i = sub.add_parser("init", help="cadastra uma rede com as duas senhas")
    i.add_argument("--rede", default=None, help="apelido curto (padrao: derivado do SSID)")
    i.add_argument("--ssid", required=True)
    i.add_argument("--painel-url", default=None, help="ex: http://192.168.0.1")
    i.add_argument("--modelo", default=None, help="ex: TP-Link Archer C6")
    i.add_argument("--caminho-menu", default=None, help="caminho do menu no painel")
    i.add_argument("--senha-a", default=None, help="omita para digitar sem eco no terminal")
    i.add_argument("--senha-b", default=None)
    i.add_argument("--rotulo-a", default="senha principal")
    i.add_argument("--rotulo-b", default="senha alternativa")
    i.add_argument("--ativa", choices=SLOTS, default="a", help="qual senha esta valendo hoje")
    i.add_argument("--padrao", action="store_true", help="torna esta a rede padrao")
    i.add_argument("--force", action="store_true", help="recria uma rede ja cadastrada")
    i.set_defaults(func=cmd_init)

    r = sub.add_parser("redes", help="lista as redes cadastradas e o slot ativo de cada uma")
    r.set_defaults(func=cmd_redes)

    d0 = sub.add_parser("padrao", parents=[uma_rede], help="define a rede padrao")
    d0.set_defaults(func=cmd_padrao)

    rm = sub.add_parser("remover", parents=[uma_rede], help="apaga uma rede cadastrada")
    rm.add_argument("--confirmar", action="store_true")
    rm.set_defaults(func=cmd_remover)

    g = sub.add_parser("config", parents=[uma_rede],
                       help="ajusta campos da rede sem mexer no estado")
    g.add_argument("--ssid", default=None)
    g.add_argument("--painel-url", default=None)
    g.add_argument("--modelo", default=None)
    g.add_argument("--caminho-menu", default=None)
    g.add_argument("--rotulo-a", default=None)
    g.add_argument("--rotulo-b", default=None)
    g.add_argument("--senha-a", default=None, help="troca a senha do slot A")
    g.add_argument("--senha-b", default=None, help="troca a senha do slot B")
    g.set_defaults(func=cmd_config)

    s = sub.add_parser("status", parents=[uma_rede], help="mostra qual senha esta ativa")
    s.add_argument("--revelar", action="store_true", help="mostra a senha em texto")
    s.set_defaults(func=cmd_status)

    t = sub.add_parser("trocar", parents=[uma_rede], help="abre uma troca para a outra senha")
    t.add_argument("--para", choices=SLOTS, default=None)
    t.add_argument("--reiniciar", action="store_true", help="descarta a pendencia anterior")
    t.set_defaults(func=cmd_trocar)

    c = sub.add_parser("confirmar", parents=[uma_rede],
                       help="registra que a troca foi aplicada no roteador")
    c.add_argument("--para", choices=SLOTS, default=None)
    c.set_defaults(func=cmd_confirmar)

    x = sub.add_parser("cancelar", parents=[uma_rede], help="descarta a troca pendente")
    x.set_defaults(func=cmd_cancelar)

    m = sub.add_parser("mostrar", parents=[uma_rede], help="mostra a senha de um slot")
    m.add_argument("--slot", choices=SLOTS, default=None)
    m.set_defaults(func=cmd_mostrar)

    h = sub.add_parser("historico", parents=[uma_rede], help="ultimas trocas registradas")
    h.add_argument("-n", type=int, default=10)
    h.set_defaults(func=cmd_historico)

    doc = sub.add_parser("doctor", help="checa config, permissoes e riscos")
    doc.set_defaults(func=cmd_doctor)

    return p


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
