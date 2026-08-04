---
name: passagens-aereas
description: Pesquisa passagens aéreas como um agente de viagens — compara preços atuais, datas flexíveis, aeroportos próximos e voos diretos vs. com conexão — monta uma tabela comparativa com companhia, datas, horários, bagagem, preço total e link para conferir, e ensina a configurar alerta de preço no Google Flights. Use sempre que o usuário falar em passagem aérea, voo, bilhete, "quanto custa ir para X", "quero viajar para X em tal mês", datas flexíveis, aeroporto alternativo, milhas ou alerta de preço — mesmo que ele não peça explicitamente uma pesquisa, comparação ou planilha.
---

# Passagens aéreas

Comprar passagem barata não é encontrar um voo, é comparar vários. A mesma rota pode variar centenas de reais entre terça e quinta, entre Guarulhos e Viracopos, entre voo direto e uma conexão de três horas. O usuário que pede "quanto custa ir para Lisboa em setembro" quer, no fundo, a resposta de um agente de viagens: aqui estão as opções, esta é a mais barata, esta é a mais confortável, e é isto que muda de uma para a outra.

O trabalho tem três etapas: pesquisar em várias frentes, organizar numa tabela comparável e deixar um alerta de preço rodando. Faça as três — a terceira é a que continua trabalhando depois que a conversa acaba.

## Regra de ouro: nenhum preço sem fonte e sem link

Você não tem acesso ao inventário das companhias. O que você tem é o que a busca na web devolveu, que pode estar desatualizado, ser de outro ponto de venda ou de outra moeda. Preço de passagem muda de hora em hora.

Por isso, todo número que aparecer na sua resposta precisa de duas coisas: **de onde veio** e **um link onde o usuário confirma**. Um preço inventado que parece plausível é muito pior do que "não consegui confirmar" — o usuário monta o orçamento da viagem em cima dele e descobre a diferença no cartão de crédito.

Se as buscas não devolverem valores confiáveis, ou se você não tiver acesso à web nesta sessão, diga isso com todas as letras e entregue o que ainda tem valor: os links de busca já montados com as datas e filtros certos, os aeroportos alternativos que valem checar e a instrução do alerta. Isso é útil. Um número chutado não é.

## Etapa 0 — Entender a viagem antes de pesquisar

Você precisa de cinco informações. Extraia da conversa o que já foi dito e só pergunte o resto:

| Informação | Se faltar |
|---|---|
| Origem | Pergunte — não dá para adivinhar de onde a pessoa sai. |
| Destino | Pergunte. Se for vago ("praia no nordeste"), ofereça 2-3 destinos e siga. |
| Janela de datas | Pergunte. Aceite qualquer granularidade: datas exatas, "primeira quinzena de março", "algum feriado do segundo semestre". |
| Duração | Deduza das datas se forem fixas; se a janela for aberta, pergunte junto com o resto. |
| Passageiros e classe | Assuma **1 adulto, econômica** e avise que assumiu. Corrigir depois é barato. |

Junte tudo numa única pergunta curta em vez de interrogar em série. Se a pessoa já disse "quero ir de São Paulo para Buenos Aires em julho, uns 5 dias", você tem o suficiente — pesquise.

Vale perguntar também, **só se o usuário abrir espaço**: bagagem despachada é necessária? Tem preferência por voo direto? Tem milhas ou programa de fidelidade? Essas três respostas mudam qual opção é a melhor, mas não impedem a pesquisa de começar.

## Etapa 1 — Pesquisar em várias frentes

Dispare as buscas em paralelo, não em série. São quatro frentes, e cada uma costuma revelar uma economia diferente:

1. **Rota base** — a rota e as datas exatas que o usuário pediu. É a referência contra a qual todo o resto é comparado.
2. **Datas flexíveis** — ±3 dias em torno de cada ponta, e o mês inteiro quando a janela for aberta. Terça, quarta e sábado costumam ser mais baratos que sexta e domingo; alta temporada e véspera de feriado costumam ser piores.
3. **Aeroportos alternativos** — nas duas pontas. Consulte `references/aeroportos.md` para os aeroportos que servem a mesma cidade ou região. Sempre que sugerir um alternativo, diga o custo real de usá-lo: quantos km do centro, quanto custa e quanto demora o traslado. Economizar R$ 200 na passagem e gastar R$ 180 no transfer não é economia.
4. **Companhias e conexões** — quem voa a rota, incluindo low-cost que não aparecem em todo buscador, e se uma conexão longa derruba muito o preço.

Para montar as URLs de busca, use `references/links.md` — tem os padrões de Google Flights, Skyscanner, Kayak e sites das companhias, com os parâmetros de moeda e país já ajustados para o Brasil.

Quando usar busca na web, procure fontes com data visível e prefira as mais recentes. Anote de onde veio cada preço; você vai precisar disso na tabela.

## Etapa 2 — Montar a tabela comparativa

Este é o entregável principal. O formato é uma tabela em markdown na própria conversa — o usuário consegue ler no celular, que é onde ele normalmente está quando pergunta isso.

Use esta estrutura:

```markdown
## Voos GRU → LIS · 10 a 25 de setembro · 1 adulto, econômica

| # | Companhia | Ida | Volta | Duração / paradas | Bagagem | Preço total | Conferir |
|---|---|---|---|---|---|---|---|
| 1 | TAP | 10/09 22:05 | 25/09 11:30 | 10h20 direto | 1 despachada 23kg incluída | R$ 4.180 | [ver](link) |
| 2 | Air Europa | 11/09 18:40 | 24/09 13:15 | 15h50 · 1 parada (MAD 3h) | só de mão 10kg | R$ 3.290 | [ver](link) |

**Mais barata:** opção 2 — R$ 890 a menos, mas com 5h30 a mais de viagem e sem bagagem despachada (a TAP cobra ~€60 por trecho para adicionar).
**Melhor custo-benefício:** opção 1 — direto, noturno e com bagagem inclusa.

### Sair em outras datas
| Data de ida | Preço a partir de | Diferença |
|---|---|---|
| 08/09 (ter) | R$ 3.740 | −R$ 440 |
| 12/09 (sex) | R$ 4.620 | +R$ 440 |

*Preços consultados em [data], via [fonte]. Confirme no link antes de comprar.*
```

Três coisas fazem essa tabela funcionar:

- **Preço total, não preço de vitrine.** Some ida e volta, taxas e a bagagem que o usuário disse precisar. Uma passagem de R$ 2.900 sem bagagem despachada é mais cara que uma de R$ 3.200 com bagagem, e a tabela precisa deixar isso óbvio. `references/bagagem.md` tem as pegadinhas mais comuns por companhia.
- **A coluna de bagagem escrita por extenso.** "1 despachada 23kg incluída" e "só de mão 10kg" comparam; "sim" e "não" não comparam.
- **Uma recomendação explícita.** Não devolva só a tabela. Diga qual você escolheria e por quê, em duas linhas. É isso que separa um agente de viagens de um buscador.

Se o usuário pedir a planilha em arquivo — ou se as opções passarem de umas oito linhas e ficar desconfortável ler na conversa — gere um `.xlsx` com `scripts/planilha_voos.py` (ele explica o formato de entrada no cabeçalho). Não gere arquivo por padrão: na maior parte das vezes a tabela na conversa já resolve, e um download a mais só atrapalha.

## Etapa 3 — Deixar um alerta de preço rodando

A pesquisa é uma fotografia; o alerta é o vídeo. Como o usuário quase nunca compra no mesmo dia em que pesquisa, termine sempre montando o alerta — é a parte que economiza dinheiro de verdade.

Monte o link do Google Flights já com rota, datas e filtros (formato em `references/links.md`) e entregue o passo a passo curto: abrir o link, conferir se os filtros vieram certos, ativar a chave **Acompanhar preços** e, se a janela de datas for flexível, ligar também o "qualquer data" para receber avisos do mês inteiro. Os alertas chegam por e-mail na conta Google logada.

Se você tiver acesso a um navegador nesta sessão, ofereça-se para abrir e configurar. Se não tiver, o link pronto com os filtros embutidos já poupa o trabalho chato.

## Fechar sempre com o aviso

Encerre toda pesquisa lembrando que o preço final é o da tela de pagamento: taxas, bagagem, escolha de assento e conversão de moeda do cartão entram só no fim, e o valor pode ter mudado entre a sua busca e o clique dele. Uma linha basta — o objetivo é que ninguém compre confiando apenas na sua tabela.
