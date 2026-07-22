---
name: anexar-comprovantes
description: >-
  Anexa automaticamente os comprovantes bancários (Pix/transferência/boleto) aos
  lançamentos correspondentes no software Mais Controle ERP, via automação de
  navegador (Playwright), fazendo login com as credenciais do usuário e pausando
  para o 2FA/CAPTCHA. Use quando o usuário quiser "subir/anexar os comprovantes
  no sistema", "lançar os comprovantes no Mais Controle", "colar os Pix nas
  contas a pagar", "juntar os comprovantes aos pagamentos no ERP" ou algo
  equivalente. Normalmente roda DEPOIS da conferência (skill comparar-pagamentos),
  usando o de-para de qual comprovante pertence a qual lançamento. NÃO use para
  apenas comparar/conferir (isso é a skill comparar-pagamentos), nem para pagar
  contas ou emitir documentos — aqui só se anexa arquivo ao lançamento.
---

# Anexar comprovantes no Mais Controle ERP

Automatiza o trabalho manual de abrir cada lançamento no **Mais Controle ERP** e
anexar o comprovante do banco no campo **Arquivos**. Faz login, **pausa para o
2FA/CAPTCHA**, localiza cada lançamento e sobe o arquivo.

## Antes de tudo: segurança e ambiente

Leia e siga — isto protege o usuário.

- **Credenciais nunca no código nem no Git.** Login e senha vêm das variáveis de
  ambiente `MAISCONTROLE_USER` e `MAISCONTROLE_PASS`, fornecidas **na hora de
  rodar**. Nunca escreva a senha em arquivo, log, commit ou mensagem. O
  `.gitignore` da skill já bloqueia `sessao/`, `.env`, `plano.json` e afins.
- **2FA/CAPTCHA exige a pessoa presente.** O script preenche usuário/senha e
  **para**, esperando o usuário concluir o segundo fator na janela do navegador
  e apertar Enter. Não tente burlar captcha.
- **Prefira rodar na máquina do usuário.** Idealmente esta skill roda no Claude
  Code **local** (desktop/terminal) do usuário, para que o navegador e a senha
  fiquem no computador dele e o 2FA apareça na tela dele. Se estiver num ambiente
  remoto/nuvem sem tela visível, avise que o modo com navegador visível
  (`headless: false`) pode não funcionar e combine como proceder.
- **Confirme a autorização.** Só faça isso a pedido do dono da conta, no sistema
  dele. É automação do próprio trabalho — legítimo — mas não avance sem o ok
  explícito para logar e alterar lançamentos.

## Pré-requisitos

```bash
pip install playwright        # a lib Python
# o navegador Chromium já costuma existir no ambiente; se faltar: playwright install chromium
export MAISCONTROLE_USER="seu_usuario_ou_email"
export MAISCONTROLE_PASS="sua_senha"
```

## De onde vem o "plano"

O `plano.json` diz **qual arquivo anexar em qual lançamento**. Cada item:

```json
[
  {"n_doc": "ref oc 3414", "valor": "R$ 360,00", "favorecido": "K CARDOSO", "arquivo": "comprovantes/k_cardoso.png"}
]
```

- `n_doc` é a melhor chave de busca (o número da OC/documento é único no sistema).
- `arquivo` deve ser um caminho existente para o comprovante.
- O ideal é gerar esse plano a partir da **conferência** (skill
  `comparar-pagamentos`): para cada par **Conferido**, o comprovante casado já
  tem lançamento certo. Reaproveite `n_doc`, `valor` e `favorecido` de lá e
  aponte `arquivo` para o comprovante correspondente. Não inclua no plano os
  itens "Sem comprovante" nem os "Comprovante sem lançamento".

## Fluxo de trabalho

### 1. Primeira vez — calibração da tela (uma vez por sistema)

Os nomes de botões/campos do Mais Controle precisam ser confirmados na tela real
(ficam atrás de login). Faça uma execução guiada com o usuário:

1. Gere o config modelo: `python scripts/anexar.py --init-config --config config.json`
2. Rode em **dry-run** com 1 item de teste:
   `python scripts/anexar.py --plano plano_teste.json --config config.json --dry-run`
3. Quando o navegador abrir, peça ao usuário para logar + 2FA e apertar Enter.
4. Observe (screenshots / a própria janela) como são: o menu **Financeiro →
   Pagamentos/Contas a Pagar**, a **busca** de lançamento, a área **Arquivos** e
   o botão **Salvar**. Ajuste os seletores correspondentes em `config.json`
   (campos marcados como `CONFIRMAR`). Prefira seletores por **texto/rótulo
   visível** (`text=Arquivos`, `button:has-text('Salvar')`) — são mais estáveis.
5. Repita o dry-run até o item de teste anexar corretamente (sem salvar).

Guarde o `config.json` calibrado (ele não tem segredo — só URLs e seletores —
então pode ser commitado se o usuário quiser reusar).

### 2. Execução normal

```bash
python scripts/anexar.py --plano plano.json --config config.json
```

O script: abre o navegador → você loga + 2FA → para cada item, busca o
lançamento pelo `n_doc`, abre, anexa o `arquivo` no campo Arquivos e salva.
Ele escreve `resultado_anexos.json` com OK/FALHA e o motivo de cada um.

Use `--dry-run` para ensaiar sem salvar. A sessão fica em `sessao/` (fora do
Git) para não refazer login a cada rodada; apague a pasta para "deslogar".

### 3. Feche o ciclo

Relate ao usuário: quantos anexados, quais falharam e por quê (ex.: lançamento
não encontrado na busca, botão Salvar não localizado). Para os que falharam,
ofereça reexecutar só aqueles ou anexar manualmente. Se muitos falharem no mesmo
ponto, provavelmente um seletor mudou — volte ao passo de calibração.

## Se algo não bater

- **"campo de usuário não encontrado":** a tela de login mudou; logue
  manualmente na janela e ajuste `campo_usuario`/`campo_senha` no config.
- **"lançamento não localizado":** a busca por `n_doc` não achou; teste buscar
  por valor ou favorecido, ou confirme o seletor `campo_busca`/`abrir_lancamento`.
- **"campo de anexo não encontrado":** talvez seja preciso abrir uma aba
  "Arquivos/Anexos" antes; ajuste `aba_arquivos` e `input_arquivo`.
- **Ambiente sem tela (headless):** com 2FA não dá para automatizar às cegas;
  rode na máquina do usuário com navegador visível.

## Limites honestos

Automação de navegador é sensível a mudanças de layout do sistema. Este script é
resiliente (tenta vários seletores e registra falhas claras), mas pode precisar
de reajuste quando o Mais Controle atualizar a interface. Não prometa
infalibilidade; prometa um processo rápido de recalibrar quando necessário.
