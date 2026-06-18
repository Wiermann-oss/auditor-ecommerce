# Princípio — Prompt Engineering aplicado a vibe coding

> Como falar com a IA de forma que o output seja consistente, confiável e auditável. Para usar Claude Code (ou agente equivalente) em desenvolvimento real.

---

## A diferença entre prompt e contexto

- **Prompt:** o que você diz **agora**, na mensagem atual.
- **Contexto:** tudo que o agente já sabe — `CLAUDE.md`, `ARCHITECTURE.md`, sessões anteriores carregadas, código que ele leu.

A maioria dos problemas de "prompt ruim" é, na verdade, **contexto ruim**. Antes de mexer no prompt, mexa no contexto.

---

## Os 8 princípios operacionais

### 1. Especifique a saída antes do raciocínio

**Ruim:** "Implementa o módulo de lotes."
**Bom:** "Implementa o módulo de lotes. Ao terminar, retorne: lista de arquivos criados, lista de modificados, comando para rodar, critérios de aceite implementados."

Por quê: definindo a forma da resposta, você força clareza. O agente raciocina para preencher um esqueleto, não para "fazer alguma coisa".

---

### 2. Force o agente a perguntar antes de inferir

**Ruim:** "Cria a spec do módulo X."
**Bom:** "Antes de gerar a spec, faça 3 perguntas críticas sobre o domínio que o PRODUCT.md não responde claramente. Espere minhas respostas."

Por quê: agente que não pergunta vai inferir. Inferência em domínio que ele não conhece é o vetor número 1 de bug.

---

### 3. Use papéis funcionais, não personalidades

**Ruim:** "Você é um genial 10x developer."
**Bom:** "Você é um product manager sênior conduzindo discovery."

Por quê: papel funcional ativa um repertório de comportamentos (perguntar, documentar, estruturar). "Genial" é flatery — não muda o output.

---

### 4. Estruture com numeração e seções

**Ruim:** "Considera segurança, testes, documentação, e também boas práticas de Clean Code, e tipos."

**Bom:**
```
Considere:
1. Segurança (RLS, validação na fronteira)
2. Testes (cobertura das regras R1-R5 da spec)
3. Documentação (atualização do ARCHITECTURE.md)
4. Clean Code (funções 4-20 linhas, tipos explícitos)
```

Por quê: seções numeradas ficam lidas. Frase corrida com "e" se perde no meio.

---

### 5. Diga o que NÃO fazer, não só o que fazer

**Ruim:** "Implementa a feature."
**Bom:** "Implementa a feature. NÃO toque arquivos fora da lista. NÃO adicione dependências. NÃO atualize ARCHITECTURE.md ainda — isso é etapa separada."

Por quê: agentes têm tendência a "ajudar mais". Restringir explicitamente é tão importante quanto pedir explicitamente.

---

### 6. Construa o prompt em camadas

Camada 1: **Objetivo** — o que precisa acontecer.
Camada 2: **Restrições** — o que não pode acontecer.
Camada 3: **Forma da saída** — como a resposta deve vir.
Camada 4: **Verificações** — como o próprio agente deve validar antes de entregar.

Os prompts deste guia (`prompts/*.md`) seguem essa estrutura.

---

### 7. Repita o que importa

LLMs sofrem de "perda no meio" (Lost in the Middle). Informação no meio do prompt é menos retida.

**Como compensar:**
- Coloque a regra mais importante no **início** e no **fim** do prompt.
- Se for mesmo crítico, repita 3 vezes em formas diferentes.

---

### 8. Peça verificação interna antes da entrega

**Ruim:** "Implementa e me entrega."
**Bom:** "Implementa. Antes de me entregar, verifique:
- Cada função tem ≤ 20 linhas?
- Tipos explícitos sem `any`?
- Cada regra R# da spec tem código identificável?
Se algo falhar, refatore antes de entregar."

Por quê: o agente passa a fazer code review do próprio output. Reduz erros bobos que você teria que apontar depois.

---

## Anti-patterns clássicos de prompt

### "Faz tudo direito"
- Vago. Não dá referência. Output qualquer.
- **Em vez:** "Faz X. Verifica Y. Não toca Z. Retorna no formato W."

### "Continua de onde parou"
- O agente não sabe onde parou.
- **Em vez:** "Leia o último arquivo em docs/sessions/. Confirme onde paramos. Espere minha aprovação para continuar."

### "Faz como você faria"
- Convida personalidade aleatória.
- **Em vez:** "Siga as convenções do CLAUDE.md (seção 2). Use os padrões canônicos (seção 6)."

### "Não esquece de testar"
- "Não esquece" é negação flutuante. LLMs lidam mal.
- **Em vez:** "Antes de entregar, rode `pnpm test` e garanta que passa. Se falhar, corrija antes de me responder."

---

## O efeito "warm-up"

Sessões longas com Claude tendem a melhorar nos primeiros 3-5 turnos (o agente "aquece" no contexto) e depois degradar (perda no meio, contexto inflado, repetições).

**Implicação para o trilho:**
- Sessões devem ter um **objetivo único**.
- Quando termina o objetivo, fecha a sessão e abre outra.
- Não tente fazer 3 features na mesma sessão.

---

## Validação contínua

A cada 3-4 turnos da sessão, faça uma de duas coisas:

1. **Pergunta de checagem:** "qual é o objetivo desta sessão?"
   - Se a resposta divergir do que combinaram, a sessão saiu do trilho. Pause.

2. **Pergunta de glossário:** "o que significa [termo do domínio] neste projeto?"
   - Se a resposta não bate com o glossário, o `CLAUDE.md` ficou fora do contexto. Pause e relembre.

---

## Mantra

> Prompt ruim com contexto bom funciona. Prompt bom com contexto ruim falha. Sempre invista primeiro no contexto (docs vivos), depois no prompt (forma da pergunta).
