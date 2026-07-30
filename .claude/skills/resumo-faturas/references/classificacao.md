# Classificação PF/PJ e categorias

## Índice

- [O princípio](#o-princípio)
- [Categorias PJ — construtora](#categorias-pj--construtora)
- [Categorias PF — pessoal](#categorias-pf--pessoal)
- [Casos clássicos e como decidir](#casos-clássicos-e-como-decidir)
- [Alocação por obra](#alocação-por-obra)
- [Como escrever uma regra nova](#como-escrever-uma-regra-nova)
- [O que não é decisão desta skill](#o-que-não-é-decisão-desta-skill)

## O princípio

A pergunta que classifica não é "onde foi comprado", é **"a quem serve o
gasto"**. Cimento comprado no fim de semana continua sendo da obra; almoço em
churrascaria no cartão da empresa continua sendo pessoal, a não ser que fosse
almoço com cliente ou refeição da equipe.

Por isso a decisão tem três camadas com pesos diferentes:

1. **Cartão** — sinal mais forte, porque foi uma decisão deliberada de quem
   abriu o cartão. Mas não é definitivo: todo mundo passa o cartão errado às vezes.
2. **Estabelecimento** — sinal bom quando o ramo é inequívoco (fornecedor de
   vergalhão não vende para pessoa física fazendo compras de casa). Fraco quando
   o ramo atende os dois lados (supermercado, posto, restaurante).
3. **Contexto** — valor, frequência, obra mencionada na descrição, o que o
   usuário respondeu em meses anteriores.

Quando 1 e 2 discordam **e nenhum é inequívoco, não escolha** — marque confiança
baixa e leve para o usuário. O custo de perguntar é um segundo; o custo de errar
uma nota de R$ 8.000 é retrabalho na contabilidade.

## Categorias PJ — construtora

| Categoria | O que entra |
|---|---|
| Material de construção | Cimento, aço, areia, brita, tijolo, argamassa, hidráulica, elétrica, acabamento |
| Ferramentas e EPI | Furadeira, serra, andaime pequeno, capacete, bota, luva, óculos |
| Locação de equipamentos | Betoneira, andaime, escoramento, bomba, container, gerador, banheiro químico |
| Serviços de terceiros | Empreiteiro, projetista, topógrafo, sondagem, laudo, caçamba/entulho |
| Combustível e pedágio | Abastecimento de veículo e máquina, tag de pedágio, estacionamento em obra |
| Veículos e máquinas | Manutenção, peça, pneu, revisão, seguro de frota |
| Taxas, licenças e cartório | Prefeitura, ISS, alvará, CREA/CAU, ART/RRT, cartório, bombeiros, concessionárias |
| Software técnico | AutoCAD/Autodesk, Revit, Eberick/AltoQi, Sienge, SketchUp, armazenamento de projeto |
| Escritório e administrativo | Papelaria, impressão de projeto, internet e telefone do escritório, contabilidade |
| Alimentação de equipe | Marmita/refeição de obra, água, café, lanche de equipe em jornada |
| Marketing e vendas | Placa de obra, anúncio, stand, corretagem, fotos e vídeo de empreendimento |
| Viagens a serviço | Deslocamento para obra fora da cidade, hospedagem de equipe |
| Financeiro do cartão | Anuidade, juros, IOF, multa, seguro do cartão |

## Categorias PF — pessoal

Supermercado · Alimentação e delivery · Saúde e farmácia · Educação · Casa e
utilidades · Vestuário · Transporte pessoal · Assinaturas e lazer · Viagens
pessoais · Presentes e doações · Pets · Outros pessoais

Não invente subcategoria nova a cada mês — categoria que aparece uma vez só não
serve para comparar meses. Se algo não couber, "Outros pessoais" com uma
observação é melhor que uma categoria de um item.

## Casos clássicos e como decidir

**Material de construção no cartão pessoal.** PJ, quase sempre. É o caso que mais
justifica a regra sobrepor o cartão. A exceção real é reforma da casa do próprio
dono — se o volume for relevante e recorrente, pergunte uma vez e crie a regra
com o centro de custo certo (ex.: uma obra "RESIDENCIA-SOCIO" só para isolar).

**Supermercado.** Padrão PF. Vira PJ quando é compra de rancho/água/café para a
obra — o sinal costuma ser valor fora do padrão, atacadista, ou compra no mesmo
dia de outros gastos de obra. Na dúvida, pergunte: é o caso mais frequente de
erro nos dois sentidos.

**Combustível.** Depende do veículo, não do posto. Se a empresa tem frota e o
cartão é PJ, PJ. Se o mesmo carro serve para os dois usos, proponha ao usuário um
critério simples e estável (ex.: "tudo do cartão PJ é PJ, abastecimento no fim de
semana é PF") em vez de decidir caso a caso todo mês.

**Restaurante e delivery.** Padrão PF. Vira PJ em refeição de equipe em jornada,
almoço com cliente ou fornecedor, e alimentação em viagem a serviço. Valor por
pessoa e horário ajudam: R$ 480 em marmitaria às 11h em dia útil não é jantar de
família.

**Ferramenta pequena.** PJ. Mesmo comprada em marketplace e mesmo barata — é
insumo de trabalho.

**Celular, notebook, tablet.** Pergunte. É o tipo de compra em que a resposta
muda por item e o valor é alto o bastante para importar.

**Anuidade, juros e IOF.** Seguem o dono do cartão, não o estabelecimento. Já é
tratado automaticamente pelo `classificar.py`.

**Assinatura de software.** Técnico (AutoCAD, Sienge, Revit) é PJ. Entretenimento
(streaming, música, jogo) é PF. Genérico (Google, Apple, Microsoft, armazenamento)
depende do uso — pergunte uma vez e a regra resolve para sempre.

**Estorno.** Herda a classificação da compra original. Se a compra era PJ da Obra
Alfa, o estorno é PJ da Obra Alfa — senão o total da obra fica inflado.

## Alocação por obra

Só faz sentido para PJ. Três formas, da mais confiável para a menos:

1. **Cartão dedicado** — `centro_custo_padrao` no config. Se um adicional está
   com o encarregado de uma obra, tudo dele cai lá.
2. **Apelido na descrição** — quando o fornecedor põe a referência da obra na
   descrição do lançamento. É o que a lista `apelidos` de cada obra captura.
3. **Fornecedor exclusivo** — locadora que só atende uma obra no período. Vale
   virar regra com `centro_custo`, mas revise quando a obra encerrar.

Não force alocação sem sinal. `(não alocado)` honesto é melhor que rateio
inventado — despesa administrativa e compra de estoque geral realmente não
pertencem a uma obra só. Se o volume não alocado ficar grande demais para
gestão, o caminho é sugerir ao usuário um centro de custo "ADM" e/ou um critério
de rateio explícito, não chutar.

## Como escrever uma regra nova

Depois que o usuário resolve uma dúvida, grave no `config.yaml`:

```yaml
  - match: "obramax|balaroti"      # regex, sem acento, minúsculas
    categoria: "Material de construção"
    titularidade: PJ
    forca: forte                   # forte vence o cartão; fraca só desempata
```

Três cuidados que evitam estrago:

- **Use `forte` só quando o ramo é inequívoco.** `forte` sobrepõe o cartão em
  todos os meses futuros, inclusive nos casos que você não previu.
- **Ancore o suficiente.** `"max"` casa com "Obramax"; `"pao"` casa com
  "Pizza Paozinho". Prefira o nome inteiro da bandeira.
- **Uma regra por decisão do usuário**, com o texto que ele confirmou. Regra
  genérica demais volta como erro dois meses depois, quando ninguém lembra por
  que ela existe.

## O que não é decisão desta skill

Classificar como PJ **não** torna a despesa dedutível, não gera crédito de
imposto e não substitui documento fiscal — nota fiscal em nome do CNPJ é outra
conversa, e é ela que a contabilidade precisa. O que sai daqui é informação
gerencial: onde o dinheiro foi, de quem é o gasto e em qual obra caiu.

Se aparecer volume relevante de despesa pessoal no cartão PJ (ou o contrário),
aponte uma vez, com o número, e siga. É informação útil para a conversa com o
contador — não é motivo para travar o fechamento nem para repetir o aviso a cada
seção do relatório.
