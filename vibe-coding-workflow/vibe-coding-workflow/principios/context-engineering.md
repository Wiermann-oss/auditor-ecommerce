# Princípio — Context Engineering

> Como gerenciar **o que o agente vê** numa sessão. A diferença entre projeto que escala e projeto que vira labirinto em 2 meses.

---

## A premissa

Janela de contexto é finita e cara. Cada token consumido em "contexto irrelevante" é um token a menos para raciocínio. Então você não joga **tudo** que sabe — joga **o relevante para a tarefa atual**, e nada mais.

A isso se chama **contexto cirúrgico** (Karpathy + Langchain).

---

## Os 4 tipos de contexto

### 1. Contexto persistente do projeto
- `CLAUDE.md`
- `ARCHITECTURE.md`
- `PRODUCT.md` (lido sob demanda)
- Carregado em **toda** sessão. Não negociável.

### 2. Contexto persistente da feature/tarefa
- `docs/specs/[feature].md` (se feature)
- `docs/decisions/[tema].md` (se relevante)
- Carregado **quando a tarefa atual toca essa feature/decisão**.

### 3. Contexto efêmero da sessão
- Mensagens que você troca durante a sessão atual.
- Decisões momentâneas, ajustes, correções.
- Some quando a sessão fecha. Por isso o **log de sessão** é crítico.

### 4. Contexto de código carregado
- Arquivos que o agente leu durante a sessão.
- Os caminhos importam: ler 1 arquivo grande de 800 linhas é pior que ler 4 arquivos de 200.

---

## A fórmula do contexto cirúrgico

Em qualquer sessão de Fase 3 (feature):

```
Contexto = CLAUDE.md
        + ARCHITECTURE.md
        + último log em docs/sessions/
        + spec da feature em docs/specs/
        + arquivos de código que a feature toca
        + ADRs relacionados
```

**Não** entra:
- `PRODUCT.md` inteiro (só seções específicas se relevantes)
- Specs de outras features
- Logs antigos de outras sessões
- Arquivos de código não relacionados

---

## Anti-padrões de contexto

### 1. Contexto inflado — "joga tudo"
**Sintoma:** você cola arquivos enormes, todo o histórico, especificações de outras features.
**Resultado:** Lost in the Middle. Agente esquece o que é importante.
**Correção:** liste só o que a tarefa precisa. Se em dúvida, pergunte ao agente: "do que você precisa para esta tarefa?".

### 2. Contexto zero — "começa limpo sem ler nada"
**Sintoma:** você abre janela nova e pede direto sem o agente ler `CLAUDE.md`/`ARCHITECTURE.md`.
**Resultado:** agente reinventa convenções, viola regras invioláveis, infere domínio errado.
**Correção:** sempre comece com `prompts/04-inicio-sessao.md`.

### 3. Contexto fantasma — informação só na cabeça do usuário
**Sintoma:** você sabe que existe a regra X, mas ela não está em nenhum doc.
**Resultado:** agente nunca aplica X. Você corrige toda vez. Frustração.
**Correção:** se você precisou explicar 2x, **vai para o `CLAUDE.md` ou para o glossário do `PRODUCT.md`**.

### 4. Contexto desatualizado
**Sintoma:** `ARCHITECTURE.md` diz uma coisa, código diz outra.
**Resultado:** agente confia no doc errado e produz código errado.
**Correção:** atualizar docs ao **fim de toda sessão** — regra de ouro.

### 5. Contexto duplicado
**Sintoma:** mesma regra escrita em 3 docs diferentes (PRODUCT.md, CLAUDE.md, spec).
**Resultado:** atualiza um, esquece os outros. Divergência.
**Correção:** uma regra mora em **um** lugar canônico, e os outros referenciam.

---

## Onde mora cada coisa (tabela canônica)

| Tipo de informação | Mora em |
|---|---|
| Visão de produto, usuários, escopo | `PRODUCT.md` |
| Glossário detalhado do domínio | `PRODUCT.md` (canônico) + `CLAUDE.md` (resumido) |
| Stack, convenções, regras invioláveis | `CLAUDE.md` |
| Padrões de implementação canônicos | `CLAUDE.md` |
| Estrutura de pastas | `CLAUDE.md` |
| Mapa de módulos do sistema | `ARCHITECTURE.md` |
| Modelo de dados (tabelas) | `ARCHITECTURE.md` |
| Fluxos técnicos rastreados | `ARCHITECTURE.md` |
| Pontos frágeis | `ARCHITECTURE.md` |
| Comportamento de uma feature específica | `docs/specs/[feature].md` |
| Decisão arquitetural duradoura | `docs/decisions/[tema].md` |
| O que foi feito hoje | `docs/sessions/[data].md` |

Sempre que precisar saber "onde mora isso?", consulte essa tabela.

---

## Estratégia de retenção do contexto

### Por sessão (curto prazo)
- Janela limpa para tarefas independentes.
- Mesma janela para tarefas dependentes (continuidade de raciocínio).
- Quando o output começar a piorar (repetição, esquecimento de regra), feche e abra nova.

### Entre sessões (médio prazo)
- O **log de sessão** é o mecanismo de retenção. Quando você abre a próxima sessão, o agente lê o último log e "lembra" onde estava.

### Longo prazo (meses)
- ADRs em `docs/decisions/` são a memória dos "porquês" arquiteturais.
- `ARCHITECTURE.md` é a memória do "o quê".
- `PRODUCT.md` é a memória do "para quem e por quê".

Sem um desses, o projeto perde a memória nesse eixo.

---

## A lei do contexto cirúrgico

> Quanto mais relevante e menos volumoso o contexto, melhor o output. Inflar contexto não melhora — degrada. Carregar de menos não funciona — gera invenção. O ponto ótimo é **suficiente para a tarefa, nada além**.

---

## Auditoria de contexto

Faça periodicamente (a cada 5-10 sessões):

1. Abra uma sessão nova.
2. Pergunte: "se você fosse retomar este projeto sem nada além dos docs, conseguiria? O que está faltando?"
3. O agente vai apontar lacunas.
4. Para cada lacuna: ou cria um doc, ou atualiza um existente.

---

## Sinais de contexto saudável

- Sessão nova consegue continuar de onde a anterior parou só lendo docs.
- Agente cita termos do glossário corretamente sem você ensinar.
- Agente respeita regras invioláveis sem você lembrar.
- Você não precisa repetir nada que já está documentado.

---

## Sinais de contexto doente

- Você fica explicando a mesma coisa toda sessão.
- Agente reinventa convenções diferentes em cada módulo.
- Documentação contradiz o código.
- Você não sabe mais qual é a fonte da verdade para regra X.

Quando vir 1 ou mais sinais doentes → **sessão de manutenção de contexto**, antes de qualquer feature nova.

---

## Mantra

> Documentação não é overhead. É **memória persistente** que substitui sua incapacidade de carregar todo o projeto na cabeça e de inspecionar o código a fundo.
