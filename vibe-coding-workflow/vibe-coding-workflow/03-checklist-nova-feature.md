# 03 — Checklist de Nova Feature (Fase 3)

> O ciclo que você vai repetir para cada feature do projeto. 6 passos. Sem atalhos para features que tocam regra de negócio, dinheiro ou dados.

> **Estilo de explicação obrigatório:** seguir [`principios/comunicacao-com-usuario.md`](principios/comunicacao-com-usuario.md) — analogia primeiro, termo técnico depois, sem encadear jargão.

---

## Quando NÃO usar este checklist

- Ajuste cosmético de UI (mudou cor, espaçamento, copy) → vai direto, sem spec.
- Bug crítico em produção → use `prompts/08-corrigir-bug.md`.
- Refatoração estrutural → não é feature, é sessão dedicada com ADR antes.

Para tudo que **não** está nessa lista: **siga o ciclo abaixo**.

---

## Pré-flight (antes do passo 1)

- [ ] Esta feature está prevista no `ARCHITECTURE.md`? Se não, atualize o `ARCHITECTURE.md` primeiro.
- [ ] Esta feature está no escopo v1 do `PRODUCT.md`? Se não, decida se entra ou se é v2+.
- [ ] Tem 1 a 3 horas livres? Feature parcial é pior que feature não começada.
- [ ] Não tem código não commitado da sessão anterior.

---

## Passo 3.1 — Pedir spec

1. [ ] Sessão nova do Claude Code.
2. [ ] Cole `prompts/04-inicio-sessao.md` (sempre).
3. [ ] Aguarde confirmação de leitura dos docs.
4. [ ] Cole `prompts/05-pedir-spec.md` adaptando o nome da feature.
5. [ ] **O Claude deve fazer 3 perguntas críticas antes de gerar a spec.** Se ele tentar gerar direto, interrompa: "antes de gerar, faça as 3 perguntas críticas sobre o domínio que o `PRODUCT.md` não responde claramente".
6. [ ] Responda as perguntas com profundidade.
7. [ ] Deixe o Claude gerar `docs/specs/[nome].md`.

**Saída desta etapa:** arquivo `docs/specs/[nome].md` seguindo `templates/spec.md.template`.

---

## Passo 3.2 — Validar spec

**Você lê. Sem código ainda.**

Para cada seção da spec, verifique:

- [ ] **Resumo:** consigo explicar essa feature para alguém em 30 segundos lendo só o resumo?
- [ ] **Comportamento funcional:** os caminhos cobrem o que o usuário realmente vai fazer? Inclui erros visíveis?
- [ ] **Dados envolvidos:** as entidades estão no `ARCHITECTURE.md`? Se há campo novo, faz sentido onde foi proposto?
- [ ] **Regras de negócio:** cada regra usa termos do glossário do `CLAUDE.md`? As regras estão **completas**, não exemplificativas?
- [ ] **UI/UX:** estados de loading, vazio, erro e sucesso aparecem? Permissões por papel batem com o `PRODUCT.md`?
- [ ] **Casos de borda:** a lista é específica desta feature? Se parecer genérica ("e se o usuário fizer X errado"), peça para detalhar.
- [ ] **Critérios de aceite:** eu consigo testar cada item no navegador sem ler código?
- [ ] **Riscos e impactos:** quais módulos existentes podem quebrar? Há reversibilidade?

**Se algo está faltando, peça correção:**
```
Corrija a spec: [seção X] está incompleta porque [motivo].
A regra que faltou é: [regra em linguagem de negócio].
```

**Critério de saída:** você consegue dizer "se isso for implementado exatamente assim, é o que eu quero". Sem hesitação.

---

## Passo 3.3 — Validar contexto

**Antes do código, confirma que o Claude entendeu.**

1. [ ] Cole `prompts/06-validacao-contexto.md`.
2. [ ] O Claude deve responder:
   - As 3 entidades principais desta feature.
   - Como ela se conecta com módulos existentes (citando nomes do `ARCHITECTURE.md`).
   - Qual é o maior risco de implementação.
   - Quais arquivos existentes ele vai tocar.
3. [ ] **Verificação cruzada:**
   - As entidades batem com o glossário?
   - As conexões batem com o `ARCHITECTURE.md`?
   - O maior risco faz sentido?
   - Os arquivos listados existem mesmo?
4. [ ] Se algo está errado, **corrija agora**, antes de o código existir.

**Critério de saída:** o Claude demonstrou entendimento factualmente correto do contexto.

---

## Passo 3.4 — Implementar

1. [ ] Cole `prompts/07-implementar.md`.
2. [ ] Deixe o Claude implementar.
3. [ ] **Não interrompa para "ajustar de leve".** Deixa terminar.
4. [ ] Quando terminar, peça uma listagem dos arquivos criados/modificados.
5. [ ] Abra 1 ou 2 dos arquivos modificados e peça: "explica o que esta função/componente faz em linguagem de negócio". Se a explicação for confusa, o código está confuso — peça refatoração.

**Sinais de alerta durante implementação:**
- Claude começa a tocar arquivos que **não estavam** na lista do passo 3.3 → pare e pergunte por quê.
- Aparece dependência nova (biblioteca npm) que não estava no `CLAUDE.md` → pare e decida (vai virar regra do `CLAUDE.md` ou rejeita).
- Aparece migration de banco → leia a migration. Pergunte ao Claude o que cada coluna faz.

---

## Passo 3.5 — Teste manual

**Você no navegador. Cada item da seção "Critérios de aceite" da spec.**

- [ ] Caminho feliz: passou.
- [ ] Pelo menos 1 caminho alternativo: passou.
- [ ] Pelo menos 1 caso de borda da spec: passou.
- [ ] Estados visuais (loading, vazio, erro, sucesso): vistos.
- [ ] Permissões por papel: testadas com usuário de papel diferente.

**Se quebrar:**
1. Não tente "consertar de qualquer jeito".
2. Use `prompts/08-corrigir-bug.md` que força diagnóstico antes da correção.
3. Volta a testar até passar todos os critérios.

**Critério de saída:** todos os critérios de aceite da spec passam no navegador.

---

## Passo 3.6 — Atualizar docs e fechar

1. [ ] Cole `prompts/09-fim-sessao.md`.
2. [ ] Verifique que o Claude:
   - [ ] Atualizou `ARCHITECTURE.md` (módulo agora aparece como "pronto" e não "planejado", entidades novas estão lá, fluxos novos rastreados).
   - [ ] Criou `docs/sessions/YYYY-MM-DD-[nome-feature].md`.
   - [ ] Se houve decisão arquitetural duradoura, criou `docs/decisions/YYYY-MM-DD-[tema].md`.
3. [ ] Leia o log da sessão.
4. [ ] Commit no git: mensagem descritiva no formato `feat: [nome da feature]` ou similar.

---

## Critério de "feature pronta"

Uma feature **só está pronta** quando:

- [ ] Todos os critérios de aceite da spec passam no navegador.
- [ ] `ARCHITECTURE.md` reflete o estado atual.
- [ ] Log de sessão criado.
- [ ] Commit feito.

Se faltar qualquer um dos quatro, **a feature não está pronta**. Não comece a próxima.

---

## Os 4 atalhos que parecem inofensivos e não são

1. **"A spec eu faço de cabeça."** Spec não escrita = spec não existida. Você não vai lembrar daqui a 2 semanas.
2. **"O log eu faço amanhã."** Não vai. E aí a próxima sessão começa sem contexto.
3. **"Esse caso de borda raramente acontece."** Raro acontece. E quando acontece, ninguém entende por quê.
4. **"O Claude já entendeu, não precisa validar contexto."** O custo do passo 3.3 é 2 minutos. O custo de pular é 2 horas refazendo código no caminho errado.

---

## Mantra

> A spec é seu único checkpoint sem ler código. Se a spec é rasa, seu projeto é cego. Densidade de spec = profundidade de controle.
