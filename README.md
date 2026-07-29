# claude-arquivos

Repositório de arquivos e experimentos.

## Rotina de compras

Script que pesquisa uma watchlist de produtos no **Mercado Livre**, **Shopee**,
**Shein** e no **Google Shopping**, monta um relatório em Markdown com o melhor
preço de cada loja e destaca o que bateu o preço-alvo ou caiu desde a última
execução. Opcionalmente envia o relatório por e-mail.

### Instalação

```bash
pip install -r requirements.txt
```

### Uso

```bash
# executa a watchlist inteira e imprime/salva o relatório
python -m rotina_compras

# só algumas lojas, com log detalhado
python -m rotina_compras --fontes shopee shein -v

# executa e manda por e-mail
python -m rotina_compras --email
```

O relatório é salvo em `relatorios/AAAA-MM-DD.md` e o histórico de preços em
`dados/historico.jsonl`. Outras opções em `python -m rotina_compras --help`.

### A watchlist

Editar `config/watchlist.yml` — os itens que vêm no arquivo são só um exemplo
para o script rodar de cara. Cada item aceita:

```yaml
itens:
  - nome: Fone Bluetooth TWS       # rótulo no relatório
    termos: fone bluetooth tws     # o que vai na busca (padrão: o nome)
    preco_alvo: 150.00             # abaixo disso, o item sobe pro topo
    fontes: [mercado_livre, shopee, google_shopping]
    max_resultados: 6
```

### Configuração por variável de ambiente

| Variável | Para quê |
| --- | --- |
| `ML_ACCESS_TOKEN` | **Obrigatória para o Mercado Livre.** Token de https://developers.mercadolivre.com.br — a API de busca não aceita mais requisição anônima. |
| `PROVEDOR_BUSCA` | `duckduckgo` (padrão, sem chave) ou `serpapi`. |
| `SERPAPI_KEY` | Necessária com `PROVEDOR_BUSCA=serpapi`. Habilita o Google Shopping de verdade, com preço estruturado. |
| `SMTP_HOST`, `SMTP_PORTA`, `SMTP_USUARIO`, `SMTP_SENHA`, `EMAIL_PARA`, `EMAIL_DE` | Envio de e-mail com `--email`. Porta 465 usa SSL; qualquer outra usa STARTTLS. |

### Rodar todo dia às 8h

Via cron, numa máquina no fuso de Brasília:

```cron
0 8 * * * cd /caminho/para/claude-arquivos && /usr/bin/python3 -m rotina_compras --email >> /tmp/rotina-compras.log 2>&1
```

Há também um workflow do GitHub Actions em
`.github/workflows/rotina-compras.yml`, que roda só sob demanda (aba Actions →
"Run workflow"). Para agendar, descomente o bloco `schedule` — está em
`0 11 * * *`, que é 8h de Brasília em UTC. As credenciais precisam existir como
secrets do repositório.

### Limites conhecidos

- **Mercado Livre** é a única fonte com preço confiável: vem da API oficial.
- **Shopee, Shein e Google Shopping** bloqueiam acesso automatizado às páginas de
  busca, então o script lê os resultados de um buscador. O preço sai do texto
  indexado — pode estar defasado, e alguns resultados vêm sem preço nenhum.
  Confira na loja antes de comprar. Com `SERPAPI_KEY` o Google Shopping devolve
  preço estruturado e fica bem melhor.
- Uma fonte que falha (bloqueio, rate limit, token vencido) vira um aviso dentro
  do relatório; as outras seguem normalmente.

### Testes

```bash
python -m unittest discover -s tests -t .
```
