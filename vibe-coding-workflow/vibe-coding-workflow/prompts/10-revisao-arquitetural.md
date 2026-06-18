# Prompt — Revisão Arquitetural

> Use a cada 3-5 features implementadas. Sessão dedicada **só** a diagnóstico.

> **Estilo de explicação obrigatório:** seguir [`../principios/comunicacao-com-usuario.md`](../principios/comunicacao-com-usuario.md) — analogia primeiro, termo técnico depois, sem encadear jargão.

---

## Como usar

1. Sessão nova do Claude Code.
2. Cole `prompts/04-inicio-sessao.md` primeiro.
3. Após confirmação, cole o prompt abaixo.

---

## Prompt

```
Esta sessão é de REVISÃO ARQUITETURAL. Não vamos implementar
nada. Vamos diagnosticar.

PASSO 1 — LER E MAPEAR
1. Releia ARCHITECTURE.md inteiro.
2. Leia o conteúdo de src/ (todos os arquivos relevantes
   de código de negócio).
3. Leia os últimos 5 arquivos em docs/sessions/.
4. Liste os módulos que existem no código vs os que existem
   no ARCHITECTURE.md. Aponte discrepâncias.

PASSO 2 — DIAGNÓSTICO
Produza um diagnóstico estruturado, com itens classificados
por severidade ALTA, MÉDIA, BAIXA. Cubra obrigatoriamente:

A) Inconsistências docs vs código
   - O que ARCHITECTURE.md diz que NÃO bate com o código?
   - O que existe no código que NÃO está no ARCHITECTURE.md?

B) Decisões conflitantes entre módulos
   - Mesma regra de negócio implementada de jeitos
     diferentes em módulos diferentes
   - Mesma entidade representada de formas inconsistentes

C) Duplicação de lógica
   - Funções similares em arquivos diferentes
   - Cálculos iguais em lugares diferentes
   - Validações repetidas

D) Violações do CLAUDE.md
   - Funções acima do limite (>20 linhas)
   - Arquivos acima do limite (>500 linhas)
   - Indentação acima de 2 níveis
   - Tipos `any` ou type assertion sem justificativa
   - Nomes genéricos (handler, data, manager, etc)
   - Catch silencioso

E) Acoplamento problemático
   - Módulo A depende de detalhes internos de B (deveria
     ser interface)
   - Ciclos de dependência
   - Módulos que mudam juntos (sinal de mau fatiamento)

F) Pontos de escala
   - Onde a v1 vai engasgar primeiro com volume
   - Queries não indexadas
   - N+1 queries
   - Falta de paginação

G) Reversibilidade
   - Migrations que tornam mudanças futuras irreversíveis
   - Decisões que fecham caminhos sem ADR

H) Dívida documentada vs real
   - Pontos frágeis listados em ARCHITECTURE.md que ainda
     existem
   - Pontos frágeis NÃO listados que você descobriu agora

PASSO 3 — FORMATO DA RESPOSTA
Para cada item, formato exato:

### [SEVERIDADE] [Categoria]: [Título curto]
**Onde:** [arquivo:linha ou módulo]
**O que:** [descrição em 1-2 linhas]
**Por que importa:** [consequência se não for tratado]
**Sugestão:** [conserto possível]
**Custo de adiar:** [baixo/médio/alto]

PASSO 4 — RESUMO EXECUTIVO
No final, me dê:
- Top 3 problemas mais sérios (severidade ALTA)
- Top 3 mais fáceis de resolver (alto retorno por hora)
- Pelo menos 1 que pode ser ACEITO (não vale a pena consertar)

PASSO 5 — NÃO FAÇA NADA
Não conserte nada nesta sessão. Não modifique código. Não
atualize ARCHITECTURE.md ainda. Apenas diagnóstico.
```

---

## Como usar o resultado

Para cada item do diagnóstico, decida:

| Decisão | Quando | O que fazer |
|---|---|---|
| **CONSERTAR AGORA** | Severidade ALTA + impacto bloqueante | Em sessão separada (não esta) |
| **DOCUMENTAR E ADIAR** | Severidade MÉDIA + dá pra conviver | Criar ADR com prazo |
| **ACEITAR** | Severidade BAIXA + custo > benefício | Registrar no log que aceitou |
| **REJEITAR** | Você discordou | Registrar motivo no log |

---

## Sinais de diagnóstico raso

- Itens sem `arquivo:linha` ou nome de módulo.
- Severidade quase toda igual (provavelmente ALTA).
- Sugestões genéricas ("refatorar", "limpar").
- Lista curta demais (< 5 itens em projeto com 5+ features).

Quando vir, peça aprofundamento.

---

## Encerramento da sessão de revisão

Use `prompts/09-fim-sessao.md` adaptando:
- Tema: `revisao-arquitetural`
- Log inclui: lista de itens, decisão por item, ADRs criados.

---

## Mantra

> Diagnóstico hoje vale 10x conserto amanhã. Revisão pulada é dívida invisível dobrando — até virar bola de neve que não dá mais para parar.
