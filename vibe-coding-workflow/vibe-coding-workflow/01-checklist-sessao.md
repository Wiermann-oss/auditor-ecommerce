# 01 — Checklist Universal de Sessão

> Aplica-se a **toda** sessão de trabalho num projeto que já passou da Fase 1. Independentemente do que você vai fazer hoje.

> **Estilo de explicação obrigatório:** seguir [`principios/comunicacao-com-usuario.md`](principios/comunicacao-com-usuario.md) — analogia primeiro, termo técnico depois, sem encadear jargão.

---

## Antes de abrir o Claude Code

- [ ] Estou no diretório certo do projeto? (`pwd` confirma)
- [ ] Sei qual é o objetivo desta sessão em 1 frase? Se não, pare e escreva.
- [ ] Esta sessão é: implementar feature / corrigir bug / refatorar / explorar / revisar / outro?
- [ ] Há código não commitado da sessão anterior? Decidir o que fazer com ele antes de continuar.

---

## Início de sessão (sempre)

1. **Abra uma janela nova do Claude Code.** Janela limpa é regra.
2. **Cole o prompt de início de sessão** (`prompts/04-inicio-sessao.md`).
3. **Aguarde a confirmação.** O Claude precisa responder explicitamente que leu `CLAUDE.md` e `ARCHITECTURE.md`. Se a resposta for genérica, peça para resumir as 3 coisas mais importantes que aprendeu nos docs — se errar, há algo desatualizado.
4. **Estabeleça o objetivo.** Diga em 1 frase o que vai fazer hoje. Se a sessão for de implementação, diga também qual módulo do `ARCHITECTURE.md` ela afeta.

**Sinais de alerta no início:**
- Claude não menciona nenhum termo do glossário do `CLAUDE.md` → docs estão rasos ou desatualizados.
- Claude descreve o projeto de forma genérica ("um sistema web para gerenciar dados") → docs não foram lidos com profundidade.
- Claude propõe stack diferente da definida → `CLAUDE.md` está sendo ignorado, **pare e investigue**.

---

## Durante a sessão

Independentemente do tipo de trabalho:

- [ ] **Pergunta antes de assumir.** Se o Claude começar a inferir algo do domínio, interrompa: "isso veio de onde? do `PRODUCT.md` ou inferência?".
- [ ] **Uma coisa por vez.** Se a tarefa começar a crescer ("já que estou aqui, também vou..."), pare. Anote no log e foque no objetivo desta sessão.
- [ ] **Mantenha o `ARCHITECTURE.md` em mente.** Se o que está sendo feito não bate com algum módulo descrito, é sinal de divergência. Atualiza o doc ou ajusta o código — nunca os dois fora de sincronia.
- [ ] **Code review por amostragem.** Mesmo sem ler o código todo, abra 1-2 arquivos modificados e pergunte ao Claude: "explica o que esta função faz em linguagem de negócio". Se a explicação for confusa, o código está confuso.

---

## Fim de sessão (sempre)

1. **Cole o prompt de fim de sessão** (`prompts/09-fim-sessao.md`).
2. **Verifique os artefatos:**
   - [ ] `ARCHITECTURE.md` foi atualizado refletindo o que mudou.
   - [ ] `docs/sessions/YYYY-MM-DD-[tema].md` foi criado.
   - [ ] Se houve decisão arquitetural duradoura → arquivo em `docs/decisions/` foi criado.
3. **Leia o log.** Se você não entender o que está escrito no log, ele está ruim. Peça para reescrever em linguagem mais simples.
4. **Commit no git** (se usa git): mensagem descritiva, **não** "ajustes" ou "wip".

**Regra de fechamento:**
> Se você fechou a sessão sem atualizar `ARCHITECTURE.md` e criar log, considere a sessão como **incompleta**. Volta amanhã, lê o que foi feito, e fecha direito antes de começar coisa nova.

---

## Os 5 sinais de que a sessão está saindo do trilho

1. Você não consegue explicar em 1 frase o que está sendo feito agora.
2. O Claude está modificando arquivos que não estavam no plano.
3. Aparece código com termo de domínio errado (use o glossário do `CLAUDE.md` para verificar).
4. Aparecem comentários do tipo `// TODO` ou `// FIX` — sinal de feature pela metade.
5. Você está aceitando respostas sem ler porque "está tarde".

Quando vir 2 ou mais → pare, fecha a sessão (mesmo incompleta), volta amanhã.

---

## Mantra

> Toda sessão tem início, meio e fim. Pular o início (ler docs) ou o fim (atualizar docs) **destrói a sessão seguinte**, não esta.
