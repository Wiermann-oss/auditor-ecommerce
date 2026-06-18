# Vibe Coding Workflow — Guia Pessoal

> Guia operacional para desenvolver software com Claude Code sendo um dev júnior/não-dev, usando princípios de prompt engineering, context engineering e clean code para LLM.

---

## Para quem é este guia

- Você sabe ler código, mas não escreve do zero com fluência.
- Você usa Claude Code (ou agente equivalente) como ferramenta principal de desenvolvimento.
- Você quer construir projetos reais (SaaS, ferramentas internas, sites) sem virar dev sênior.
- Você quer **risco controlado**: nunca produzir código que ninguém entende em 3 meses — nem você, nem o agente.

---

## Como usar este guia

Toda vez que você for trabalhar num projeto, abre este guia e segue esta árvore de decisão:

```
Estou começando um projeto novo?
  → SIM → leia 02-checklist-novo-projeto.md
  → NÃO ↓

Estou retomando depois de pausa (>3 dias)?
  → SIM → use prompts/11-retomar-projeto.md
  → NÃO ↓

Vou implementar uma feature nova?
  → SIM → leia 03-checklist-nova-feature.md
  → NÃO ↓

Já implementei 3-5 features desde a última revisão?
  → SIM → leia 04-checklist-revisao.md
  → NÃO ↓

→ Use 01-checklist-sessao.md (checklist universal de qualquer sessão)
```

---

## Estrutura deste guia

```
vibe-coding-workflow/
├── README.md                          ← VOCÊ ESTÁ AQUI
├── 00-trilho-mestre.md                ← As 5 fases do trilho — leia 1x para entender o todo
├── 01-checklist-sessao.md             ← Checklist universal: início e fim de TODA sessão
├── 02-checklist-novo-projeto.md       ← Checklist Fase 0+1: do nada ao primeiro código
├── 03-checklist-nova-feature.md       ← Checklist Fase 3: ciclo de cada feature
├── 04-checklist-revisao.md            ← Checklist Fase 4: revisão arquitetural
│
├── prompts/                           ← Prompts prontos para copiar e colar
│   ├── 00-discovery.md                Entrevista que gera PRODUCT.md
│   ├── 01-gerar-product-md.md         Geração do PRODUCT.md a partir da entrevista
│   ├── 02-gerar-claude-md.md          Geração do CLAUDE.md
│   ├── 03-gerar-architecture-md.md    Geração do ARCHITECTURE.md inicial
│   ├── 04-inicio-sessao.md            Toda sessão começa com este
│   ├── 05-pedir-spec.md               Spec densa antes de implementar
│   ├── 06-validacao-contexto.md       Confirmação antes do código
│   ├── 07-implementar.md              Implementação propriamente dita
│   ├── 08-corrigir-bug.md             Diagnóstico antes da correção
│   ├── 09-fim-sessao.md               Toda sessão termina com este
│   ├── 10-revisao-arquitetural.md     Diagnóstico a cada 3-5 features
│   ├── 11-retomar-projeto.md          Voltar de pausa sem reler tudo
│   └── 12-criar-adr.md                Decisão arquitetural duradoura
│
├── templates/                         ← Esqueletos com seções obrigatórias
│   ├── PRODUCT.md.template
│   ├── CLAUDE.md.template
│   ├── ARCHITECTURE.md.template
│   ├── spec.md.template
│   ├── session.md.template
│   └── decision.md.template
│
├── principios/                        ← Por que o trilho é assim
│   ├── clean-code-llm.md              Os 13 princípios de Akita aplicados
│   ├── prompt-engineering.md          Como falar com a IA
│   ├── context-engineering.md         Como gerenciar o que ela vê
│   └── comunicacao-com-usuario.md     Como o agente deve te explicar coisas técnicas
│
└── referencia/                        ← Material de apoio
    ├── estrutura-projeto.md           Estrutura padrão de pastas em todo projeto
    ├── stack-recomendado.md           Stack default e quando desviar
    └── glossario-meta.md              Glossário deste workflow (PRODUCT, ADR, spec, etc)
```

---

## Os 4 documentos vivos de qualquer projeto

Todo projeto que você abrir terá esses 4 documentos. **Eles não são opcionais.** Sem eles, o trilho desmonta.

| Documento | O que é | Quando criar | Quando atualizar |
|---|---|---|---|
| `PRODUCT.md` | Visão de produto e domínio | Fase 0 | Quando produto muda |
| `CLAUDE.md` | Manual de operação do agente | Fase 1 | Quando convenções mudam |
| `ARCHITECTURE.md` | Mapa vivo do sistema | Fase 1 | Final de toda sessão |
| `docs/sessions/[data].md` | Log de cada sessão | A cada sessão | Nunca (é log) |

E mais dois condicionais:

| Documento | Quando criar |
|---|---|
| `docs/specs/[feature].md` | Antes de cada feature |
| `docs/decisions/[tema].md` | Quando uma decisão arquitetural duradoura é tomada |

---

## Os 3 mantras que sustentam o trilho

1. **Toda sessão começa lendo `CLAUDE.md` e `ARCHITECTURE.md`.** Sem exceção.
2. **Toda sessão termina atualizando `ARCHITECTURE.md` e criando log de sessão.** Sem exceção.
3. **Spec antes de código, sempre que a feature toca regra de negócio, dinheiro ou dado.** Atalhos só em UI cosmética.

Se um dia você se pegar pulando os três, pare. Não é vibe coding maduro — é débito técnico em formação.

---

## O princípio operacional

> Você não tem o olho treinado de dev sênior para detectar bug lendo código. O substituto é **observabilidade arquitetural**: documentos vivos, specs, logs e revisões. Esse é o seu mecanismo de controle. Sem ele, você está construindo às cegas.

---

## Próximo passo

Se é a primeira vez que abre este guia: leia `00-trilho-mestre.md` inteiro (15 minutos).

Se já leu: use a árvore de decisão acima.
