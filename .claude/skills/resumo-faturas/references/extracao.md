# Extração de faturas — o que costuma dar errado

Leia isto antes de extrair a fatura de um banco pela primeira vez. Quase todo
erro de fechamento cai em um dos casos abaixo.

## Índice

- [O erro mais comum: somar o que não é compra](#o-erro-mais-comum-somar-o-que-não-é-compra)
- [Parcelas](#parcelas)
- [Compra internacional e IOF](#compra-internacional-e-iof)
- [Estornos e créditos](#estornos-e-créditos)
- [Cartões adicionais](#cartões-adicionais)
- [Particularidades por banco](#particularidades-por-banco)
- [PDF com senha](#pdf-com-senha)
- [Limpeza da descrição](#limpeza-da-descrição)
- [Quando o total não fecha](#quando-o-total-não-fecha)

## O erro mais comum: somar o que não é compra

A fatura tem várias linhas com cara de lançamento que **não** são despesa do
mês. Se entrarem como `compra`, o total estoura:

- `SALDO ANTERIOR` / `SALDO FATURA ANTERIOR`
- `PAGAMENTO EFETUADO` / `PGTO DEBITO AUTOMATICO` / `PAGAMENTO RECEBIDO OBRIGADO`
  → é o pagamento da fatura passada. Registre com `tipo=pagamento` (o
  `relatorio.py` já exclui esse tipo dos totais gerenciais) ou simplesmente não
  extraia.
- `TOTAL DESTA FATURA`, `LIMITE DISPONÍVEL`, `VALOR MÍNIMO`, `PRÓXIMAS FATURAS`
  → são resumo, nunca lançamento.
- Blocos de "lançamentos futuros"/"próximas faturas" → informativo, não entra.

O `conferir.py` acusa esses textos automaticamente, mas ele só pega o que
conhece — na dúvida, compare com o "total desta fatura" impresso.

## Parcelas

Na fatura, cada linha de parcelada mostra o **valor da parcela**, não o valor da
compra. Mantenha assim: `valor` = parcela do mês, `parcela` = `3/10`. A projeção
de meses futuros multiplica a parcela pelas que faltam; se você lançar o valor
cheio da compra, a projeção fica 10x errada.

Descrições típicas: `PARC 03/10`, `03/10`, `3 DE 10`, `PARCELA 3/10`.

Compra parcelada é **dívida com prazo**, não recorrência — não confunda com
assinatura.

## Compra internacional e IOF

Uma compra em dólar aparece em duas ou três linhas: a compra convertida, o IOF e
às vezes o "ajuste de conversão".

- `valor` = valor final em BRL (o que o banco cobra).
- `moeda_origem` = `USD`/`EUR`, `valor_origem` = valor na moeda original.
- IOF vira linha própria com `tipo=iof`. Não embuta o IOF no valor da compra:
  separado, ele aparece no relatório como custo do cartão, que é o que interessa.

Se o banco lançar a compra em dólar e a conversão em outra linha, some as duas em
um único lançamento em BRL — senão o fechamento não bate.

## Estornos e créditos

Estorno, cashback, desconto e "crédito de ajuste" entram com **valor negativo** e
`tipo=estorno`. Assim a soma da coluna `valor` é exatamente o total da fatura, que
é a propriedade da qual o `conferir.py` depende.

Cuidado com o sinal: alguns extratos marcam crédito com `C` no fim da linha ou com
o sinal depois do número (`89,90-`). O `parse_valor` em `comum.py` entende os dois.

## Cartões adicionais

Faturas com adicionais agrupam por portador ("Lançamentos de MARCIO", "Lançamentos
de FULANO"). O cabeçalho do grupo vale para todas as linhas seguintes até o próximo
cabeçalho — preencha `portador` e `cartao` (final do adicional, que costuma ser
diferente do titular).

Isso importa de verdade: em construtora é comum o adicional estar com um
encarregado e representar quase só gasto de obra. Se o config tiver
`centro_custo_padrao` nesse cartão, a alocação por obra sai de graça.

## Particularidades por banco

| Banco | O que observar |
|---|---|
| **Itaú** | Separa "lançamentos nacionais" e "internacionais" em blocos distintos, cada um com subtotal — não conte o subtotal. Data em `dd/mm`, ano só no cabeçalho. |
| **Nubank** | PDF limpo, uma linha por lançamento. O CSV do app é melhor ainda: baixe por `Fatura → Exportar`. Parcelas vêm como `Parcela 3/10` no fim da descrição. |
| **Bradesco** | Colunas grudam na extração de texto; extraia por posição/tabela em vez de dividir por espaço. Traz "saldo anterior" no topo. |
| **Banco do Brasil** | Usa `D`/`C` no fim da linha para débito/crédito. Ourocard traz seção de dólar com cotação do dia. |
| **Santander** | Repete o cabeçalho a cada página — filtre linhas repetidas de cabeçalho. |
| **Inter / C6 / Original** | Fatura costuma vir só por link no e-mail; peça o PDF ou o CSV ao usuário. C6 exporta OFX, que é a melhor origem. |
| **Sicoob / Sicredi** | Layout regional variável; confira o fechamento com atenção extra na primeira vez. |

Se o banco não estiver na lista, o roteiro é o mesmo: extraia, confira contra o
total impresso e, quando descobrir uma peculiaridade nova, **acrescente uma linha
nesta tabela** — é isso que faz o mês seguinte ser mais rápido.

## PDF com senha

Faturas costumam vir protegidas com CPF (só números, às vezes só os 5 primeiros
dígitos), CNPJ ou data de nascimento. Peça a senha ao usuário em vez de tentar
adivinhar. Para abrir, use a skill `pdf`.

## Limpeza da descrição

O campo `estabelecimento` é o que as regras de classificação enxergam, então vale
limpar bem:

| Descrição na fatura | `estabelecimento` |
|---|---|
| `PAGSEG *LEROY MERLIN SP` | `Leroy Merlin` |
| `MP *OBRAMAX0123 SAO PAULO` | `Obramax` |
| `IFD*IFOOD CLUB` | `iFood` |
| `EC *GERDAU ACOS LONGOS` | `Gerdau` |

Regras práticas: tire prefixos de adquirente (`PAGSEG`, `MP`, `EC`, `PAG*`,
`IFD*`, `SUMUP`, `CIELO`), tire cidade e UF do fim, tire sequências numéricas de
loja. Mantenha o texto original em `descricao` — se a limpeza errar, o original
ainda está lá para conferir.

## Quando o total não fecha

Na ordem, é quase sempre:

1. **Faltou lançamento** (diferença negativa): quebra de página do PDF, ou um
   bloco de adicional que não foi extraído. Reconte quantas linhas o PDF tem por
   página e compare.
2. **Sobrou lançamento** (diferença positiva): linha de resumo/saldo contada como
   compra, ou lançamento duplicado pela extração.
3. **Sinal invertido**: estorno lançado positivo. A diferença costuma ser
   exatamente o dobro do valor do estorno — pista boa.
4. **IOF ou encargo fora**: diferença pequena e redonda.

Resolva antes de classificar. Relatório construído sobre extração incompleta é
pior que nenhum relatório, porque parece confiável.
