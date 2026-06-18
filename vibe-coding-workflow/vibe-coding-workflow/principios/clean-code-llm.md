# Princípio — Clean Code para LLM

> Adaptação dos 13 princípios do Akita ("Clean Code para Agentes de IA") aplicados a este workflow. Por que cada princípio existe, quando aplicar e quando ignorar.

---

## A premissa que muda tudo

Código deixou de ser escrito apenas para humanos lerem. O leitor primário agora é um LLM (Claude). LLMs têm restrições específicas:

- **Truncamento de arquivo.** Arquivos enormes são lidos em chunks → contexto perdido.
- **Degradação de atenção.** Quanto mais token, pior a qualidade do raciocínio.
- **Janela limitada.** Mesmo modelos premium têm limites práticos.
- **Custo por token.** Contexto grande = sessão cara.

Conclusão: código otimizado para LLM precisa ser **denso, pequeno, previsível e bem nomeado**.

**MAS:** seu objetivo não é virar Akita. É construir SaaS sem virar dev. Por isso, alguns princípios são adotados ao pé da letra; outros são moderados; e um é rejeitado.

---

## Os 13 princípios e como aplicar

### 1. Funções pequenas (4–20 linhas) — **ADOTAR**

**Por quê:** funções pequenas cabem inteiras no contexto do agente, e cada uma tem uma única razão para mudar. Você consegue pedir "explica essa função em linguagem de negócio" e validar a resposta.

**Como aplicar:**
- Limite máximo: 20 linhas. Acima disso, divida.
- Limite mínimo: 4 linhas. Abaixo disso, pode ser inline.

**Exceção:** funções de "orquestração" (que só chamam outras em sequência) podem ter 25-30 linhas se forem só linhas de chamada.

---

### 2. SRP — Single Responsibility — **ADOTAR**

**Por quê:** se o nome da função/módulo precisa de "e" (`processarEEnviar`), está fazendo duas coisas. Duas responsabilidades = dois lugares para bug, contexto dobrado, refator dobrado.

**Como aplicar:**
- Frase de responsabilidade sem "e".
- Se aparecer "e", divida.

---

### 3. Nomes únicos com poucos hits no grep — **ADOTAR**

**Por quê:** seu mecanismo de revisão é grep + leitura. Nome `processData` aparece 47 vezes, então você não consegue rastrear nada. Nome `calcularConversaoAlimentarDoCiclo` aparece 1 vez.

**Como aplicar:**
- Verbo + objeto **específico**.
- Sem `handle*`, `process*`, `manage*`, `do*`.
- Para validar: rode `grep -r "nomeDaFuncao" src/` e confirme < 5 hits relevantes.

---

### 4. Comentários com proveniência — **MODERAR**

**Akita diz:** comentar não o "o quê", mas o "porquê" e a proveniência.

**O que adotar:** comentários que ligam código a regras de negócio numeradas (`// R3 da spec lotes`).

**O que rejeitar:** invenção de proveniência onde não há histórico ainda. Se o projeto tem 1 mês, não há proveniência. Coloque o "porquê" em `docs/decisions/`, não no código.

**Regra prática:**
- Comentário no código: amarra o código à regra de negócio (R1, R2...).
- ADR em `docs/decisions/`: o motivo arquitetural duradouro.
- README/CLAUDE.md: convenção do projeto.

---

### 5. Tipos explícitos — **ADOTAR (ferreamente)**

**Por quê:** você não tem dev sênior revisando. O type checker é sua primeira camada de testes. Sem tipos, qualquer mudança pode ser regressão silenciosa.

**Como aplicar:**
- TypeScript estrito (`"strict": true` no `tsconfig`).
- Nunca `any`. Se precisar mesmo, `unknown` com narrow.
- Sem `as Foo` sem comentário explicando.
- Tipos de retorno explícitos em funções públicas.

---

### 6. DRY — **MODERAR (perigosamente)**

**Akita diz:** repetição consome tokens e gera inconsistência.

**O perigo:** abstração prematura é pior que duplicação. Para você, *muito* pior — você não consegue avaliar se a abstração é boa.

**Regra prática:**
- 2 linhas iguais em 2 lugares: deixa.
- 3+ linhas iguais em 3+ lugares: extrai.
- Lógica de negócio idêntica em 2 lugares: extrai (perigo de divergência é alto).
- Se a "duplicação" tem semântica diferente em cada lugar (parece igual mas não é): não extrai. Vai virar acoplamento falso.

---

### 7. Testes que o agente consegue rodar — **ADOTAR**

**Por quê:** loop fechado de validação. O agente implementa, roda os testes, confirma que passou. Sem isso, você fica como único oráculo — gargalo enorme.

**Como aplicar:**
- Pelo menos um teste por regra de negócio crítica da spec.
- Testes rodam com 1 comando (no `CLAUDE.md` seção 8).
- Falha ruidosa, não silenciosa.

**Pragmática:** não exija 100% de cobertura. Exija cobertura nas regras de negócio numeradas (R1, R2...) e nos cálculos de KPI.

---

### 8. Estrutura de diretório previsível — **ADOTAR**

**Por quê:** o agente navega pelo filesystem. Se cada módulo tem layout diferente, ele inventa caminhos errados.

**Como aplicar:**
- `CLAUDE.md` seção 3 documenta a estrutura.
- Todo módulo de negócio segue o mesmo layout (`types.ts`, `*-service.ts`, `*-validators.ts`, etc).
- `referencia/estrutura-projeto.md` neste guia tem o template.

---

### 9. Dependency Injection / testabilidade — **MODERAR**

**Akita diz:** injeção facilita testes e isolamento.

**O perigo:** DI ortodoxa em projeto pequeno cria 3 camadas de abstração que ninguém entende.

**Regra prática:**
- Para serviços externos (banco, API, fila): wrapper com interface no projeto.
- Para regra de negócio interna: chamar direto. Não invente DI.
- Quando começar a ter mais de 1 implementação de algo: aí extrai interface.

---

### 10. Sem aninhamento profundo — **ADOTAR**

**Por quê:** profundidade > 2 níveis sobrecarrega rastreamento de contexto. Você lê com dificuldade; o agente lê pior.

**Como aplicar:**
- Máximo 2 níveis de indentação.
- Use early returns (`if (!x) return ...`).
- Extraia bloco interno como função.

---

### 11. Erros com contexto — **ADOTAR**

**Por quê:** mensagens genéricas (`"Erro"`, `"Invalid input"`) não ajudam você nem o agente a diagnosticar.

**Como aplicar:** toda mensagem inclui:
1. **O valor** que causou o erro.
2. **A forma esperada.**
3. **O lugar** (módulo / contexto).

Exemplo: `LoteInválido em fecharLote: id="abc" não é UUID v4`

---

### 12. Formatação e estilo consistentes — **ADOTAR**

**Por quê:** consistência reduz carga cognitiva. Cada estilo diferente é tokenômico.

**Como aplicar:**
- Prettier + ESLint configurados.
- Roda no pre-commit (husky/lefthook).
- `CLAUDE.md` seção 8 tem o comando.

---

### 13. Sem comentários óbvios — **ADOTAR**

**Por quê:** ruído tokenômico. `// pega o usuário pelo id` em cima de `getUserById` é redundância pura.

**Como aplicar:**
- Comentário só quando o código não conta a história sozinho.
- Comentário só para o "porquê", nunca o "o quê".
- Comentário ligado a regra de negócio: `// R3 da spec`.

---

## O princípio que é REJEITADO

**"Código não é mais para humanos lerem."**

Para você, **é**. O código é caixa-preta na maior parte do tempo, mas você ainda precisa abrir um arquivo de tempos em tempos e entender, mesmo que pedindo explicação ao agente. Se o código foi otimizado só para máquina, e você não consegue navegar nele nem com ajuda, perdeu controle.

A premissa correta para você: **código otimizado para que o agente leia bem, mas estruturado de forma que você ainda consiga inspecionar pontos críticos com ajuda do agente**.

---

## Resumo aplicado

| Princípio | Aplicar como? |
|---|---|
| 1. Funções pequenas | Ferreamente. 4-20 linhas. |
| 2. SRP | Ferreamente. Sem "e" no nome. |
| 3. Nomes únicos | Ferreamente. < 5 hits no grep. |
| 4. Comentários com proveniência | Moderado. Liga a R# da spec. ADR no `docs/decisions/`. |
| 5. Tipos explícitos | Ferreamente. Sem `any`. |
| 6. DRY | Cuidadoso. 3+ duplicações = extrai. |
| 7. Testes executáveis | Ferreamente em regras de negócio críticas. |
| 8. Estrutura previsível | Ferreamente. Mesmo layout em todo módulo. |
| 9. DI | Moderado. Só pra serviços externos. |
| 10. Sem aninhamento | Ferreamente. Max 2 níveis. |
| 11. Erros com contexto | Ferreamente. Valor + forma + lugar. |
| 12. Formatação | Ferreamente. Prettier + lint. |
| 13. Sem comentário óbvio | Ferreamente. |

---

## Mantra

> Princípios são heurísticas, não dogma. O objetivo é **risco controlado**, não pureza estética. Aplica o que reduz seu risco; modera o que adiciona complexidade que você não consegue avaliar.
