---
name: wifi-toggle-senha
description: Alterna a senha do Wi-Fi da rede local entre duas senhas fixas (A e B), guardando qual esta ativa para que a proxima execucao volte exatamente para a anterior. Use sempre que o usuario pedir para trocar, mudar, alternar, rotacionar ou voltar a senha do Wi-Fi/roteador, pedir a "senha de visita" ou a "senha de casa", perguntar qual senha do Wi-Fi esta valendo agora, ou quiser trocar a senha temporariamente e depois desfazer — mesmo que ele nao cite a skill pelo nome e mesmo que fale so em "senha da rede", "senha do roteador" ou "wifi dos convidados".
---

# Alternar a senha do Wi-Fi entre duas senhas fixas

O usuario tem duas senhas de Wi-Fi definidas — por exemplo a de casa (A) e a de
visita (B). Cada execucao alterna para a outra, e a execucao seguinte volta para
a anterior. Nao ha geracao aleatoria: as duas senhas sao sempre as mesmas, o que
importa e saber qual esta valendo.

A troca em si e **manual, feita pelo usuario no painel do roteador**. Esta skill
nao acessa a rede nem o roteador — ela guarda o estado, entrega a senha certa e
o passo a passo, e so registra a troca depois que o usuario confirma que aplicou.
Esse "confirmar depois" e o ponto central: se o estado for atualizado antes da
troca acontecer de verdade, na proxima vez a skill vai indicar a senha errada e
o usuario fica sem saber qual das duas esta na rede.

## Ferramenta

Todo o estado fica em `scripts/wifi_toggle.py`. Chame o script em vez de ler ou
editar os JSONs na mao — ele cuida de permissao 600, gravacao atomica, historico
e das travas contra estado inconsistente.

```bash
python3 <skill>/scripts/wifi_toggle.py <comando> [--json]
```

| Comando | Para que serve |
| --- | --- |
| `init --ssid NOME [--senha-a X --senha-b Y ...]` | cria a config na primeira vez |
| `config [--caminho-menu ... --senha-a ...]` | ajusta a config sem mexer no estado |
| `status [--revelar]` | qual slot esta ativo, desde quando, se ha troca pendente |
| `trocar [--para a\|b]` | abre a troca para o outro slot e imprime a senha + passos |
| `confirmar` | registra que a troca foi aplicada no roteador |
| `cancelar` | descarta a troca pendente (o estado nao muda) |
| `mostrar [--slot a\|b]` | revela a senha de um slot |
| `historico [-n N]` | ultimas trocas registradas |
| `doctor` | checa config, permissoes e risco de vazar senha em git |

Use `--json` quando precisar ler o estado com precisao (por exemplo para decidir
o proximo passo); a saida sem `--json` ja e texto pronto para mostrar ao usuario.

## Fluxo normal ("troca a senha do Wi-Fi")

1. Rode `status --json`. Isso responde tres coisas de uma vez: se a config ja
   existe, qual slot esta ativo e se ficou alguma troca pendente de antes.
2. Se nao existir config, siga "Primeira vez" abaixo.
3. Se houver **troca pendente**, nao abra outra. Pergunte se o usuario chegou a
   aplicar aquela: se sim, `confirmar`; se nao, `cancelar` e siga em frente.
4. Rode `trocar`. Repasse ao usuario, em texto claro: a senha nova, o passo a
   passo do painel e o aviso de que os aparelhos conectados vao cair e precisam
   da senha nova.
5. Espere o usuario dizer que aplicou. So entao rode `confirmar` e diga qual
   senha vale agora e para qual slot a proxima execucao vai voltar.

Se o usuario disser que a troca deu errado ou que desistiu no meio, rode
`cancelar` — assim o estado continua refletindo a senha que esta de fato na rede.

## Primeira vez (sem config)

Pergunte, de forma direta e numa mensagem so: nome da rede (SSID), as duas
senhas, um apelido para cada uma, qual delas esta valendo hoje, e o endereco do
painel do roteador (normalmente http://192.168.0.1 ou http://192.168.1.1) com o
modelo, se ele souber. Depois:

```bash
python3 scripts/wifi_toggle.py init \
  --ssid "CasaWiFi" --painel-url http://192.168.0.1 --modelo "TP-Link Archer C6" \
  --rotulo-a "casa" --rotulo-b "visita" --ativa a
```

Sem `--senha-a`/`--senha-b`, o script pede as senhas sem eco no terminal — melhor
quando ha alguem olhando a tela ou quando o historico do shell fica salvo. Se
voce estiver rodando sem terminal interativo, passe as senhas por argumento e
avise o usuario que elas podem ficar no historico do shell.

O WPA2 exige no minimo 8 caracteres e as duas senhas precisam ser diferentes; o
script recusa nos dois casos.

## Caminho no painel do roteador

Os passos que o script imprime usam o campo `caminho_menu` da config. Se o
usuario informou o modelo e voce nao sabe o caminho de cor, consulte
`references/roteadores.md` — tem os caminhos de menu dos modelos mais comuns no
Brasil (TP-Link, Intelbras, Askey/Vivo, Humax/Claro, ZTE, ASUS, D-Link, Mikrotik)
e o que fazer quando o modelo nao esta na lista. Quando descobrir o caminho
certo, grave com `config --caminho-menu "..."` para as proximas execucoes ja
saírem prontas — `config` mexe so nos campos informados e nao toca no estado nem
nas senhas.

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
  despeje as duas senhas e o historico inteiro sem ele pedir.
- Trocar a senha derruba todos os aparelhos conectados, inclusive coisas chatas
  de reconectar (impressora, camera, TV, aspirador). Vale lembrar antes da troca,
  nao depois.
- Esta skill e para a rede do proprio usuario. Se aparecer pedido para mexer em
  rede de terceiros ou em equipamento ao qual ele nao tem acesso legitimo, nao
  ajude.
