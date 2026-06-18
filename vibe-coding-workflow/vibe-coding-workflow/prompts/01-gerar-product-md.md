# Prompt — Gerar PRODUCT.md

> Use **depois** de concluir a entrevista de discovery. Mesma sessão da entrevista.

> **Estilo de explicação obrigatório:** seguir [`../principios/comunicacao-com-usuario.md`](../principios/comunicacao-com-usuario.md) — analogia primeiro, termo técnico depois, sem encadear jargão.

---

## Pré-requisitos

- [ ] Entrevista de discovery concluída.
- [ ] Todas as 8 áreas foram cobertas.
- [ ] Você confirmou que pode gerar o documento.

---

## Prompt

```
Agora gere o PRODUCT.md baseado em toda a entrevista que fizemos.

Use a estrutura abaixo, sem pular nenhuma seção. Se faltar
informação para alguma seção, NÃO INVENTE — pare, me pergunte,
e só continue depois da minha resposta.

ESTRUTURA OBRIGATÓRIA:

# [Nome do produto]

## 1. Visão e proposta de valor
- Frase de uma linha: o que o produto é.
- Parágrafo de 3-5 linhas: para quem, qual problema, como resolve.
- O que o produto NÃO é (lista de delimitações negativas).

## 2. Usuários e papéis
Para cada papel:
- Nome
- Contexto (quem é, nível técnico, ambiente de uso)
- Objetivos no sistema
- Frustrações atuais
- Frequência de uso

## 3. Glossário do domínio
Para cada termo, formato exato:

### [Termo]
**Definição:** [1-3 linhas]
**Exemplo:** [exemplo concreto]
**Relações:** [como se conecta com outros termos]
**NÃO confundir com:** [sinônimos proibidos, se houver]

## 4. Entidades do negócio
Para cada entidade:
- Nome
- Atributos relevantes (sem se preocupar com banco)
- Ciclo de vida (estados, transições)
- Quem cria, quem edita, quem consulta

## 5. Fluxos principais
Para cada fluxo:
- Nome
- Quem dispara
- Pré-condições
- Passos numerados em linguagem de negócio
- Pós-condições
- Divergências (quando aborta ou ramifica)

## 6. KPIs e regras de cálculo
Para cada KPI, formato exato:

### [Nome do KPI]
**Mede:** [em palavras]
**Fórmula:** [matemática simples, não código]
**Unidade:** [unidade]
**Frequência:** [diário, semanal, etc]
**Normal:** [faixa]
**Alerta:** [faixa]

## 7. Escopo
### 7.1 Entra na v1
- Lista
### 7.2 Fica para depois
- Lista com justificativa por item
### 7.3 Nunca vai entrar
- Lista com motivo

## 8. Restrições e premissas
- Operacionais
- Legais/regulatórias
- Orçamento/prazo
- Integrações futuras esperadas

REGRAS DE GERAÇÃO:
- Use linguagem do negócio, não técnica.
- Se faltar informação para uma seção, não invente — pergunte.
- Não use placeholders tipo "TBD" — cada seção sai pronta ou
  você me pergunta.
- Termos de domínio devem ser usados com consistência (sempre
  o mesmo termo para a mesma coisa).

Salve o arquivo como PRODUCT.md na raiz do projeto.
```

---

## Validação após geração

Leia o PRODUCT.md inteiro e confirme:

- [ ] Não tem nenhum "TBD" ou "a definir".
- [ ] Glossário tem TODOS os termos que apareceram na entrevista.
- [ ] Cada KPI tem fórmula explícita.
- [ ] Cada fluxo tem pré e pós-condição.
- [ ] Escopo nunca-entra está preenchido (não está vazio).
- [ ] Você consegue mostrar para alguém de fora e essa pessoa entende o produto.

Se algo falhar, peça correção pontual. Não regenere o documento inteiro.
