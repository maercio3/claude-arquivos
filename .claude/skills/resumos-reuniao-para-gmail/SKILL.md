---
name: resumos-reuniao-para-gmail
description: >
  Reúne os resumos das reuniões do Notion (notas de reunião), coloca as tarefas
  e action items em evidência, e monta um rascunho de e-mail pronto no Gmail para
  maercio2@gmail.com. Use SEMPRE que o usuário quiser "enviar / mandar / compilar
  os resumos de reunião", "resumo das reuniões da semana", "action items das
  reuniões por e-mail", "notas de reunião do Notion no Gmail" ou algo parecido —
  mesmo que ele não diga explicitamente "Notion" ou "Gmail". Também vale quando ele
  pedir um digest/compilado de reuniões com as tarefas destacadas.
---

# Resumos de reunião do Notion → rascunho no Gmail

Esta skill lê as notas de reunião do usuário no Notion, resume cada uma e destaca
as **tarefas / action items** ("em evidência"), e monta um **rascunho de e-mail
formatado no Gmail** para o destinatário padrão. Ela não envia sozinha: cria o
rascunho pronto para o usuário revisar e clicar em "Enviar" — assim ele sempre
confere antes de mandar, e evita disparos acidentais.

## Padrões desta skill

- **Destinatário padrão:** `maercio2@gmail.com`. Se o usuário indicar outro e-mail
  na hora, use o que ele pediu.
- **Escopo padrão:** reuniões dos **últimos 7 dias**. O usuário pode ampliar
  ("últimos 30 dias", "todas", "este mês") ou pedir uma reunião específica pelo
  título.
- **Entrega:** sempre **rascunho** no Gmail (a ferramenta disponível não envia
  diretamente). Deixe isso claro ao final.

## Fluxo

### 1. Definir o escopo
Interprete o pedido do usuário para descobrir o período ou a reunião:
- Sem período explícito → últimos 7 dias.
- "últimos 30 dias", "este mês", "esta semana", "ontem" → intervalo de datas.
- Um título específico ("standup", "1:1 com a Ana", "planning") → filtro por título.

### 2. Buscar as reuniões no Notion
Use a ferramenta **`notion-query-meeting-notes`**. Ela já retorna, por padrão, as
notas em que o usuário é participante ou criador — não filtre pelo usuário atual.

- **Por período (caminho recomendado):** o filtro de data relativo dessa
  ferramenta é frágil, então o jeito mais confiável é **buscar sem filtro** (a
  ferramenta já retorna as notas mais recentes primeiro, até 50) e **recortar você
  mesmo** pela propriedade `Criado em` / `created_time`, comparando com a data de
  hoje. Ex.: para "últimos 7 dias", mantenha as reuniões com `created_time` >=
  (hoje − 7 dias).
- **Se preferir filtrar no servidor:** use `created_time` com um intervalo de datas
  exato (o formato relativo costuma dar erro de validação). Exemplo:
  ```json
  {
    "operator": "and",
    "filters": [
      {
        "property": "created_time",
        "filter": {
          "operator": "date_is_within",
          "value": { "type": "exact", "value": { "type": "daterange", "start_date": "2026-07-15", "end_date": "2026-07-22" } }
        }
      }
    ]
  }
  ```
  Se der erro de validação, volte para o caminho recomendado (buscar sem filtro e
  recortar por data).
- **Por título:** filtre `title` com `string_contains` (busca é case-insensitive;
  use uma única palavra-chave se um termo composto não casar).
- Nunca invente reuniões — trabalhe só com o que a ferramenta devolver. Se um item
  tiver título vazio ou "Reunião", ainda assim busque o conteúdo (o `‣` indica que
  há uma página com anotações).

Se **nenhuma** reunião for encontrada, avise o usuário e pergunte se quer ampliar o
período — não crie um rascunho vazio.

### 3. Extrair resumo e tarefas de cada reunião
Para cada reunião retornada, chame **`notion-fetch`** com o ID/URL da página para
ler o conteúdo completo. De cada página, capture:

- **Título, data e participantes** da reunião.
- **Resumo:** um parágrafo curto (2–4 frases). Se a nota já tiver uma seção de
  resumo/summary, use-a; senão, sintetize a partir das anotações. Seja fiel ao
  conteúdo — não acrescente conclusões que não estão na nota.
- **Tarefas / action items** (o mais importante — vão "em evidência"). Procure em
  vários formatos, porque cada nota organiza de um jeito:
  - itens de checklist / to-do (caixas de seleção) na página;
  - seções chamadas "Action items", "Tarefas", "To-dos", "Próximos passos",
    "Next steps", "Encaminhamentos", "Pendências";
  - tarefas relacionadas (relations para um banco de Tarefas), se aparecerem.
  Para cada tarefa, guarde o **texto**, e quando existir: **responsável**
  (@pessoa) e **prazo/data**. Se uma reunião não tiver tarefas, registre isso
  ("Sem tarefas registradas") em vez de omitir a reunião.

Não inclua transcrições longas no e-mail — só o resumo e as tarefas.

### 4. Montar o e-mail
Use o modelo em `assets/email_template.html` como base do `htmlBody`. Estrutura:

1. **Cabeçalho** com o período coberto e a contagem de reuniões.
2. **Bloco "✅ Tarefas em destaque"** logo no topo — a lista consolidada de TODAS as
   tarefas de todas as reuniões, cada uma com responsável e prazo quando houver, e
   entre parênteses de qual reunião veio. Este bloco é o coração do e-mail: deixe-o
   visualmente destacado (fundo diferente, negrito). É isso que "tarefas em
   evidência" significa.
3. **Resumos por reunião**, um bloco por reunião: título, data, participantes,
   resumo e as tarefas daquela reunião.

Também preencha o campo `body` (texto puro) com uma versão equivalente em texto,
para clientes que não renderizam HTML. Mantenha as tarefas destacadas também no
texto puro (ex.: prefixo "➤" e uma seção "TAREFAS EM DESTAQUE" no topo).

**Assunto sugerido:** `Resumos de reunião — <período>` (ex.: "Resumos de reunião —
15 a 22 de julho de 2026"). Se for uma única reunião, use o título dela.

Escreva o e-mail no mesmo idioma das notas (normalmente português).

### 5. Criar o rascunho no Gmail
Chame **`create_draft`** com:
- `to`: `["maercio2@gmail.com"]` (ou o e-mail que o usuário pediu);
- `subject`: o assunto montado;
- `htmlBody`: o HTML preenchido;
- `body`: a versão em texto puro.

### 6. Confirmar ao usuário
Diga que o rascunho foi criado (mencione o assunto e quantas reuniões/quantas
tarefas entraram) e lembre que ele está no Gmail em **Rascunhos**, pronto para
revisar e clicar em **Enviar** — a skill não envia sozinha. Se quiser, ofereça
ajustar período ou destinatário e gerar de novo.

## Dicas de qualidade
- Ordene as reuniões da mais recente para a mais antiga.
- Se houver muitas tarefas, agrupe-as por reunião dentro do bloco em destaque para
  ficar legível, mas mantenha-as todas visíveis no topo.
- Datas e nomes: use o que está na nota; não preencha responsável/prazo com
  suposições. É melhor deixar em branco do que inventar.
- Não crie rótulos, não mande para a lixeira nem mexa em outros e-mails — o único
  efeito colateral desta skill é criar UM rascunho.
