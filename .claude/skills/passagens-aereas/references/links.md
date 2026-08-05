# Links de busca e alerta

Padrões de URL para montar buscas já filtradas. Monte o link em vez de mandar o usuário preencher o formulário na mão — é a diferença entre ele conferir seu resultado em um clique ou desistir.

Códigos são sempre IATA de três letras (GRU, LIS, JFK). Datas em `AAAA-MM-DD`, exceto no Skyscanner.

## Google Flights — busca e alerta de preço

É a ferramenta principal, porque é a única da lista que manda alerta por e-mail.

A forma mais confiável de montar a URL é pela consulta em linguagem natural **em inglês** (o parser aceita outros idiomas de forma inconsistente, mas a página abre traduzida do mesmo jeito):

```
https://www.google.com/travel/flights?hl=pt-BR&curr=BRL&gl=BR&q=Flights%20to%20LIS%20from%20GRU%20on%202026-09-10%20through%202026-09-25
```

Peças que valem acrescentar ao texto do `q=` conforme o caso:

| Intenção | Acrescente |
|---|---|
| Só ida | omita o `through <data>` |
| Voo direto | `nonstop` |
| Classe | `business class` / `premium economy` |
| Mais de um passageiro | `for 2 adults` |
| Bagagem despachada | `with 1 checked bag` |

`hl=pt-BR&curr=BRL&gl=BR` força interface em português, preços em real e ponto de venda Brasil. Sem `gl=BR` o Google às vezes devolve tarifas de outro mercado, que o usuário não consegue comprar.

**Ativar o alerta** (o usuário precisa estar logado numa conta Google):
1. Abrir o link e conferir se rota, datas e passageiros vieram corretos.
2. Ligar a chave **Acompanhar preços** (aparece logo abaixo do formulário de busca).
3. Com janela de datas flexível, ligar também a opção de acompanhar **qualquer data** dessa rota — os avisos passam a cobrir o mês inteiro em vez de só o par de datas escolhido.
4. Os e-mails chegam quando o preço sobe ou cai de forma relevante. Para desligar: google.com/travel/flights → menu → Acompanhamento de preços.

## Skyscanner (BR)

Bom para varrer mês inteiro e para achar low-cost que o Google às vezes não lista.

```
https://www.skyscanner.com.br/transporte/passagens-aereas/gru/lis/260910/260925/?adultsv2=1&cabinclass=economy
```

Atenção ao formato de data: **AAMMDD**, dois dígitos para o ano. Códigos de aeroporto em minúsculas.

Variações úteis:
- Mês inteiro, ida: troque a data por `260900` (dia `00` = mês todo).
- Cidade inteira em vez de um aeroporto: use o código de cidade quando existir (`sao` para São Paulo, `rio`, `lon`, `nyc`, `par`).

## Kayak (BR)

Útil para o gráfico de preço por dia e para filtros finos de duração de conexão.

```
https://www.kayak.com.br/flights/GRU-LIS/2026-09-10/2026-09-25?sort=bestflight_a
```

- Sem bagagem despachada na comparação: acrescente `/0bags` antes da `?`.
- Só voos diretos: `&fs=stops=0`.
- Uma bagagem despachada: `/1bag`.

## Momondo

Mesmo motor do Kayak, resultados às vezes diferentes por incluir agências menores. Vale como terceira opinião, não como fonte única.

```
https://www.momondo.com.br/flight-search/GRU-LIS/2026-09-10/2026-09-25
```

## Sites das companhias

Sempre confira o preço final no site da companhia antes de recomendar a compra numa agência online. A diferença costuma ser pequena e a dor de cabeça com remarcação, cancelamento e reembolso é muito menor quando o bilhete foi emitido direto.

| Companhia | Site |
|---|---|
| LATAM | latamairlines.com |
| GOL | voegol.com.br |
| Azul | voeazul.com.br |
| TAP | flytap.com |
| Air Europa | aireuropa.com |
| Copa | copaair.com |
| Avianca | avianca.com |
| Iberia | iberia.com |

Nas companhias brasileiras vale checar também o preço em milhas (LATAM Pass, Smiles, TudoAzul): em promoção de resgate a mesma poltrona pode sair bem mais barata, e o usuário pode já ter saldo sem lembrar.

## Cuidados ao usar estes links

- Links de agência quebram e mudam de formato com frequência. Se você não conseguiu abrir a página, não afirme que o preço está lá — diga que é um link de busca, não um preço confirmado.
- Preço muda por sessão e por localização. O que você viu não é necessariamente o que o usuário vai ver.
- Não recomende janela anônima como truque de economia: não há evidência consistente de que funcione, e passa a impressão errada de que você tem controle sobre o preço.
