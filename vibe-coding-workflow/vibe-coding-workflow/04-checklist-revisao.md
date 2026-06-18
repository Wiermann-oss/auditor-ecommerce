# 04 — Checklist de Revisão Arquitetural (Fase 4)

> A cada 3 a 5 features implementadas, sessão dedicada **só** a diagnóstico. Sem implementação.

> **Estilo de explicação obrigatório:** seguir [`principios/comunicacao-com-usuario.md`](principios/comunicacao-com-usuario.md) — analogia primeiro, termo técnico depois, sem encadear jargão.

---

## Quando fazer

- [ ] Implementei 3 a 5 features desde a última revisão.
- [ ] Sinto que o projeto está "estranho" mas não consigo apontar onde.
- [ ] Estou começando a duplicar lógica entre módulos (ou suspeito disso).
- [ ] Vou começar uma feature grande e quero entrar com a base limpa.

Qualquer um desses motivos basta. Mas pelo menos **um** dos quatro deve ser verdade.

---

## Pré-flight

- [ ] Não há código não commitado.
- [ ] `ARCHITECTURE.md` foi atualizado pela última sessão de feature.
- [ ] Tem 1 a 2 horas livres.
- [ ] Você está disposto a **não consertar nada hoje**. Hoje é diagnóstico.

---

## Sessão de revisão

### Passo 4.1 — Diagnóstico

1. [ ] Sessão nova do Claude Code.
2. [ ] Cole `prompts/04-inicio-sessao.md`.
3. [ ] Cole `prompts/10-revisao-arquitetural.md`.
4. [ ] Deixe o Claude analisar.
5. [ ] O retorno deve ter os itens classificados por severidade (alta/média/baixa).

**O que o diagnóstico deve cobrir:**
- [ ] Inconsistências entre `ARCHITECTURE.md` e código real.
- [ ] Decisões conflitantes entre módulos (mesma regra calculada de jeitos diferentes).
- [ ] Duplicação de lógica de negócio.
- [ ] Funções/arquivos acima dos limites do `CLAUDE.md`.
- [ ] Tipos `any`, `unknown` mal usados, ou type assertions perigosas.
- [ ] Tratamento de erros silencioso (catch que engole erro).
- [ ] Acoplamento excessivo entre módulos que deveriam ser independentes.
- [ ] Pontos onde escala vai quebrar primeiro.
- [ ] Migrations que tornam certas mudanças futuras irreversíveis.

### Passo 4.2 — Triagem

Para cada item do diagnóstico, decida:

- **CONSERTAR AGORA** (no máximo 2-3 itens):
  - Risco arquitetural alto.
  - Bloqueia features futuras.
  - Quanto mais demorar, pior fica.

- **DOCUMENTAR E ADIAR** (cria entrada em `docs/decisions/` com prazo):
  - Risco médio, mas dá pra conviver.
  - Tem decisão a tomar e você ainda não tem dados.

- **ACEITAR** (registra no log que foi decidido aceitar):
  - Risco baixo ou inexistente.
  - Custo de consertar é maior que custo de manter.

- **REJEITAR** (registra que discordou do diagnóstico):
  - Você analisou e o Claude está exagerando.
  - Documenta o motivo no log para não voltar a discutir.

### Passo 4.3 — ADRs (se aplicável)

Para cada item "DOCUMENTAR E ADIAR" ou "CONSERTAR AGORA com mudança de padrão":

1. [ ] Cole `prompts/12-criar-adr.md`.
2. [ ] Forneça contexto: problema, decisão, alternativas descartadas.
3. [ ] Verifique que o ADR foi criado em `docs/decisions/YYYY-MM-DD-[tema].md`.

### Passo 4.4 — Conserto (apenas se decidido na triagem)

**Importante:** se decidiu consertar 2-3 itens, considere fazer numa **outra sessão**. Misturar diagnóstico com conserto polui o contexto.

Se decidir consertar nesta sessão:
1. [ ] Para cada item, peça ao Claude um plano de mudança (não a mudança).
2. [ ] Valide o plano.
3. [ ] Peça a implementação.
4. [ ] Teste no navegador.

### Passo 4.5 — Fechamento

1. [ ] Cole `prompts/09-fim-sessao.md` adaptando o tema para "revisão arquitetural".
2. [ ] O log de sessão deve incluir:
   - [ ] Lista de itens diagnosticados.
   - [ ] Decisão tomada para cada item (CONSERTAR / ADIAR / ACEITAR / REJEITAR).
   - [ ] Links para ADRs criados.
   - [ ] Estado pós-revisão.

---

## Critério de saída

- [ ] Lista clara de itens, com decisão por item.
- [ ] ADRs criados onde aplicável.
- [ ] `ARCHITECTURE.md` atualizado se houve conserto.
- [ ] Log de sessão criado.
- [ ] Você sabe quais são os 2-3 problemas mais sérios do projeto **agora**.

---

## Os 3 erros típicos da revisão

1. **Consertar tudo.** Tentação de "limpar". Resultado: refatoração massiva, regressões, frustração. Resista.
2. **Não consertar nada.** Outra tentação: "vou anotar e depois vejo". Adiar tudo é como não ter feito a revisão. Conserte ao menos os de severidade alta.
3. **Deixar diagnóstico vago.** Se o Claude diz "o módulo X está acoplado", peça exemplo concreto: "qual função no módulo X depende de qual função no módulo Y?". Diagnóstico sem exemplo não é diagnóstico.

---

## Mantra

> Revisão é prevenção. Consertar dívida pequena agora é 10x mais barato que consertar dívida grande depois — e dívida grande é dívida pequena que você ignorou por 3 meses.
