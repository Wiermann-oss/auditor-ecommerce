# Prompt — Retomar Projeto

> Use quando voltar ao projeto após pausa de 3 dias ou mais. Substitui o `04-inicio-sessao.md` na primeira sessão de retomada.

> **Estilo de explicação obrigatório:** seguir [`../principios/comunicacao-com-usuario.md`](../principios/comunicacao-com-usuario.md) — analogia primeiro, termo técnico depois, sem encadear jargão.

---

## Como usar

1. Sessão nova do Claude Code no diretório do projeto.
2. Cole o prompt.
3. Aguarde o briefing antes de decidir o que fazer hoje.

---

## Prompt

```
Estou retomando este projeto após uma pausa. Antes de qualquer
coisa, faça um BRIEFING completo do estado atual.

PASSO 1 — LEITURA OBRIGATÓRIA (em ordem)
1. CLAUDE.md
2. ARCHITECTURE.md
3. PRODUCT.md (se mudou desde a última sessão)
4. Os 3 últimos arquivos em docs/sessions/ (em ordem cronológica)
5. Todos os arquivos em docs/decisions/ criados nas últimas
   2 semanas

PASSO 2 — BRIEFING
Quando terminar, me dê o seguinte briefing:

A) ESTADO DO PROJETO
- Em 3 frases: o que é, em que fase está
- Módulos prontos
- Módulos em construção (com % aproximado)
- Módulos planejados ainda não começados

B) ÚLTIMA SESSÃO
- Data
- O que foi feito
- O que ficou pendente
- Próximo passo planejado pelo "eu do passado"

C) DECISÕES RECENTES
- Lista resumida das decisões em docs/decisions/ recentes
- Quais ainda estão "abertas" / não tomadas

D) RISCOS ATUAIS
- Pontos frágeis listados no ARCHITECTURE.md
- Bugs/problemas em aberto registrados nos logs

E) DESALINHAMENTO POTENCIAL
- ARCHITECTURE.md está coerente com o último log?
- Há alguma seção do PRODUCT.md que parece desatualizada
  comparada com o que foi implementado?
- Alguma feature sem spec em docs/specs/?

F) SUGESTÃO DE PRÓXIMO PASSO
Baseado em (B) e (D), sugira:
- O que faria sentido fazer hoje
- Por quê
- Estimativa em horas

PASSO 3 — ESPERAR
Me apresente A-F e ESPERE minha decisão sobre o que fazer
hoje. Não comece nenhuma tarefa.
```

---

## Verificação do briefing

- [ ] (A) Bate com sua memória do projeto?
- [ ] (B) Bate com o último log que você lembra?
- [ ] (E) Apontou algo desalinhado? Conserte **antes** de qualquer feature nova.
- [ ] (F) Sugestão faz sentido?

---

## Decisão sobre o que fazer hoje

Após briefing:

- **Se há desalinhamento (E):** corrija primeiro. Atualize doc desatualizado.
- **Se a sugestão (F) faz sentido:** vá para o checklist apropriado (`02-checklist-novo-projeto.md`, `03-checklist-nova-feature.md`, ou `04-checklist-revisao.md`).
- **Se não tem certeza:** sessão curta de revisão arquitetural antes de decidir.

---

## Quando NÃO usar este prompt

- Pausa < 3 dias → use `04-inicio-sessao.md` normal.
- Está retomando porque deu erro de produção → use `08-corrigir-bug.md` direto.

---

## Mantra

> Voltar a um projeto é como voltar a um livro. Se você não relê o resumo, vai começar a ler do meio sem entender. Briefing é o resumo do livro do projeto.
