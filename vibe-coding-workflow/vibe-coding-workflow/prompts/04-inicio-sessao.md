# Prompt — Início de Sessão

> Use no começo de **toda** sessão de qualquer projeto que já passou da Fase 1.

> **Estilo de explicação obrigatório:** seguir [`../principios/comunicacao-com-usuario.md`](../principios/comunicacao-com-usuario.md) — analogia primeiro, termo técnico depois, sem encadear jargão.

---

## Como usar

1. Sessão nova do Claude Code (janela limpa).
2. Substitua `[TAREFA_DE_HOJE]` pelo objetivo em 1 frase.
3. Cole o prompt.
4. **Aguarde a confirmação explícita.** Não comece a tarefa antes.

---

## Prompt

```
Antes de fazer qualquer outra coisa nesta sessão:

1. Leia o arquivo CLAUDE.md inteiro.
2. Leia o arquivo ARCHITECTURE.md inteiro.
3. Leia o último arquivo em docs/sessions/ (se existir).

Quando terminar, responda OBRIGATORIAMENTE com:
A) Stack do projeto (3 itens principais)
B) 3 regras invioláveis do CLAUDE.md mais relevantes para a
   tarefa de hoje
C) Estado atual do projeto em 2 frases (baseado em
   ARCHITECTURE.md e último log)
D) O termo do glossário que mais provavelmente vai aparecer
   na tarefa de hoje, com a definição

Só depois disso, espere minha próxima instrução.

TAREFA DE HOJE: [TAREFA_DE_HOJE]

Não comece a executar a tarefa ainda. Apenas confirme A, B, C, D.
```

---

## Verificação após resposta do Claude

Antes de continuar, confirme:

- [ ] (A) Stack bate com o `CLAUDE.md`.
- [ ] (B) Regras citadas são reais (estão no `CLAUDE.md`).
- [ ] (C) Estado bate com o que você lembra do último log.
- [ ] (D) Termo e definição estão corretos.

**Se qualquer item falhar:**
- Peça para reler o arquivo específico.
- Se persistir, há algo desatualizado nos docs — investigue **antes** de seguir.

**Sinais de alerta graves (pare a sessão):**
- Claude descreve stack diferente da real → `CLAUDE.md` foi ignorado ou está corrompido.
- Claude descreve features inexistentes → ele inventou. Confiabilidade baixa nesta sessão.
- Claude usa termos que não estão no glossário → vocabulário inconsistente. Atualize o glossário antes.

---

## Variação para projetos com muitos docs

Se o projeto tem `docs/specs/` cheio e a tarefa toca uma feature já especificada, adicione:

```
4. Leia também docs/specs/[nome-da-feature].md
```

Mas **só** se a feature já tem spec. Caso contrário, fique nos 3 arquivos base.
