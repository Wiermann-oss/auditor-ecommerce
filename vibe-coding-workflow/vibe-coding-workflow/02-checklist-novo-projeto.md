# 02 — Checklist de Novo Projeto

> Cobre Fase 0 (Discovery) e Fase 1 (Fundação documental). Do nada ao primeiro código possível.

> **Estilo de explicação obrigatório:** seguir [`principios/comunicacao-com-usuario.md`](principios/comunicacao-com-usuario.md) — analogia primeiro, termo técnico depois, sem encadear jargão.

---

## Antes de começar

- [ ] Tenho clareza sobre o **problema** que o produto resolve? (Não a solução — o problema.)
- [ ] Sei quem vai usar isso? (Eu mesmo? Um cliente? Vários papéis?)
- [ ] Tenho ao menos 30-60 minutos contínuos para a primeira sessão de discovery?
- [ ] Decidi o nome do projeto e o diretório onde vai morar.

Se respondeu "não" a alguma das três primeiras → **não comece o projeto ainda**. Volte quando tiver clareza. Começar com problema mal definido é a forma número 1 de produzir software inútil.

---

## Fase 0 — Discovery

### Sessão 0.1 — Entrevista de produto

1. [ ] Crie o diretório do projeto e entre nele:
   ```bash
   mkdir nome-do-projeto && cd nome-do-projeto
   ```
2. [ ] Abra o Claude Code (sessão nova, vazia).
3. [ ] Cole o prompt de `prompts/00-discovery.md`.
4. [ ] **Responda em primeira pessoa, falando do negócio.** Não tente parecer técnico.
5. [ ] Quando o Claude pedir um exemplo concreto, dê um exemplo real, não inventado.
6. [ ] Se o Claude tentar gerar o `PRODUCT.md` antes de cobrir todas as 8 áreas, interrompa: "ainda não cobrimos [X]".

**Áreas que devem ser cobertas (cheque uma a uma):**
- [ ] Visão e proposta de valor (incluindo o que **não** é).
- [ ] Usuários e papéis (com contexto, frequência, frustrações).
- [ ] Glossário do domínio (com definição, exemplo, relações, sinônimos proibidos).
- [ ] Entidades do negócio (atributos, ciclo de vida).
- [ ] Fluxos principais (pré-condições, passos, pós-condições, divergências).
- [ ] KPIs com fórmula, unidade, frequência, faixas de alerta.
- [ ] Escopo v1 vs futuro vs nunca.
- [ ] Restrições e premissas operacionais.

### Sessão 0.2 — Geração do PRODUCT.md

1. [ ] Cole o prompt de `prompts/01-gerar-product-md.md`.
2. [ ] O Claude deve gerar `PRODUCT.md` seguindo `templates/PRODUCT.md.template`.
3. [ ] Leia o documento inteiro.
4. [ ] Para cada seção, marque mentalmente: "isso é exatamente o que eu disse?". Se não, peça correção.
5. [ ] **Critério de saída:** você consegue mostrar o `PRODUCT.md` para alguém que não conhece o projeto, e essa pessoa entende o que é, para quem, e por quê.

---

## Fase 1 — Fundação documental

### Sessão 1.1 — CLAUDE.md

1. [ ] Decida o stack. Se não souber, use `referencia/stack-recomendado.md`.
2. [ ] Abra sessão nova do Claude Code.
3. [ ] Cole o prompt de `prompts/02-gerar-claude-md.md`.
4. [ ] Forneça o stack escolhido como input.
5. [ ] Leia o `CLAUDE.md` gerado **integralmente**.
6. [ ] Verifique:
   - [ ] Stack está exatamente como você escolheu.
   - [ ] Glossário tem todos os termos do `PRODUCT.md`.
   - [ ] Regras invioláveis fazem sentido (não tem nada que parece "regra de Akita aplicada cega" sem motivo).
   - [ ] Padrões de implementação canônicos estão presentes (como criar módulo CRUD, migration, componente UI, endpoint).
   - [ ] Anti-patterns têm exemplo ruim **e** bom.

### Sessão 1.2 — ARCHITECTURE.md inicial

1. [ ] Sessão nova (limpa).
2. [ ] Cole o prompt de `prompts/03-gerar-architecture-md.md`.
3. [ ] **Importante:** o Claude deve te perguntar se há decisões com mais de uma opção viável **antes** de gerar. Se não perguntar, peça.
4. [ ] Tome as decisões pendentes com o Claude apresentando prós/contras.
5. [ ] Deixe o Claude gerar o `ARCHITECTURE.md`.
6. [ ] Verifique seção por seção (ver `templates/ARCHITECTURE.md.template`).

### Sessão 1.3 — Estrutura de pastas

1. [ ] Cole no Claude:
   ```
   Crie a estrutura de pastas conforme referencia/estrutura-projeto.md
   e o ARCHITECTURE.md. Não crie nenhum arquivo de código ainda —
   apenas a árvore de pastas com .gitkeep onde necessário.
   ```
2. [ ] Confira que existe:
   - [ ] `docs/specs/`
   - [ ] `docs/decisions/`
   - [ ] `docs/sessions/`
   - [ ] Pastas de código (ex: `src/app/`, `src/components/`, `src/lib/`, `src/types/`)
   - [ ] Pasta de banco/migrations (ex: `supabase/migrations/`)

### Sessão 1.4 — Inicializar git

1. [ ] `git init`
2. [ ] Crie `.gitignore` apropriado para o stack.
3. [ ] Primeiro commit: `chore: fundação documental e estrutura inicial`.

---

## Critério de passagem para Fase 2

Você só passa para Fase 2 quando:

- [ ] `PRODUCT.md` aprovado por você, sem partes vagas.
- [ ] `CLAUDE.md` lido inteiro, regras fazem sentido.
- [ ] `ARCHITECTURE.md` lido inteiro, você consegue desenhar os módulos no papel.
- [ ] Estrutura de pastas criada conforme planejado.
- [ ] Git inicializado, primeiro commit feito.

**Tempo realista:** 4 a 10 horas distribuídas em 2 a 5 sessões. Não tente fazer tudo em uma só.

---

## Os 3 erros que matam projeto na largada

1. **Discovery raso.** PM amador faz 3 perguntas; PM bom faz 30. Se a entrevista durou menos de 1 hora, foi rasa.
2. **Aceitar `ARCHITECTURE.md` genérico.** Se o documento não tem fluxos rastreados (passo a passo do que acontece tecnicamente em cada fluxo do produto), é raso.
3. **Pular para código.** A tentação é grande. Resista. Cada hora gasta em Fase 0+1 economiza dias em Fase 3.

---

## Mantra

> Fase 0 e 1 não são "preparação". São **construção** — você está construindo o substrato do projeto. Sem substrato denso, todo código que vier depois é fundação flutuante.
