# claude-arquivos

Repositório de arquivos e experimentos.

## Skills

### `resumo-faturas`

Resume faturas de cartão separando gasto pessoal (PF) de gasto da construtora
(PJ), aloca o que é PJ por obra e gera resumo em texto, planilha e PDF.

Basta pedir em linguagem natural — "resume essas faturas de julho", "separa o
que é da empresa", "manda pro contador" — que a skill é acionada. Veja
`.claude/skills/resumo-faturas/SKILL.md` para o fluxo completo.

Antes do primeiro uso, copie `.claude/skills/resumo-faturas/assets/config.exemplo.yaml`
para `faturas/config.yaml` e preencha os cartões e as obras.
