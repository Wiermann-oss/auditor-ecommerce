# Prompt — Implementar Feature

> Use após validação de contexto aprovada. Esta é a etapa em que o código nasce.

> **Estilo de explicação obrigatório:** seguir [`../principios/comunicacao-com-usuario.md`](../principios/comunicacao-com-usuario.md) — analogia primeiro, termo técnico depois, sem encadear jargão.

---

## Como usar

1. Validação de contexto aprovada (passo anterior).
2. Mesma sessão.
3. Substitua `[NOME_DA_FEATURE]`.
4. Cole o prompt.

---

## Prompt

```
Implemente [NOME_DA_FEATURE] conforme docs/specs/[NOME_DA_FEATURE].md.

REGRAS DE IMPLEMENTAÇÃO — siga estritamente:

1. FONTE DE VERDADE
- A spec é a fonte de verdade do COMPORTAMENTO.
- O CLAUDE.md é a fonte de verdade das CONVENÇÕES.
- O ARCHITECTURE.md é a fonte de verdade da ESTRUTURA.

2. ESCOPO
- Toque apenas os arquivos que você listou na validação de
  contexto.
- Se descobrir que precisa tocar arquivo extra, PARE e pergunte.
- Se descobrir que precisa de dependência nova, PARE e pergunte.

3. PADRÕES
- Funções de 4 a 20 linhas. Se passar, divide.
- Arquivos abaixo de 500 linhas. Se passar, divide.
- Tipos sempre explícitos. Nunca `any`.
- Nomes únicos com poucos hits no grep. Sem handle/process/manage.
- Early returns. Máximo 2 níveis de indentação.
- Erros com mensagem que inclui o valor que causou e a forma
  esperada.
- Use os padrões canônicos do CLAUDE.md (seção 6) para tarefas
  comuns (criar módulo CRUD, migration, componente, endpoint).

4. REGRAS DE NEGÓCIO
- Cada regra numerada da spec (R1, R2, ...) deve estar
  implementada e identificável no código.
- Se a regra não estiver óbvia no código, adicione comentário
  curto referenciando: // R3 da spec
- Use termos do glossário ao nomear funções, variáveis e
  tabelas.

5. TRATAMENTO DE ERROS
- Sem catch silencioso.
- Erro de validação: mensagem clara para o usuário.
- Erro inesperado: log estruturado + mensagem genérica para
  o usuário.

6. MIGRATIONS
- Se houver migration, ela deve ser reversível ou ter justificativa
  em comentário no topo.
- Inclua RLS, soft delete e auditoria conforme regras invioláveis
  do CLAUDE.md.

7. ENTREGÁVEL
Ao terminar, retorne:
- Lista de arquivos criados (caminho completo).
- Lista de arquivos modificados (caminho completo + resumo
  da mudança em 1 linha).
- Comando(s) que eu preciso rodar para ver funcionando localmente
  (incluindo migrations, se houver).
- Quais critérios de aceite da spec você considera implementados
  (lista numerada igual à da spec).

NÃO faça:
- Atualizar ARCHITECTURE.md ainda — isso é etapa separada.
- Criar log de sessão ainda — isso é etapa separada.
- Implementar coisa fora da spec.
- "Aproveitar para refatorar X" — refator é sessão dedicada.

Comece pela ordem que fizer mais sentido (geralmente:
migration → tipos → lógica de domínio → endpoint/serviço
→ UI). Anuncie cada etapa antes de começar.
```

---

## Durante a implementação

Observe:

- [ ] Claude **anuncia** cada etapa antes de implementar.
- [ ] Claude **não toca** arquivos fora da lista da validação de contexto.
- [ ] Claude **não adiciona** dependências sem perguntar.
- [ ] Cada arquivo grande gerado entra dentro do limite (< 500 linhas).
- [ ] Cada função grande gerada entra dentro do limite (< 20 linhas).

**Se vir uma das violações, interrompa imediatamente:**
- "Pare. Por que você está mexendo em [arquivo X]?"
- "Pare. De onde veio a dependência [Y]?"
- "Esta função tem [N] linhas. Divida antes de continuar."

---

## Após a implementação (antes do teste)

Pergunte ao Claude:

```
Para 2 dos arquivos mais importantes que você criou/modificou,
explique em linguagem de negócio o que cada função/componente
principal faz.
```

Se a explicação for confusa, o código está confuso. Peça refatoração antes de testar.

---

## Anti-padrões clássicos a vigiar

1. **Função de 80 linhas com 4 responsabilidades.** Sinal: você lê o nome e não consegue prever o que ela faz inteira.
2. **Catch que engole erro.** Sinal: `catch (e) {}` ou `catch (e) { console.log(e) }` em produção.
3. **`any` disfarçado.** Sinal: `as unknown as X` sem comentário explicando o porquê.
4. **Comentário óbvio.** Sinal: `// pega o usuário pelo id` em cima de `getUserById`.
5. **Lógica de negócio na UI.** Sinal: cálculo financeiro dentro de componente React.

Quando vir, peça refatoração imediata.
