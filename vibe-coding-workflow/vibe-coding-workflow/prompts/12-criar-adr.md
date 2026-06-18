# Prompt — Criar ADR (Architecture Decision Record)

> Use quando uma decisão arquitetural duradoura for tomada. Não use para qualquer decisão — só para as que vão impedir ou enviesar decisões futuras.

> **Estilo de explicação obrigatório:** seguir [`../principios/comunicacao-com-usuario.md`](../principios/comunicacao-com-usuario.md) — analogia primeiro, termo técnico depois, sem encadear jargão.

---

## O que é uma decisão "duradoura"?

**SIM, é ADR-vale:**
- Escolha de padrão de banco (UUIDs vs sequenciais; soft delete em todas as tabelas; etc).
- Estratégia de auth (cookies vs JWT; multi-fator obrigatório vs opcional).
- Como fazer multitenancy.
- Convenção nova de nomenclatura.
- Escolha entre duas bibliotecas concorrentes (com motivo).
- Decisão de não usar uma feature nativa do framework.
- Padrão de API (REST/GraphQL/RPC).
- Modo de errar (exceções vs Result type).

**NÃO é ADR-vale:**
- Bug fix.
- Renomear variável.
- Adicionar validação.
- Decidir cor de botão.
- Refatoração local.

---

## Como usar

1. Você está em sessão de feature/revisão e identificou uma decisão duradoura.
2. Tenha em mãos: o problema, a decisão tomada, alternativas consideradas.
3. Substitua os placeholders.
4. Cole o prompt.

---

## Prompt

```
Vamos registrar uma decisão arquitetural em um ADR.

CONTEXTO:
- Tema: [TEMA_CURTO_ex: "estrategia-soft-delete"]
- Problema: [DESCRIÇÃO_DO_PROBLEMA]
- Decisão tomada: [O_QUE_FOI_DECIDIDO]
- Alternativas consideradas: [LISTA_DE_ALTERNATIVAS]
- Por que essas alternativas foram descartadas:
  [JUSTIFICATIVA_POR_ALTERNATIVA]

GERE docs/decisions/YYYY-MM-DD-[TEMA].md com a estrutura
abaixo, sem pular seções:

# ADR — [Título descritivo]

**Data:** YYYY-MM-DD
**Status:** Aceito | Em discussão | Substituído por [...]
**Tema:** [tema curto]

## 1. Contexto
[2-4 parágrafos descrevendo o problema, o ambiente em que ele
surgiu, e por que precisa ser decidido agora. Linguagem clara,
sem jargão desnecessário.]

## 2. Decisão
[1-3 parágrafos descrevendo o que foi decidido, em forma
afirmativa: "Vamos usar X", "Adotaremos Y como padrão".]

## 3. Motivação
[Por que essa decisão? O que ela otimiza? Quais princípios
do projeto ela respeita? Cite CLAUDE.md/PRODUCT.md quando
aplicável.]

## 4. Alternativas consideradas
Para cada alternativa:

### Alternativa A: [Nome]
- Descrição
- Prós
- Contras
- Por que foi descartada

### Alternativa B: [Nome]
[mesmo formato]

## 5. Consequências

### Positivas
- [O que essa decisão habilita]

### Negativas
- [Custos / complexidade / limitações]

### O que essa decisão FECHA
- [Caminhos futuros que ficam mais difíceis ou impossíveis]

## 6. Implementação
- Onde essa decisão se materializa no código
- Quais arquivos/módulos afeta
- Há migration/refactor necessário?
- Há regra a adicionar no CLAUDE.md?

## 7. Revisão
- Quando essa decisão deve ser reavaliada?
- Sob que condições ela seria revertida?

REGRAS DE GERAÇÃO:
- Linguagem clara, sem jargão excessivo.
- Decisão em forma afirmativa.
- Pelo menos 2 alternativas consideradas (se só houvesse uma,
  não era decisão).
- Seção 5.3 (o que fecha) é OBRIGATÓRIA — é o que dá força ao
  ADR.
- Salvar em docs/decisions/YYYY-MM-DD-[TEMA].md.

PASSO EXTRA:
Após criar o ADR, sugira:
- Atualização em ARCHITECTURE.md (seção 5) referenciando
  este ADR
- Atualização em CLAUDE.md (se a decisão vira regra)
- Outras documentações afetadas
```

---

## Validação após geração

- [ ] Seção 5.3 (o que essa decisão fecha) está preenchida com itens concretos.
- [ ] Pelo menos 2 alternativas foram consideradas.
- [ ] Cada alternativa tem prós e contras.
- [ ] Status está marcado como "Aceito" (a menos que seja proposta).
- [ ] ARCHITECTURE.md foi atualizado para referenciar o ADR.

---

## Padrão de nomeação

`docs/decisions/YYYY-MM-DD-[tema-curto-em-kebab-case].md`

Exemplos:
- `docs/decisions/2026-04-25-soft-delete-em-todas-tabelas.md`
- `docs/decisions/2026-05-12-auth-com-supabase-magic-link.md`
- `docs/decisions/2026-06-03-uuid-em-vez-de-sequencial.md`

---

## ADR vs log de sessão

| Aspecto | ADR | Log de sessão |
|---|---|---|
| Foco | Decisão duradoura | O que foi feito hoje |
| Vida útil | Anos (ou até ser substituído) | Histórico permanente, mas raramente lido |
| Lido em | Decisões futuras relacionadas | Retomada após pausa |
| Estrutura | Estruturada (contexto/decisão/alternativas) | Linear (o que fiz, o que decidi, próximo passo) |
| Quantidade | Poucos (5-30 num projeto) | Muitos (1 por sessão) |

---

## Mantra

> ADR não é burocracia: é o "porquê" que vai sobreviver à sua memória. Daqui a 6 meses, você não vai lembrar por que escolheu X — o ADR vai.
