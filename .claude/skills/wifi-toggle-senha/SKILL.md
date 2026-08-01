---
name: wifi-toggle-senha
description: Alterna a senha do Wi-Fi entre duas senhas fixas (A e B), em uma ou varias redes cadastradas (casa, escritorio, sitio...), guardando qual esta ativa em cada uma para que a proxima execucao volte exatamente para a anterior. Use sempre que o usuario pedir para trocar, mudar, alternar, rotacionar ou voltar a senha do Wi-Fi/roteador, pedir a "senha de visita" ou a "senha de casa", perguntar qual senha do Wi-Fi esta valendo agora, quiser cadastrar mais uma rede, ou quiser trocar a senha temporariamente e depois desfazer — mesmo que ele nao cite a skill pelo nome e mesmo que fale so em "senha da rede", "senha do roteador" ou "wifi dos convidados".
---

# Alternar a senha do Wi-Fi entre duas senhas fixas

Cada rede cadastrada tem duas senhas fixas — por exemplo a de casa (A) e a de
visita (B). Cada execucao alterna para a outra, e a execucao seguinte volta para
a anterior. Nao ha geracao aleatoria: as duas senhas sao sempre as mesmas, o que
importa e saber qual esta valendo.

Da para cadastrar quantas redes quiser (casa, escritorio, sitio). Cada uma tem
seu proprio par de senhas, seu proprio estado e seu proprio historico — trocar a
senha de uma nao mexe nas outras.

A troca em si e **manual, feita pelo usuario no painel do roteador**. Esta skill
nao acessa a rede nem o roteador — ela guarda o estado, entrega a senha certa e
o passo a passo, e so registra a troca depois que o usuario confirma que aplicou.
Esse "confirmar depois" e o ponto central: se o estado for atualizado antes da
troca acontecer de verdade, na proxima vez a skill vai indicar a senha errada e
o usuario fica sem saber qual das duas esta na rede.

## Ferramenta

Todo o estado fica em `scripts/wifi_toggle.py`. Chame o script em vez de ler ou
editar os JSONs na mao — ele cuida de permissao 600, gravacao atomica, historico,
migracao de formato e das travas contra estado inconsistente.

```bash
python3 <skill>/scripts/wifi_toggle.py <comando> [--rede APELIDO] [--json]
```

| Comando | Para que serve |
| --- | --- |
| `init --ssid NOME [--rede APELIDO ...]` | cadastra uma rede (use de novo para acrescentar outra) |
| `redes` | lista as redes, o slot ativo de cada uma e qual e a padrao |
| `padrao --rede X` | define a rede usada quando ninguem passa `--rede` |
| `remover --rede X --confirmar` | apaga uma rede (senhas e historico juntos) |
| `config [--caminho-menu ... --senha-a ...]` | ajusta a config de uma rede sem mexer no estado |
| `status [--revelar]` | qual slot esta ativo, desde quando, se ha troca pendente |
| `trocar [--para a\|b]` | abre a troca para o outro slot e imprime a senha + passos |
| `confirmar` | registra que a troca foi aplicada no roteador |
| `cancelar` | descarta a troca pendente (o estado nao muda) |
| `mostrar [--slot a\|b]` | revela a senha de um slot |
| `historico [-n N]` | ultimas trocas da rede |
| `doctor` | checa config, permissoes, pendencias e risco de vazar senha em git |

`--rede` aceita tanto o apelido (`casa`) quanto o proprio SSID (`CasaWiFi`).
Use `--json` quando precisar ler o estado com precisao para decidir o proximo
passo; a saida sem `--json` ja e texto pronto para mostrar ao usuario.

## Escolher a rede certa

Com **uma rede so** cadastrada, `--rede` e dispensavel: o script usa a unica que
existe. Com **varias**, resolva a ambiguidade antes de agir, porque trocar a
senha da rede errada faz o usuario perder acesso onde nao queria:

1. Rode `redes --json` para ver o que existe.
2. Se o usuario nomeou a rede ("troca a do escritorio"), use esse nome em
   `--rede` — apelido ou SSID, os dois funcionam.
3. Se ele nao nomeou e ha mais de uma, pergunte qual antes de trocar. Nao caia
   na padrao por comodismo: a padrao serve para quando ele claramente fala da
   rede principal ("troca a senha do wifi" morando so em casa), nao para
   adivinhar entre casa e escritorio.

## Fluxo normal ("troca a senha do Wi-Fi")

1. Rode `status --json` (com `--rede` se ja souber qual). Isso responde tudo de
   uma vez: se a config existe, qual slot esta ativo e se ficou alguma troca
   pendente de antes.
2. Se nao existir config nenhuma, siga "Cadastrar uma rede" abaixo.
3. Se houver **troca pendente**, nao abra outra. Pergunte se o usuario chegou a
   aplicar aquela: se sim, `confirmar`; se nao, `cancelar` e siga em frente.
4. Rode `trocar`. Repasse ao usuario, em texto claro: a senha nova, o passo a
   passo do painel e o aviso de que os aparelhos conectados vao cair e precisam
   da senha nova.
5. Espere o usuario dizer que aplicou. So entao rode `confirmar` e diga qual
   senha vale agora e para qual slot a proxima execucao vai voltar.

Se o usuario disser que a troca deu errado ou que desistiu no meio, rode
`cancelar` — assim o estado continua refletindo a senha que esta de fato na rede.

## Cadastrar uma rede

Vale tanto para a primeira vez quanto para acrescentar mais uma depois — e o
mesmo `init`. Pergunte, de forma direta e numa mensagem so: nome da rede (SSID),
um apelido curto, as duas senhas, um apelido para cada senha, qual delas esta
valendo hoje, e o endereco do painel do roteador (normalmente
http://192.168.0.1 ou http://192.168.1.1) com o modelo, se ele souber.

```bash
python3 scripts/wifi_toggle.py init \
  --rede casa --ssid "CasaWiFi" \
  --painel-url http://192.168.0.1 --modelo "TP-Link Archer C6" \
  --rotulo-a "casa" --rotulo-b "visita" --ativa a
```

Sem `--senha-a`/`--senha-b`, o script pede as senhas sem eco no terminal — melhor
quando ha alguem olhando a tela ou quando o historico do shell fica salvo. Se
voce estiver rodando sem terminal interativo, passe as senhas por argumento e
avise o usuario que elas podem ficar no historico do shell.

Sem `--rede`, o apelido sai do SSID (`Escritório Ação` vira `escritorio-acao`).
A primeira rede cadastrada vira a padrao; use `--padrao` para promover outra.
O WPA2 exige no minimo 8 caracteres e as duas senhas da mesma rede precisam ser
diferentes; o script recusa nos dois casos.

## Caminho no painel do roteador

Os passos que o script imprime usam o campo `caminho_menu` da rede. Se o usuario
informou o modelo e voce nao sabe o caminho de cor, consulte
`references/roteadores.md` — tem os caminhos de menu dos modelos mais comuns no
Brasil (TP-Link, Intelbras, Askey/Vivo, Humax/Claro, ZTE, ASUS, D-Link, Mikrotik)
e o que fazer quando o modelo nao esta na lista. Quando descobrir o caminho
certo, grave com `config --rede X --caminho-menu "..."` para as proximas
execucoes ja saírem prontas — `config` mexe so nos campos informados e nao toca
no estado nem nas senhas.

Se o usuario quiser mudar uma das duas senhas fixas, use
`config --senha-a NOVA` (ou `--senha-b`) e lembre que ele precisa aplicar essa
senha nova no roteador se o slot alterado for justamente o que esta ativo.

## Cuidados

- **As senhas ficam em texto em `~/.config/wifi-toggle-senha/config.json`**, com
  permissao 600. Isso protege de outros usuarios da maquina, nao de quem tem
  acesso a sua conta. Diga isso ao usuario na configuracao inicial, sem alarde.
- Nunca copie a config, o state ou as senhas para dentro de um repositorio, nem
  cole senha em commit, PR ou issue. O comando `doctor` avisa se o diretorio de
  dados cair dentro de um repo git.
- Ao mostrar a senha, mostre so a que o usuario precisa naquele momento. Nao
  despeje as senhas de todas as redes nem o historico inteiro sem ele pedir.
- Trocar a senha derruba todos os aparelhos conectados, inclusive coisas chatas
  de reconectar (impressora, camera, TV, aspirador). Vale lembrar antes da troca,
  nao depois.
- Esta skill e para redes do proprio usuario. Se aparecer pedido para mexer em
  rede de terceiros ou em equipamento ao qual ele nao tem acesso legitimo, nao
  ajude.
