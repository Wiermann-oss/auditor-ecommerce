# Referência — Estrutura de Projeto

> Estrutura de pastas padrão. Use em todo projeto. Adaptações pontuais permitidas, mas o esqueleto é fixo.

---

## Esqueleto universal

```
nome-do-projeto/
│
├── CLAUDE.md                    ← Manual do agente
├── ARCHITECTURE.md              ← Mapa vivo do sistema
├── PRODUCT.md                   ← Visão de produto e domínio
├── README.md                    ← Como rodar (curto, aponta para CLAUDE.md)
├── .gitignore
├── .env.example                 ← Variáveis de ambiente sem valores
│
├── docs/
│   ├── specs/                   ← Spec por feature (antes da implementação)
│   │   └── README.md            ← Lista das specs ativas
│   │
│   ├── decisions/               ← ADRs (decisões arquiteturais duradouras)
│   │   └── README.md            ← Índice cronológico de ADRs
│   │
│   └── sessions/                ← Log por sessão (criado ao FIM de cada sessão)
│       └── (sem README — logs são cronológicos)
│
├── src/                         ← Código de aplicação
│   ├── app/                     ← Rotas/pages (Next.js App Router ou similar)
│   ├── components/              ← Componentes UI reutilizáveis (sem domínio)
│   ├── lib/                     ← Utilitários, clientes externos, infra
│   ├── modules/                 ← Módulos de negócio
│   │   └── [nome-modulo]/
│   │       ├── components/      ← Componentes específicos deste módulo
│   │       ├── types.ts         ← Tipos do módulo
│   │       ├── [nome]-service.ts        ← Operações com banco
│   │       ├── [nome]-validators.ts     ← Schemas zod / validação
│   │       ├── [nome]-actions.ts        ← Server actions / endpoints
│   │       └── index.ts         ← Exports públicos do módulo
│   └── types/                   ← Tipos compartilhados
│
├── tests/
│   ├── unit/                    ← Testes unitários (regras de negócio)
│   ├── integration/             ← Testes de integração (módulos + banco)
│   └── e2e/                     ← Testes de ponta a ponta (opcional)
│
└── supabase/                    ← (ou prisma/, drizzle/, etc)
    └── migrations/              ← SQL versionado
```

---

## Regras da estrutura

### 1. Documentos vivos vivem na raiz
`CLAUDE.md`, `ARCHITECTURE.md`, `PRODUCT.md` ficam na raiz. **Não** dentro de `docs/`. Motivo: visibilidade — agentes leem a raiz primeiro.

### 2. Um módulo de negócio = uma pasta em `src/modules/`
Cada módulo do `ARCHITECTURE.md` (seção 2) tem uma pasta correspondente. Mesmo nome, mesma responsabilidade.

### 3. Componentes específicos vivem dentro do módulo
**NÃO** colocar componente específico de "lotes" em `src/components/`. Colocar em `src/modules/lotes/components/`. Reutilizáveis sem domínio (ex: `Button`, `Modal`, `DatePicker`) ficam em `src/components/`.

### 4. Sem regra de negócio em `src/app/`
`app/` é roteamento + UI. Lógica de domínio sempre em `src/modules/`.

### 5. Sem regra de negócio em `src/lib/`
`lib/` é infra (cliente Supabase, helpers de data, formatadores). Sem domínio.

### 6. Sem regra de negócio em componentes UI
Cálculos de KPI, validações, transformações de domínio → no service do módulo. Componente só renderiza.

---

## Por que essa estrutura

| Escolha | Por quê |
|---|---|
| Docs vivos na raiz | Agentes leem antes de entrar em pastas |
| `docs/` separado de `src/` | Documentação não é código — não confunde scanner |
| `modules/` em vez de `features/` | Termo do DDD; força pensar em módulo de negócio, não em "feature solta" |
| Layout fixo dentro do módulo | Previsibilidade — o agente acerta o caminho na primeira tentativa |
| `tests/` paralelo a `src/` | Testes próximos do código que testam, mas não misturados |

---

## Adaptações permitidas

- **Stack diferente:** trocar `supabase/` por `prisma/`, `drizzle/`, `dbt/`, etc. Estrutura interna idêntica.
- **Sem App Router:** `src/app/` vira `src/pages/` ou equivalente. Resto igual.
- **Monorepo:** envolver tudo em `packages/[nome]/` mantendo a estrutura interna.

---

## Adaptações proibidas

- **Misturar `docs/` e `src/`.** Mesmo que sua IDE renderize melhor, não misture.
- **Pastas com nomes genéricos** (`utils/`, `helpers/`, `common/`, `core/`). São lixeiras de código órfão. Substitua por nomes específicos (`date-utils/`, `currency-formatter/`).
- **Variantes do mesmo conceito** com nomes diferentes (`services/` em alguns módulos, `repositories/` em outros). Padronize.

---

## Comando de inicialização

Na Fase 1.3, peça ao Claude:

```
Crie a estrutura de pastas conforme referencia/estrutura-projeto.md
e o ARCHITECTURE.md.

- Crie pastas vazias com .gitkeep onde necessário.
- Crie docs/specs/README.md, docs/decisions/README.md como
  índices vazios.
- NÃO crie nenhum arquivo de código ainda.
- Crie .env.example com placeholders das variáveis necessárias.
- Crie .gitignore apropriado para o stack.

Liste o que criou ao terminar.
```

---

## Manutenção

- Toda nova feature = nova pasta em `src/modules/[nome]/` (a menos que seja extensão de módulo existente).
- Toda nova spec → `docs/specs/[nome].md` + entrada no `docs/specs/README.md`.
- Todo novo ADR → `docs/decisions/YYYY-MM-DD-[tema].md` + entrada no `docs/decisions/README.md`.
- Todo log → `docs/sessions/YYYY-MM-DD-[tema].md` (sem índice — listagem cronológica do filesystem basta).
