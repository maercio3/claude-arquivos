"""Entrega do relatório: arquivo e e-mail."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


class EmailNaoConfigurado(RuntimeError):
    pass


def salvar(caminho: str | Path, conteudo: str) -> Path:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


def _config_email() -> dict[str, str]:
    obrigatorias = ("SMTP_HOST", "SMTP_USUARIO", "SMTP_SENHA", "EMAIL_PARA")
    faltando = [c for c in obrigatorias if not os.environ.get(c)]
    if faltando:
        raise EmailNaoConfigurado(
            "variáveis ausentes: " + ", ".join(faltando)
        )
    return {
        "host": os.environ["SMTP_HOST"],
        "porta": os.environ.get("SMTP_PORTA", "587"),
        "usuario": os.environ["SMTP_USUARIO"],
        "senha": os.environ["SMTP_SENHA"],
        "de": os.environ.get("EMAIL_DE") or os.environ["SMTP_USUARIO"],
        "para": os.environ["EMAIL_PARA"],
    }


def enviar_email(assunto: str, corpo_html: str, corpo_texto: str) -> str:
    """Envia o relatório por SMTP. Devolve o destinatário."""
    config = _config_email()

    mensagem = EmailMessage()
    mensagem["Subject"] = assunto
    mensagem["From"] = config["de"]
    mensagem["To"] = config["para"]
    mensagem.set_content(corpo_texto)
    mensagem.add_alternative(corpo_html, subtype="html")

    porta = int(config["porta"])
    if porta == 465:
        with smtplib.SMTP_SSL(config["host"], porta, timeout=30) as servidor:
            servidor.login(config["usuario"], config["senha"])
            servidor.send_message(mensagem)
    else:
        with smtplib.SMTP(config["host"], porta, timeout=30) as servidor:
            servidor.starttls()
            servidor.login(config["usuario"], config["senha"])
            servidor.send_message(mensagem)
    return config["para"]
