# Layouts conhecidos

Referência de onde ficam os campos em cada tipo de documento. Use como guia,
mas não como camisa de força — softwares e bancos mudam de layout, então
extraia pelo **significado** do campo, não pela posição fixa.

## 1. Relatório do software de controle (ex.: "Relatório de Pagamentos")

PDF com camada de texto, uma tabela com vários lançamentos. Cabeçalho traz
emissão, período e totais (Pago / Em aberto / Total). Rodapé traz o nome da
empresa pagadora.

Cada lançamento tem, tipicamente:

| Campo no relatório        | Vai para (pagamento.json) | Observações                                          |
|---------------------------|---------------------------|------------------------------------------------------|
| Vencimento                | `data`                    | dd/mm/aaaa                                            |
| Status                    | `status`                  | "Em aberto" / "Pago"                                 |
| Valor                     | `valor`                   | "R$ 1.775,00"                                        |
| Favorecido                | `favorecido`              | nome de quem recebe                                  |
| Dados:                    | `documento` e/ou `chave_pix` | pode ser CPF, CNPJ, telefone, chave Pix, Ag/Conta |
| N° Doc:                   | `n_doc`                   | "ref oc 3414" — identificador interno da OC/ordem   |
| Descrição / Categoria     | `descricao`               | contexto, não usado no casamento                     |
| Condição / Conta          | `forma`                   | "À Vista", "Pix", "Transferência", "Boleto", banco  |

**Cuidado na extração:** o texto do PDF vem com as colunas **intercaladas**
entre várias linhas (o valor aparece antes do nome, o "N° Doc" no meio, etc.).
Não tente casar por posição de linha. Leia o bloco inteiro de cada lançamento e
monte o registro pelo sentido de cada pedaço.

O campo **Dados** é heterogêneo. Separe o que for documento do que for chave:
- `501.621.013-68` → CPF → `documento`
- `53.077.185/0001-07` → CNPJ → `documento`
- `(98)98180-8766` ou `88997265990` → telefone → `chave_pix`
- `PIX: 02472849397` → CPF sem pontuação → `documento`
- `Ag: 0001 Conta: 50364832-8` → dados bancários → `chave_pix` (guarde como veio)

## 2. Comprovante do banco (ex.: Inter Empresas — Pix enviado)

Geralmente é **print/imagem** (PNG/JPG) ou PDF de uma tela. Um comprovante por
arquivo. Leia por **visão** quando for imagem. Estrutura:

```
[logo do banco]
Pix enviado
R$ 765,00                          <- valor

Sobre a transação
  Data da transação   Terça-feira, 21/07/2026   <- data (ignore o dia da semana)
  Horário             08h44                      <- horario
  ID da transação     E00416968202607211109...   <- id_transacao (End-to-End)

Quem recebeu
  Nome         Mario Barbosa Lima      <- recebedor_nome
  CPF/CNPJ     ***.290.871-**          <- recebedor_documento  (CPF MASCARADO!)
  Instituição  BCO DO BRASIL S.A.
  Chave Pix    +5563981389094          <- recebedor_chave

Quem pagou
  Nome         ANA K S CARDOSO LTDA    <- pagador_nome
  CPF/CNPJ     42.206.653/0001-71
  Instituição  BANCO INTER
```

### Detalhe crítico: CPF mascarado

No comprovante o CPF de quem recebeu vem como `***.NNN.NNN-**` — só os **6
dígitos do meio** aparecem. O relatório tem o CPF completo. O script
`comparar.py` já sabe casar CPF completo (11 dígitos) com máscara (6 dígitos do
meio) — basta você extrair o documento como está em cada lado. **Não invente**
os dígitos ocultos; copie a máscara literalmente (`***.290.871-**`).

### Chave Pix é polivalente

A "Chave Pix" do recebedor pode ser telefone (`+5563981389094`), CPF completo
(`066.217.703-75`), CNPJ, e-mail ou chave aleatória. Por isso o casamento tenta
bater o `documento`/`chave_pix` do relatório tanto contra `recebedor_documento`
quanto contra `recebedor_chave` do comprovante.

## 3. Outros bancos

Os rótulos mudam ("Comprovante de transferência", "Favorecido" em vez de "Quem
recebeu", "Beneficiário", etc.), mas os campos essenciais são os mesmos: valor,
data, nome de quem recebeu, documento de quem recebeu, e um identificador da
transação. Mapeie para o mesmo schema de `comprovante` e o resto funciona igual.
