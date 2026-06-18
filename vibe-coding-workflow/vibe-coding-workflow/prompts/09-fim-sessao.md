# Prompt — Fim de Sessão

> Use no fim de **toda** sessão. Sem exceção. Sessão sem fechamento é sessão incompleta.

> **Estilo de explicação obrigatório:** seguir [`../principios/comunicacao-com-usuario.md`](../principios/comunicacao-com-usuario.md) — analogia primeiro, termo técnico depois, sem encadear jargão.

---

## Como usar

1. Sessão prestes a encerrar (feature feita, ou pausa).
2. Substitua `[TEMA_DA_SESSAO]` por algo curto descritivo (ex: "modulo-lotes", "fix-conversao-alimentar", "revisao-arquitetural").
3. Cole o prompt.

---

## Prompt

```
Vamos fechar a sessão.

PASSO 1 — ATUALIZAR ARCHITECTURE.md
Atualize ARCHITECTURE.md refletindo o estado real do sistema
agora. Cubra:

A) Diagrama de módulos (seção 2)
   - Mude o estado de módulos afetados
     (planejado → em construção → pronto)
   - Adicione módulos novos
   - Adicione/remova dependências entre módulos

B) Entidades e modelo de dados (seção 3)
   - Adicione tabelas novas com colunas, FKs, índices, RLS
   - Atualize tabelas modificadas

C) Fluxos de dados (seção 4)
   - Adicione fluxos novos rastreados tecnicamente
   - Atualize fluxos alterados

D) Decisões arquiteturais já tomadas (seção 5)
   - Se houve decisão duradoura nesta sessão, adicione resumo
     com link para docs/decisions/[arquivo].md

E) Pontos frágeis (seção 6)
   - Adicione fragilidades descobertas
   - Remova fragilidades que foram consertadas

F) Inventário de arquivos críticos (seção 7)
   - Adicione arquivos novos importantes

PASSO 2 — CRIAR LOG DE SESSÃO
Crie docs/sessions/YYYY-MM-DD-[TEMA_DA_SESSAO].md seguindo
EXATAMENTE este template:

```markdown
# Sessão YYYY-MM-DD — [tema curto]

## Objetivo da sessão
[1 frase]

## O que foi feito
- [bullets concretos com arquivo entre parênteses quando relevante]

## Decisões tomadas
Para cada decisão:
- Decisão: [o que foi decidido]
- Por quê: [motivo]
- Descartado: [alternativa rejeitada]
- ADR criado? [sim/não — link se sim]

## Problemas encontrados
- Problema: [descrição]
  Causa: [causa raiz]
  Solução: [solução aplicada]
  Status: [resolvido/aberto]

## Estado do projeto agora
- Funcionando: [...]
- Quebrado/incompleto: [...]

## Próximo passo
1. [item concreto]
2. [item concreto]
3. [item concreto]

## Atualizações em outros documentos
- ARCHITECTURE.md: [resumo do que mudou]
- CLAUDE.md: [resumo do que mudou, se mudou]
- docs/decisions/: [arquivos criados, se houve]
- docs/specs/: [arquivos criados/atualizados]
```

PASSO 3 — ADRs (SE APLICÁVEL)
Se nesta sessão tomamos uma decisão arquitetural DURADOURA
(algo que vai impedir ou enviesar decisões futuras), crie
docs/decisions/YYYY-MM-DD-[tema].md com:
- Problema
- Decisão tomada
- Motivo
- Alternativas descartadas (com motivo)
- O que essa decisão FECHA como possibilidade futura

Exemplos de "decisão duradoura":
- Escolha de padrão de banco (UUID vs auto-increment)
- Estratégia de auth (cookies vs JWT vs session)
- Modo de fazer multitenancy
- Convenção de nomenclatura nova
- Escolha entre duas bibliotecas concorrentes

NÃO é decisão duradoura:
- Bug fix pontual
- Renomear uma variável
- Adicionar uma validação

PASSO 4 — RESUMO FINAL
No final da sua resposta, liste:
- Arquivos criados
- Arquivos modificados
- Documentos atualizados
- ADRs criados (se houver)
- O que rodar para verificar (comandos)

PASSO 5 — PROMPT DA PRÓXIMA SESSÃO (SE HOUVER SEQUÊNCIA)
Se esta sessão é parte de um plano multi-etapas (existe um arquivo
em docs/plans/*-etapas.md, um roadmap explícito, ou uma sequência
definida) E ainda há etapa pendente, gere ao final um prompt
copy-paste pronto para a próxima sessão, dentro de um bloco de
código markdown.

Estrutura:
- Baseie-se em prompts/04-inicio-sessao.md, mas adapte para a
  próxima etapa específica (não use o template genérico cru).
- Liste os arquivos a ler: CLAUDE.md, ARCHITECTURE.md, MEMORY.md
  (se houver memórias relevantes para a etapa), o log de sessão
  recém-criado no passo 2, o spec da feature (se aplicável), e
  a seção exata da próxima etapa no plano.
- A confirmação A/B/C/D deve ser AJUSTADA ao foco da próxima
  etapa, não copiada do template:
    * Etapa de código → "regras invioláveis" e "termo do glossário"
    * Etapa operacional/deploy → "pontos frágeis" e "pendências
      operacionais que bloqueiam"
    * Etapa de revisão → "critérios de aceite ainda não cobertos"
- Inclua TAREFA DE HOJE com 1 frase concreta da próxima etapa.
- Termine com "Não comece a executar. Apenas confirme A, B, C, D."

Se NÃO houver próxima etapa óbvia (feature completa, fim de
projeto, nada planejado adiante), pule este passo e diga
explicitamente:
"Sem próxima etapa identificada. Para retomar, abra novo plano
ou use prompts/04-inicio-sessao.md genérico."

NUNCA invente uma próxima etapa. Se o plano tem só 5 etapas e
acabamos a 5, é fim — diga que é fim.
```

---

## Verificação após fechamento

- [ ] `ARCHITECTURE.md` foi atualizado (não é o mesmo de antes).
- [ ] `docs/sessions/YYYY-MM-DD-*.md` foi criado.
- [ ] Se houve decisão duradoura, ADR foi criado.
- [ ] Você consegue ler o log e entender o que foi feito.
- [ ] Próximo passo está claro para a próxima sessão.
- [ ] Se há próxima etapa: prompt copy-paste foi gerado, cita os
      arquivos certos, e o A/B/C/D faz sentido para a etapa específica.
- [ ] Se NÃO há próxima etapa: foi dito explicitamente.

---

## Commit

Após fechamento documental:

```bash
git add .
git commit -m "feat: [descrição da feature]" # ou fix: / chore: / docs:
```

Mensagem descritiva. Nunca "ajustes", "wip", "stuff".

---

## Quando pular passos

**Nunca pule** o passo 1 (ARCHITECTURE.md) e o passo 2 (log).

**Pode pular** o passo 3 (ADR) se a sessão não teve decisão duradoura.

**Pode pular** o passo 5 (prompt da próxima sessão) se a feature
acabou ou não há sequência planejada — mas o Claude tem que dizer
isso explicitamente, não silenciar.

Em dúvida sobre o passo 3 → pergunte ao Claude: "isso conta como decisão arquitetural duradoura? por quê?"

---

## Mantra

> Documentação não atualizada é mentira documentada. A próxima sessão lê esse documento como verdade — se for mentira, o próximo trabalho começa errado.
