---
name: comparar-pagamentos
description: >-
  Concilia (bate) pagamentos de um relatório em PDF de um software de controle
  financeiro contra os comprovantes do banco (Pix, transferência, boleto),
  apontando o que foi pago corretamente, o que está divergente e o que ficou sem
  comprovante. Use SEMPRE que o usuário quiser conferir, cruzar, reconciliar ou
  comparar pagamentos com comprovantes/recibos bancários — por exemplo
  "confere esse relatório de pagamentos com os comprovantes", "quais pagamentos
  não têm comprovante", "bate os comprovantes do Inter com o sistema", "concilia
  as despesas com os Pix do banco" — mesmo que a pessoa não diga a palavra
  "conciliação". Lida com comprovantes em PDF de texto E em imagem/print (PNG,
  JPG, print de tela), inclusive vários comprovantes num PDF único ou soltos.
  Gera planilha Excel detalhada + resumo executivo e, ao final, monta um e-mail
  (rascunho no Gmail) com a planilha e os comprovantes anexados para o usuário
  revisar e enviar. NÃO use para gerar boletos, emitir notas fiscais ou fazer
  lançamentos contábeis — é só conferência.
---

# Comparar pagamentos (software de controle) × comprovantes do banco

## O que esta skill faz

Você tem dois lados que precisam bater:

1. **Software de controle** — um relatório em PDF com a lista de pagamentos
   (valor, favorecido, data, documento, nº da OC/doc interno).
2. **Banco** — os comprovantes das transações efetivadas (Pix, transferência,
   boleto), que podem ser PDFs de texto ou **imagens/prints**.

A conferência responde: **cada pagamento do sistema tem um comprovante que bate?
Os valores conferem? Sobrou comprovante sem lançamento?** A saída é uma planilha
Excel com status por linha + um resumo executivo em texto.

## Fluxo de trabalho

O trabalho tem duas naturezas: **ler/entender os documentos** (precisa da sua
inteligência e visão) e **casar + gerar o relatório** (determinístico, feito por
script). Não misture: extraia primeiro, depois deixe o script conciliar.

### Passo 1 — Identifique os arquivos e quem é quem

Confirme qual arquivo é o **relatório do software** (um PDF, muitos lançamentos)
e quais são os **comprovantes** (um por transação, PDF ou imagem; ou um PDF
único com vários). Se não estiver claro, pergunte. Uma checagem rápida: o
relatório traz totais e uma tabela; o comprovante traz "Pix enviado / R$ X",
"Quem recebeu", "Quem pagou".

### Passo 2 — Extraia os lançamentos do relatório → `pagamentos.json`

Se o PDF tiver texto, rode:

```bash
python scripts/extrair_texto.py <relatorio.pdf>
```

Se `pdfplumber` não estiver instalado: `pip install pdfplumber cffi`. Se o
relatório for imagem/escaneado (sem texto), leia com visão (ferramenta Read).

O texto vem com as colunas **intercaladas** — leia cada bloco de lançamento pelo
sentido, não pela posição. Para cada lançamento monte um objeto e salve a lista
em `pagamentos.json`:

```json
[
  {
    "valor": "R$ 1.500,00",
    "data": "21/07/2026",
    "favorecido": "Emerson Ferreira de Freitas",
    "documento": "02511073374",
    "chave_pix": "",
    "n_doc": "REF OC 3408",
    "forma": "Pix",
    "descricao": "Salário comprador",
    "status": "Em aberto"
  }
]
```

Como separar o campo **Dados** em `documento` vs `chave_pix`, e outros detalhes
de layout, estão em `references/layouts.md` — leia se tiver dúvida.

### Passo 3 — Extraia os comprovantes → `comprovantes.json`

**Comprovante em imagem/print (o caso mais comum): leia diretamente com visão.**
Não tente OCR por script — você enxerga a imagem melhor. Para cada comprovante
monte:

```json
[
  {
    "valor": "R$ 765,00",
    "data": "2026-07-21",
    "horario": "08h44",
    "id_transacao": "E00416968202607211109iN36qBpHlIP",
    "recebedor_nome": "Mario Barbosa Lima",
    "recebedor_documento": "***.290.871-**",
    "recebedor_chave": "+5563981389094",
    "pagador_nome": "ANA K S CARDOSO LTDA",
    "arquivo": "comprovante1.png"
  }
]
```

Regras de ouro na extração do comprovante:
- **Copie o CPF mascarado como está** (`***.290.871-**`). Não invente os dígitos
  ocultos — o script sabe casar máscara com o CPF completo do relatório.
- O documento que importa é o de **quem recebeu**, não o de quem pagou.
- Preencha `arquivo` com o nome do arquivo de origem — é o que liga a linha da
  planilha ao comprovante físico.
- Se um PDF único tiver vários comprovantes, gere um objeto por comprovante.

### Passo 4 — Concilie e gere a saída

```bash
python scripts/comparar.py pagamentos.json comprovantes.json \
    -o conferencia --tol-valor 0.00 --tol-dias 3
```

- `--tol-valor` — folga de valor em reais (0.00 = precisa bater centavo a
  centavo; use, por exemplo, 0.05 para tolerar arredondamento).
- `--tol-dias` — folga de data em dias (pagamento agendado que caiu no dia
  seguinte, etc.).

Ajuste as tolerâncias conforme o usuário pedir. O script produz:
- `conferencia.xlsx` — aba **Conferência** (uma linha por lançamento, colorida
  por status, com filtro) + aba **Resumo** (totais).
- `conferencia.md` — resumo executivo.

### Passo 5 — Entregue e explique

Entregue os dois arquivos e resuma em texto: quantos **conferidos**, quantos
**divergentes** (e por quê), quantos **sem comprovante**, e quantos
**comprovantes sem lançamento**. Destaque os itens que exigem ação humana
(faltando comprovante, valor diferente). Se os totais dos dois lados não
fecharem, diga o valor da diferença.

### Passo 6 — Envie por e-mail (padrão do usuário)

O usuário quer receber a conferência do dia por e-mail, **com a planilha e os
comprovantes anexados**. Faça isso ao final de toda conferência, salvo se ele
disser o contrário.

**Importante — é rascunho, não envio automático.** A ferramenta de Gmail
disponível (`create_draft`) monta o e-mail pronto na caixa "Rascunhos" com os
anexos, mas **não dispara o envio**. Deixe o rascunho pronto e avise o usuário
que é só revisar e clicar Enviar. Não prometa que o e-mail "foi enviado" — ele
foi *preparado*. (Para dados financeiros essa revisão humana costuma ser
desejável.)

Obs.: a descrição do `create_draft` traz um aviso de que "anexo ainda não é
suportado", mas na prática o campo `attachments` funciona (testado e
confirmado) — pode usar sem receio.

Monte a base64 de cada anexo (a ferramenta exige o conteúdo em base64) e crie o
rascunho:

```bash
# gera a base64 de um arquivo para colar no campo "content" do anexo
base64 -w0 conferencia.xlsx
```

Chame `create_draft` com:
- `to`: e-mail(s) de destino. **Padrão: `maercio2@gmail.com`.** Se o usuário
  pedir outro destinatário (contador, sócio, financeiro), use esse.
- `subject`: algo como `Conferência de pagamentos — <data> (X conferidos, Y divergentes, Z sem comprovante)`.
- `body`: o mesmo resumo executivo do `conferencia.md` (conferidos, divergentes
  e o que exige ação). Assim a pessoa lê o essencial sem abrir o anexo.
- `attachments`: uma entrada por arquivo, cada uma com `filename`, `mimeType` e
  `content` (base64):
  - a planilha `conferencia.xlsx`
    (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`)
  - **todos os comprovantes que foram enviados** (as imagens/PDFs originais) —
    é o que dá lastro à conferência. Use o `mimeType` certo (`image/png`,
    `image/jpeg`, `application/pdf`).
  - opcionalmente o relatório do software em PDF.

**Limite de 25MB no total dos anexos.** Se os comprovantes estourarem esse
limite, não trave: anexe a planilha + resumo e, para os comprovantes, suba-os
ao Google Drive e coloque o link no corpo do e-mail (ou pergunte ao usuário se
prefere dividir em mais de um e-mail). Avise o que foi feito.

Se o Gmail não estiver conectado nesta sessão, gere a planilha normalmente,
avise que não foi possível montar o rascunho e ofereça reenviar quando a conta
estiver conectada.

## Como funciona o casamento (para você saber explicar)

O `comparar.py` usa **valor como chave forte** e corrobora com **nome**,
**documento** e **data**:

- **Valor** dentro da tolerância é pré-requisito para ser candidato.
- **Nome** favorecido × recebedor por similaridade (ignora acento, caixa e
  sufixos como "LTDA").
- **Documento**: casa CPF completo (relatório) com CPF **mascarado** do
  comprovante (6 dígitos do meio), CNPJ completo, e telefone (últimos dígitos,
  ignorando +55). Testa `documento` e `chave_pix` dos dois lados.
- **Data** dentro da tolerância dá reforço; fora dela vira divergência.
- Casamento é **1 para 1**: cada comprovante é usado por no máximo um lançamento.

Status possíveis: **Conferido** (bate tudo), **Divergente** (achou par mas algo
difere — valor, data ou nome), **Sem comprovante** (lançamento sem par),
**Comprovante sem lançamento** (comprovante que sobrou).

## Erros comuns a evitar

- Não case por posição no texto do PDF — as colunas vêm intercaladas.
- Não preencha dígitos de CPF que estão mascarados no comprovante.
- Não rode `comparar.py` antes de ter os dois JSONs completos.
- Comprovantes e relatório precisam ser do **mesmo período/lote** para a
  conferência fazer sentido; se perceber que são de lotes diferentes (pagador
  ou valores totalmente distintos), avise o usuário.
