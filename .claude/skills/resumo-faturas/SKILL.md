---
name: resumo-faturas
description: Lê faturas de cartão de crédito (PDF, CSV/OFX do banco, e-mail do Gmail, arquivos do Google Drive ou texto colado), extrai os lançamentos, separa o que é gasto pessoal (PF) do que é da construtora (PJ), aloca os gastos PJ por obra/centro de custo e entrega um resumo em texto, uma planilha .xlsx e um PDF para o contador. Use sempre que o usuário mencionar fatura de cartão, extrato do cartão, gastos do mês, fechamento do mês, "separar o que é da empresa e o que é meu", "classificar as despesas da obra", "mandar pro contador", "quanto gastei nesse cartão", conciliação de despesas, ou anexar/apontar um PDF ou CSV que seja fatura de cartão — mesmo que não peça explicitamente um "resumo".
---

# Resumo de faturas de cartão — pessoal (PF) e construtora (PJ)

## O que essa skill resolve

O usuário mistura, no mesmo bolso, gastos pessoais e gastos de uma construtora.
Todo mês chegam faturas de vários cartões e alguém precisa dizer: **quanto foi da
empresa, quanto foi pessoal, em qual obra caiu cada despesa, e o que já está
comprometido nos próximos meses.** O trabalho manual disso é chato, repetitivo e
propenso a erro — e o erro tem custo real (despesa PJ classificada como PF vira
imposto pago a mais; despesa PF classificada como PJ vira problema com a
contabilidade).

O objetivo aqui não é só "somar gastos". É produzir um fechamento **que fecha**:
os lançamentos extraídos têm que bater com o total impresso na fatura, e cada
lançamento tem que ter um dono (PF ou PJ) defensável.

## Fluxo

Sempre nesta ordem. Os passos 3 e 6 são os que dão confiabilidade ao resultado —
não pule nenhum dos dois.

1. **Reunir as faturas** — ver "Origens" abaixo.
2. **Extrair os lançamentos** para `lancamentos.csv` + `faturas.csv`.
3. **Conferir o fechamento** com `scripts/conferir.py`. Se não fechar, resolva antes de seguir.
4. **Classificar** com `scripts/classificar.py` (cartão → regras → dúvidas).
5. **Perguntar as dúvidas** de uma vez só e gravar as respostas no config.
6. **Gerar os relatórios** com `scripts/relatorio.py` (texto + .xlsx + PDF).

### 0. Config

Todo o conhecimento que se acumula (quais cartões existem, quais obras estão
ativas, qual estabelecimento é PJ) mora em um arquivo YAML — por padrão
`faturas/config.yaml` na raiz do repositório do usuário.

Se ele não existir, copie `assets/config.exemplo.yaml` e preencha com o usuário
antes de continuar. Peça, no mínimo: os últimos 4 dígitos de cada cartão, o
titular de cada um, se cada cartão é por padrão PF ou PJ, e as obras ativas com
seus apelidos. É rápido de perguntar e economiza dezenas de dúvidas depois.

### 1. Origens das faturas

| Origem | Como pegar |
|---|---|
| PDF em pasta local | Leia direto. Se for PDF protegido por senha, peça a senha (costuma ser CPF/CNPJ ou data de nascimento). |
| Google Drive | `mcp__Google_Drive__search_files` por "fatura", nome do banco ou mês; depois `download_file_content`. |
| Gmail | `mcp__Gmail__search_threads` com algo como `fatura cartão has:attachment newer_than:60d`; baixe o anexo. Faturas de Nubank/Inter costumam vir com link em vez de anexo — nesse caso peça o PDF ao usuário. |
| CSV / OFX exportado do app | Melhor origem possível: já vem estruturado, use preferencialmente quando existir. |
| Texto colado | Trate como texto bruto e siga o mesmo processo de extração. |

Quando houver PDF **e** CSV do mesmo cartão/mês, use o CSV para os valores e o
PDF só para o total de fechamento e os encargos.

### 2. Extração

Para ler o PDF, use a skill `pdf`. O que importa é o resultado: dois CSVs em
UTF-8 (escreva com BOM — `utf-8-sig` — para abrir limpo no Excel).

`lancamentos.csv` — uma linha por lançamento:

```
data,descricao,estabelecimento,valor,moeda_origem,valor_origem,cartao,portador,parcela,tipo,titularidade,categoria,centro_custo,confianca,regra,arquivo_origem,obs
```

`faturas.csv` — uma linha por fatura processada:

```
arquivo_origem,banco,cartao,portador,vencimento,periodo_inicio,periodo_fim,total_fatura
```

Regras de preenchimento que evitam a maior parte dos erros:

- `valor` em reais, ponto como decimal, **positivo para despesa e negativo para
  crédito** (estorno, cashback, desconto). Assim a soma da coluna é o total da fatura.
- `tipo` ∈ `compra`, `parcela`, `estorno`, `pagamento`, `encargo`, `anuidade`,
  `iof`, `assinatura`, `saque`, `ajuste`. Deixe `titularidade`, `categoria`,
  `centro_custo`, `confianca` e `regra` **vazios** — quem preenche é o passo 4.
- `parcela` no formato `3/10`. Compra à vista fica vazio.
- `estabelecimento` é a descrição limpa: tire prefixos de adquirente, códigos de
  loja e cidade (`PAGSEG*LEROY MERLIN SP` → `Leroy Merlin`). É esse campo que as
  regras de classificação enxergam, então limpá-lo bem faz as regras pegarem
  no mês seguinte sozinhas.
- Compra internacional: `valor` é o valor final em BRL; guarde `moeda_origem` e
  `valor_origem`. Lance o IOF como linha própria com `tipo=iof`.

Detalhes de armadilhas por banco (o que conta e o que não conta, "pagamento
recebido", saldo anterior, faturas parciais) estão em `references/extracao.md`.
Leia antes da primeira extração de um banco novo.

### 3. Conferir o fechamento — o portão de qualidade

```bash
python3 scripts/conferir.py --lancamentos faturas/2026-07/lancamentos.csv \
                            --faturas faturas/2026-07/faturas.csv
```

O script confere schema, datas, duplicidades suspeitas e — o principal — se a
soma dos lançamentos de cada arquivo bate com o `total_fatura` declarado.

Diferença de centavos é arredondamento e pode seguir. Diferença relevante quase
sempre significa lançamento perdido numa quebra de página do PDF ou uma linha de
"saldo anterior" contada como compra. **Resolva a divergência antes de
classificar** — um resumo bonito construído sobre extração incompleta é pior que
nenhum resumo, porque parece confiável. Se depois de investigar a diferença
continuar, siga em frente, mas registre isso em destaque no topo do relatório.

### 4. Classificar

```bash
python3 scripts/classificar.py --lancamentos faturas/2026-07/lancamentos.csv \
                               --config faturas/config.yaml --inplace
```

A classificação usa três camadas, da mais forte para a mais fraca:

1. **Cartão** — se o cartão é da empresa, o padrão é PJ (e vice-versa). É o sinal
   mais confiável, mas não é absoluto: quase todo mundo já passou o almoço de
   domingo no cartão da empresa.
2. **Regras de estabelecimento** — do config. Elas podem sobrepor o padrão do
   cartão quando o sinal é forte (material de construção no cartão pessoal é PJ;
   escola dos filhos no cartão da empresa é PF).
3. **Obra / centro de custo** — por apelido da obra no config ou por proximidade
   (fornecedor que só atende uma obra). Só preencha `centro_custo` para PJ.

Quando cartão e regra discordam sem que uma delas seja forte, o script marca
`confianca=baixa` em vez de escolher — é exatamente esse o material do passo 5.

A taxonomia de categorias (PF e PJ de construtora) e os critérios de decisão nos
casos clássicos estão em `references/classificacao.md`.

### 5. Perguntar as dúvidas — em um bloco só

Junte tudo que ficou com `confianca=baixa` ou sem `titularidade` e pergunte de
uma vez, agrupando por estabelecimento (não por lançamento): "Leroy Merlin
apareceu 6 vezes, R$ 4.320 no total — PJ da Obra Alfa?" é uma pergunta; seis
perguntas separadas são um interrogatório.

Ordene pelo valor: os 10 maiores decidem a maior parte do total. Se sobrarem
itens pequenos e irrelevantes, proponha uma regra genérica em vez de perguntar
um a um.

**Grave as respostas como regras novas no config.** Esse é o ponto da skill: o
mês que vem tem que dar menos trabalho que este. Acrescente ao `config.yaml`,
mostre o que foi acrescentado, e diga ao usuário que aquilo não será perguntado
de novo.

### 6. Relatórios

```bash
python3 scripts/relatorio.py --lancamentos faturas/2026-07/lancamentos.csv \
                             --faturas faturas/2026-07/faturas.csv \
                             --config faturas/config.yaml \
                             --saida faturas/2026-07/ --formatos md,xlsx,pdf
```

Sai um `resumo.md`, um `resumo.xlsx` (abas Lançamentos, Resumo, Por categoria,
Por obra, Parcelas futuras, Revisar) e um `resumo.pdf`.

Apresente o resumo em texto **na conversa** — é o que o usuário lê primeiro — e
depois entregue os arquivos. Não faça o usuário abrir uma planilha para saber
quanto gastou.

Estrutura do texto, nesta ordem (é a ordem em que as perguntas aparecem na
cabeça de quem paga a fatura):

```markdown
# Fatura(s) de [mês] — total R$ X

**PJ (construtora): R$ X (n%)  ·  PF (pessoal): R$ Y (m%)**
[uma linha sobre o que mudou em relação ao mês anterior, se houver dado]

## Por cartão
## PJ por obra / centro de custo
## Onde foi o dinheiro (categorias, maiores primeiro)
## Maiores lançamentos
## Já comprometido nos próximos meses (parcelas)
## Assinaturas recorrentes
## Pontos de atenção
```

Em "pontos de atenção" entram: divergência de fechamento, cobranças duplicadas,
juros/rotativo, anuidade, assinatura que não aparecia antes, gasto muito acima
do padrão do estabelecimento, e itens que ficaram sem classificação. Seja
específico e traga o valor — "atenção com assinaturas" não ajuda ninguém;
"Adobe R$ 289/mês, 12 meses seguidos = R$ 3.468/ano, ainda usa?" ajuda.

## Comparação entre meses

Se existirem fechamentos anteriores na mesma estrutura de pastas, leia os
`lancamentos.csv` deles e compare: total, split PF/PJ, categoria que mais subiu.
Comparação mês a mês é o que transforma o resumo em informação de gestão. Não
invente comparação se não houver mês anterior disponível — diga que é o primeiro
fechamento.

## Limites que precisam ficar claros

A separação PF/PJ aqui é **gerencial** — serve para controle de custo e para
organizar a conversa com a contabilidade. Ela não decide dedutibilidade fiscal
nem substitui o contador, e classificar uma despesa como PJ não a torna
dedutível. Quando aparecer algo que claramente é assunto do contador (despesa
pessoal em cartão PJ em volume relevante, por exemplo), aponte uma vez, de forma
objetiva, e siga o trabalho.

Os dados de fatura são sensíveis: não jogue número de cartão completo em nenhum
relatório — só os 4 últimos dígitos, que é o que os scripts usam.

## Arquivos desta skill

- `references/extracao.md` — armadilhas de leitura de fatura por banco.
- `references/classificacao.md` — taxonomia PF/PJ e critérios de decisão.
- `scripts/conferir.py` — valida schema e fechamento.
- `scripts/classificar.py` — aplica cartão + regras + obras.
- `scripts/relatorio.py` — gera md, xlsx e pdf.
- `assets/config.exemplo.yaml` — modelo de configuração.
