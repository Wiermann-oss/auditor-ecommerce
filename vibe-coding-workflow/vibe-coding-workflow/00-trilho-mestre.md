# 00 — O Trilho Mestre

> Leia uma vez para entender o sistema todo. Depois consulte os checklists específicos de cada fase.

---

## A premissa

Dev sênior controla qualidade lendo código. Você não. Seu mecanismo de controle é diferente: **documentação viva + spec antes de código + revisão arquitetural periódica**. Esse trilho compensa a habilidade que você não tem com um processo que você consegue executar.

A ideia não é virar dev sênior. É construir software real com risco controlado, sem essa habilidade.

---

## Os dois eixos do trilho

**Eixo 1: documentos vivos no projeto**
Documentos que ficam dentro do repositório e são lidos em toda sessão.

**Eixo 2: prompts e checklists no seu guia**
Material que vive aqui, fora do projeto, e é reutilizado em todo projeto novo.

A separação é deliberada: o que muda por projeto fica no projeto; o que é universal fica no guia.

---

## As 5 fases

```
Fase 0 — Discovery                    (sem código, sem repositório)
   ↓ produz: PRODUCT.md
Fase 1 — Fundação documental          (sem código, repositório criado)
   ↓ produz: CLAUDE.md, ARCHITECTURE.md inicial, estrutura de pastas
Fase 2 — Esqueleto técnico            (primeiro código, sem features de negócio)
   ↓ produz: projeto rodando local + login + log de sessão
Fase 3 — Módulos de negócio (loop)    (90% do tempo do projeto vive aqui)
   ↓ produz: features funcionando + specs + ARCHITECTURE.md atualizado
Fase 4 — Revisão arquitetural         (a cada 3-5 features de Fase 3)
   ↓ produz: diagnóstico, ADRs, lista de correções
```

Você nunca pula uma fase. Pular é o sintoma clássico de projeto que vai dar ruim em 3 meses.

---

## Fase 0 — Discovery

**Objetivo**
Transformar o que está na sua cabeça em `PRODUCT.md` denso o suficiente para sustentar todo o resto do projeto.

**O que existe antes**
Nada. Diretório vazio.

**O que você usa**
- `prompts/00-discovery.md` — entrevista de PM conduzida pelo Claude.
- `prompts/01-gerar-product-md.md` — geração do documento ao final.
- `templates/PRODUCT.md.template` — referência da estrutura obrigatória.

**Saída**
`PRODUCT.md` cobrindo: visão, usuários, glossário do domínio, entidades, fluxos, KPIs com fórmula, escopo v1 vs futuro vs nunca, restrições.

**Critério de passagem**
Você consegue ler o `PRODUCT.md` inteiro e dizer "sim, é isso" para cada seção. Se hesitar em qualquer parte, volta e refina.

**Tempo típico**
2 a 6 horas, distribuídas em 1 a 3 sessões.

**Erro mais comum**
Aceitar entrevista superficial. Se o Claude não te perguntou pelo menos uma vez "me dê um exemplo concreto", a entrevista foi rasa.

---

## Fase 1 — Fundação documental

**Objetivo**
Criar `CLAUDE.md` e `ARCHITECTURE.md` antes de qualquer código.

**O que existe antes**
`PRODUCT.md` aprovado por você.

**O que você usa**
- `prompts/02-gerar-claude-md.md`
- `prompts/03-gerar-architecture-md.md`
- `templates/CLAUDE.md.template`
- `templates/ARCHITECTURE.md.template`
- `referencia/estrutura-projeto.md` (estrutura de pastas)
- `referencia/stack-recomendado.md` (stack default)

**Saída**
- `CLAUDE.md` (manual do agente neste projeto)
- `ARCHITECTURE.md` inicial (mapa do sistema, ainda planejado)
- Estrutura de pastas vazia: `docs/specs/`, `docs/decisions/`, `docs/sessions/`

**Critério de passagem**
- Você consegue desenhar no papel os módulos do `ARCHITECTURE.md` e como se conectam.
- Você lê o `CLAUDE.md` e entende cada regra inviolável.
- Se algum item parece "vazio" ou genérico, volta e refina.

**Erro mais comum**
`ARCHITECTURE.md` raso ("listei os módulos") em vez de denso (responsabilidade única, dependências, modelo de dados, fluxos rastreados, pontos frágeis honestos).

---

## Fase 2 — Esqueleto técnico

**Objetivo**
Projeto rodando localmente: `npm run dev`, login funcionando, banco conectado. **Nenhuma feature de negócio.**

**O que existe antes**
`PRODUCT.md`, `CLAUDE.md`, `ARCHITECTURE.md`.

**O que você usa**
- `prompts/04-inicio-sessao.md`
- `prompts/09-fim-sessao.md`
- `templates/session.md.template`

**Saída**
- Projeto Next.js (ou stack escolhida) rodando local.
- Auth funcional.
- Estrutura de pastas conforme `ARCHITECTURE.md`.
- Primeiro arquivo em `docs/sessions/`.
- `ARCHITECTURE.md` atualizado.

**Critério de passagem**
Você roda o comando, abre no navegador, faz login, vê uma tela vazia. Se quebrar, **não avança** — corrige antes.

**Erro mais comum**
Tentar implementar uma feature pequena junto ("já que estou aqui"). Não faça. Fundação quebrada acumula bugs invisíveis nas features seguintes.

---

## Fase 3 — Módulos de negócio (loop)

**Onde vive 90% do projeto.** Cada feature passa por 6 passos.

```
3.1 Pedir spec  →  3.2 Validar spec  →  3.3 Validar contexto
                                              ↓
                                          3.4 Implementar
                                              ↓
                            3.6 Atualizar docs ← 3.5 Testar manual
```

**O que existe antes**
Documentos da Fase 1 + projeto rodando da Fase 2.

**O que você usa por feature**
- `prompts/04-inicio-sessao.md`
- `prompts/05-pedir-spec.md` (passo 3.1)
- `prompts/06-validacao-contexto.md` (passo 3.3)
- `prompts/07-implementar.md` (passo 3.4)
- `prompts/08-corrigir-bug.md` (se 3.5 falhar)
- `prompts/09-fim-sessao.md` (passo 3.6)
- `templates/spec.md.template`
- `templates/session.md.template`

**Saída por feature**
- `docs/specs/[nome].md` validada por você.
- Código funcionando no navegador.
- `ARCHITECTURE.md` atualizado.
- `docs/sessions/YYYY-MM-DD-[tema].md`.

**Critério de passagem para próxima feature**
Atual está funcionando no navegador **e** documentada. Não funciona se qualquer um dos dois falhar.

**Erro mais comum**
Pular spec porque "essa é simples". Se a feature toca regra de negócio, dinheiro ou dados — spec obrigatória.

---

## Fase 4 — Revisão arquitetural

**Objetivo**
Detectar dívida técnica antes de virar bola de neve.

**Quando**
A cada 3 a 5 features implementadas. Não menos. Não mais.

**O que você usa**
- `prompts/10-revisao-arquitetural.md`
- `prompts/12-criar-adr.md` (se virar decisão duradoura)
- `templates/decision.md.template`

**Saída**
- Diagnóstico do Claude com severidade alta/média/baixa.
- Sua decisão por item: consertar agora, documentar e adiar, ou ignorar.
- ADRs novos em `docs/decisions/` quando aplicável.

**Critério de passagem**
Você sai da revisão com uma lista clara de o que fazer nas próximas sessões.

**Erro mais comum**
Tentar consertar tudo na hora. Não. Diagnóstico primeiro, decisão depois, conserto numa sessão dedicada.

---

## Quando você não está em fase nenhuma

Algumas situações não se encaixam nas 5 fases acima:

**Retomada após pausa (>3 dias)**
Use `prompts/11-retomar-projeto.md`. O Claude lê os docs e te diz onde parou.

**Bug em produção**
Não tem fase. Vai direto: diagnóstico → causa raiz → correção → log de sessão. Use `prompts/08-corrigir-bug.md`.

**Mudança de produto (PRODUCT.md desatualizado)**
Volta para Fase 0 só na seção afetada. Atualiza `PRODUCT.md` antes de qualquer código novo.

**Refatoração grande**
Não é Fase 3. É uma sessão dedicada com seu próprio ADR antes de começar (em `docs/decisions/`).

---

## A regra de ouro

> **Documentação não é burocracia. É o mecanismo que te dá controle sobre um projeto que você não consegue ler linha por linha.**

Toda vez que você sentir vontade de pular um passo do trilho "porque é mais rápido", pergunte: *o que eu vou usar para detectar que algo deu errado?* Se a resposta for "vou ver na hora", você está construindo às cegas.

---

## Próximo passo

- Primeira vez? Leia `principios/clean-code-llm.md`, `principios/prompt-engineering.md`, `principios/context-engineering.md` (15 min cada).
- Antes de qualquer sessão, garanta que o agente leu `principios/comunicacao-com-usuario.md` — define como ele deve te explicar coisas técnicas.
- Vai começar projeto agora? Vai para `02-checklist-novo-projeto.md`.
- Já tem projeto andando? Vai para `01-checklist-sessao.md`.
