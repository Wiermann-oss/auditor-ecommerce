# Prompt — Corrigir Bug

> Use quando algo quebrar (no teste manual ou em produção). **Diagnóstico antes de correção.**

> **Estilo de explicação obrigatório:** seguir [`../principios/comunicacao-com-usuario.md`](../principios/comunicacao-com-usuario.md) — analogia primeiro, termo técnico depois, sem encadear jargão.

---

## Como usar

1. Sessão (pode ser a atual ou nova; prefira atual se o bug surgiu agora).
2. Tenha em mãos: o que você fez, o que esperava, o que aconteceu.
3. Substitua os placeholders.
4. Cole o prompt.

---

## Prompt

```
Encontrei um bug. Antes de corrigir, vamos diagnosticar.

CONTEXTO:
- Feature/módulo afetado: [NOME]
- O que eu fiz: [PASSOS_DO_USUÁRIO]
- O que eu esperava: [COMPORTAMENTO_ESPERADO]
- O que aconteceu: [COMPORTAMENTO_OBSERVADO]
- Mensagem de erro (se houver): [MENSAGEM_OU_NADA]
- Arquivos relevantes: [LISTA_DE_ARQUIVOS]

PASSO 1 — DIAGNÓSTICO (SEM CORREÇÃO):
Investigue e me responda:

A) Qual é a CAUSA RAIZ do bug? Não o sintoma — a causa.
   Cite arquivo e linha quando aplicável.

B) Por que isso aconteceu? Qual decisão/código causou?
   Foi:
   - Bug de implementação (código não bateu com a spec)
   - Bug de spec (spec não previu o caso)
   - Bug de arquitetura (módulos mal separados)
   - Bug de dado (estado inválido)
   - Outro (descreva)

C) Que outros lugares do código podem ter o MESMO bug?
   Liste arquivos/funções suspeitas — não conserte ainda.

D) Qual é a correção MÍNIMA que resolve a causa raiz?
   Descreva em palavras (sem código ainda).

E) A correção precisa de atualização em algum doc?
   - PRODUCT.md (regra de negócio descoberta)
   - CLAUDE.md (regra de implementação que faltou)
   - ARCHITECTURE.md (mudança estrutural)
   - docs/specs/[feature].md (caso de borda que faltou)
   - docs/decisions/ (decisão arquitetural duradoura)

PASSO 2 — APROVAÇÃO:
Espere minha aprovação do diagnóstico antes de corrigir.

PASSO 3 — CORREÇÃO:
Quando eu aprovar, aplique a correção mínima descrita em (D)
e atualize os docs identificados em (E).

PASSO 4 — VERIFICAÇÃO:
Liste como eu posso confirmar no navegador que o bug foi
corrigido (e quais regressões testar).

NÃO faça:
- Correção sem diagnóstico aprovado.
- "Patch defensivo" que esconde o sintoma.
- Refatoração extra "já que está aqui".
- Catch silencioso para "evitar o erro".
```

---

## Sinais de que o diagnóstico está raso

- "É um problema de tipos." → não é diagnóstico, é categoria. Peça mais.
- "O state está incorreto." → onde? por quê? quem deveria ter setado?
- "O Supabase retornou erro." → qual erro? por quê?
- Não cita arquivo nem linha.

Quando vir, peça aprofundamento.

---

## Decisão pós-correção

Após o bug corrigido, decida:

- **Foi bug de spec?** → atualize a spec original e considere adicionar uma "lição aprendida" no `CLAUDE.md` (anti-pattern novo).
- **Foi bug de arquitetura?** → considere ADR em `docs/decisions/` se o problema vai se repetir.
- **Foi bug de implementação?** → log de sessão é suficiente.

---

## Mantra

> Bug não diagnosticado é bug que volta. Sempre. A correção mínima é mais valiosa do que a correção elegante.
