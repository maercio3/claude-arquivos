# Onde fica a senha do Wi-Fi em cada painel

Caminhos tipicos por fabricante. Firmware muda de versao para versao, entao trate
como ponto de partida, nao como verdade absoluta: se o menu do usuario nao bater,
use a secao "Quando o modelo nao esta na lista" no fim.

O campo que interessa quase sempre se chama *Senha*, *Chave de seguranca*,
*Pre-Shared Key*, *WPA Key* ou *Password*, dentro da configuracao de seguranca da
rede sem fio.

## Enderecos de painel mais comuns

`http://192.168.0.1`, `http://192.168.1.1`, `http://192.168.15.1` (Intelbras),
`http://192.168.25.1` (alguns ZTE/Askey), `http://tplinkwifi.net`,
`http://routerlogin.net` (Netgear), `http://192.168.100.1` (varios modems de
operadora em modo bridge/roteador).

## TP-Link

- Interface classica (azul): `Wireless` > `Wireless Security` > campo
  `Wireless Password` / `Senha sem fio`. Redes 2.4 GHz e 5 GHz tem paginas
  separadas em muitos modelos.
- Interface nova (Archer, tema claro): aba `Basic` > `Wireless`, ou
  `Advanced` > `Wireless` > `Wireless Settings` > `Password`.
- Se `Smart Connect` estiver ligado, 2.4 GHz e 5 GHz compartilham a mesma senha e
  um campo so resolve.

## Intelbras (Twibi, Action, GF/RG)

- Roteadores Action/GF: `Rede sem fio` > `Configuracoes` > `Senha`.
- Twibi (mesh, app ou web): `Wi-Fi` > `Configuracoes do Wi-Fi` > `Senha`. Em mesh,
  a troca propaga para os outros pontos sozinha, mas leva alguns segundos.
- ONTs/modems Intelbras de operadora: `Rede` > `WLAN` > `Seguranca`.

## Vivo (Askey, Sagemcom, Nokia) e Claro/NET (Humax, Technicolor, Arris)

- Painel em `http://192.168.15.1` (Vivo Fibra) ou `http://192.168.0.1` (Claro).
- Caminho tipico: `Wi-Fi` / `Rede sem fio` > `Seguranca` ou `Configuracoes
  avancadas` > campo `Senha` / `Chave WPA`.
- O login do painel costuma estar impresso na etiqueta do aparelho, e nao e o
  mesmo que a senha do Wi-Fi.
- Alguns aparelhos de operadora tambem deixam trocar pelo app (Meu Vivo, Minha
  Claro). Se o painel web estiver bloqueado, o app costuma ser o caminho.

## ZTE e Huawei (ONT de fibra)

- ZTE: `Rede local` / `Network` > `WLAN` > `Seguranca` > `WPA Passphrase`.
- Huawei: `WLAN` > `WLAN Basic Configuration` > `WPA PreSharedKey`.
- Em ONT de operadora, algumas contas de acesso so enxergam parte dos menus; se o
  campo estiver cinza, e preciso entrar com a conta de administrador do aparelho.

## ASUS

`Rede sem fio` / `Wireless` > aba `Geral` > `Chave WPA-PSK`. Escolha a banda em
`Frequency band` (2.4 GHz / 5 GHz) e repita para as duas se elas tiverem SSIDs
separados.

## D-Link

`Configuracoes` / `Setup` > `Wireless` > `Wireless Security` >
`Pre-Shared Key`. Nos modelos com assistente, ha um botao `Manual Wireless
Network Setup` que leva direto ao campo.

## Netgear

`Wireless` (menu BASIC) > `Security Options` > `Password (Network Key)`.

## Mikrotik (RouterOS)

Interface Winbox/WebFig: `Wireless` > aba `Security Profiles` > perfil usado pela
interface > `WPA2 Pre-Shared Key`. Por linha de comando:

```
/interface wireless security-profiles set [find name=default] wpa2-pre-shared-key="NOVA_SENHA"
```

## Ubiquiti UniFi

Nao e no roteador, e no controlador: `Settings` > `WiFi` > selecione a rede >
`Password`. A mudanca propaga para todos os APs adotados.

## Quando o modelo nao esta na lista

1. Descubra o endereco do painel: no Windows, `ipconfig` e o campo "Gateway
   padrao"; no Linux/macOS, `ip route | grep default` ou `netstat -nr | grep
   default`. Esse IP e o endereco do painel.
2. Entre com o usuario e senha do painel (etiqueta do aparelho; padroes comuns
   sao admin/admin, admin/senha da etiqueta).
3. Procure um menu com `Wireless`, `Wi-Fi`, `Rede sem fio` ou `WLAN` e, dentro
   dele, `Seguranca` / `Security`.
4. Confirme que o modo de seguranca esta em WPA2-PSK ou WPA2/WPA3 antes de salvar
   — se cair para WEP ou rede aberta, a rede fica exposta.
5. Se houver SSIDs separados para 2.4 GHz e 5 GHz, troque nos dois; senao metade
   dos aparelhos continua na senha antiga e o usuario acha que a troca falhou.

Depois que descobrir o caminho certo, grave na config para as proximas vezes:

```bash
python3 scripts/wifi_toggle.py config \
  --painel-url http://192.168.15.1 \
  --modelo "Askey RTF3505VW" \
  --caminho-menu "Wi-Fi > Seguranca > Chave WPA"
```

`config` altera so os campos informados: as senhas, o historico e o slot ativo
continuam como estavam. (`init --force` existe, mas reescreve tudo e reseta o
estado — use so para comecar do zero.)
