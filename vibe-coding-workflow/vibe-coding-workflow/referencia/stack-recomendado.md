# Referência — Stack Recomendado

> Default para novos projetos. Use a menos que tenha motivo concreto para desviar. Cobre 80% dos casos de SaaS / dashboard / ferramenta interna.

---

## Stack default ("indie hacker SaaS 2025/2026")

| Camada | Tecnologia | Versão | Motivo |
|---|---|---|---|
| Framework | **Next.js** | 14+ App Router | Mais documentado; melhor combinação SSR/SSG/server actions; agentes conhecem bem |
| Linguagem | **TypeScript** | 5+ estrito | Type checker substitui parte da revisão de dev sênior |
| Banco | **Supabase** (Postgres) | última | Postgres gerenciado + auth + storage + RLS pronto |
| ORM/Cliente | **supabase-js** + tipos gerados | última | Tipos auto-gerados a partir do schema |
| UI | **Tailwind CSS** | 3+ | Documentação massiva; agentes geram bem |
| Componentes | **shadcn/ui** | última | Componentes copy-paste, ownership total, sem lock-in |
| Validação | **Zod** | 3+ | Schemas tipados; integra com TS |
| Forms | **react-hook-form** + zod | última | Validação no client + server |
| Estado servidor | **TanStack Query** (opcional) | última | Cache + invalidação; usar só se UI precisa |
| Datas | **date-fns** | 3+ | Tree-shakeable; nunca moment |
| Deploy | **Vercel** | — | Zero config para Next.js |
| Auth | **Supabase Auth** | — | Magic link, OAuth, 2FA prontos |
| Pagamento (se aplicável) | **Stripe** | — | Padrão de mercado, docs excelentes |
| Observabilidade | **Sentry** + Vercel logs | última | Erro client + server |
| Testes | **Vitest** + **Playwright** | última | Vitest unit/integration, Playwright e2e |
| Lint/Format | **ESLint** + **Prettier** | última | Config padrão do Next.js como base |

---

## Por que esse stack

### 1. Densidade de documentação
Agentes (Claude incluído) foram treinados em massa de exemplos com esse stack. Resultado: menos alucinação, mais código que funciona na primeira tentativa.

### 2. Composição mínima de complexidade
Cada peça é a mais "padrão" da sua categoria. Você não está aprendendo uma stack — está usando o vocabulário comum.

### 3. Ownership total do que importa
shadcn/ui copia componente para o seu projeto, em vez de instalar dependência opaca. Você consegue ler e ajustar (ou pedir ao agente que ajuste).

### 4. RLS no banco como camada de segurança
Em vez de centralizar autorização em código (frágil, esquecível), Postgres RLS aplica regras na fronteira. Agente esquece, banco aplica.

### 5. Server actions reduzem camadas
Em vez de "API routes + cliente HTTP + tipos compartilhados", server actions chamam função tipada do cliente. Menos código, menos bug, menos contexto.

---

## Quando desviar

### Trocar Next.js por outro framework
- **Use Astro** se for site mais conteúdo + pouca interação dinâmica.
- **Use Remix** se já tiver experiência e preferir loaders/actions explícitos.
- **Use SvelteKit** só se for projeto pessoal e você quer aprender Svelte.
- **NÃO use** Express/Fastify puro para SaaS — perde produtividade gigante.

### Trocar Supabase por outro banco
- **Use Neon + Drizzle** se quiser Postgres mais "puro" + ORM com tipos gerados.
- **Use Convex** só se time-real reativo é central (pouco comum).
- **NÃO use** MongoDB sem motivo claro de modelagem documental — Postgres cobre 95% dos casos.

### Trocar Tailwind/shadcn
- Não troque. Custo/benefício piora em qualquer alternativa para esse perfil.

### Adicionar coisas
Antes de adicionar dependência, pergunte:
1. Há alternativa mais simples já no stack?
2. Vou usar isso em mais de 1 lugar?
3. Vou conseguir ler o código que ela gera?

Se "não" para qualquer pergunta → não adicione.

---

## O que NÃO entra na v1

Lista de coisas que parecem boas ideias e atrasam projeto pessoal sem necessidade:

- **Microserviços.** Tudo num projeto Next.js até 50k linhas.
- **Kubernetes / Docker complexo.** Vercel resolve.
- **GraphQL.** Server actions resolvem com menos cerimônia.
- **Redux / state managers globais.** TanStack Query + URL state cobre 90%.
- **CI/CD elaborado.** Vercel + GitHub default cobre.
- **Storybook.** A menos que seja design system real.
- **Multi-language do zero.** Se não há demanda confirmada, atrasa.

---

## Variáveis de ambiente padrão

Em `.env.example`:

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# App
NEXT_PUBLIC_APP_URL=http://localhost:3000

# Sentry (opcional)
SENTRY_DSN=
SENTRY_AUTH_TOKEN=
```

---

## Comandos padrão (para o `CLAUDE.md` seção 8)

```bash
# Setup
pnpm install
cp .env.example .env.local
supabase start
supabase db reset

# Dev
pnpm dev

# Validação
pnpm typecheck
pnpm lint
pnpm test

# Migrations
supabase migration new [nome]
supabase db reset    # aplica todas as migrations

# Deploy
git push    # Vercel detecta e faz deploy
```

---

## Stack alternativo para automação / scripts

Se o projeto não é SaaS/web, e sim **script de automação ou ferramenta CLI** (como o `shopify_specialist` deste workspace):

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ |
| Tipos | Type hints + mypy |
| Lint/Format | ruff + black |
| Testes | pytest |
| HTTP | requests ou httpx |
| Validação | pydantic |
| CLI | typer ou click |
| Config | python-dotenv |

Resto do trilho continua valendo (PRODUCT.md, CLAUDE.md, ARCHITECTURE.md, specs, sessions, decisions).

---

## Mantra

> Stack default não é "o melhor stack" — é o **mais legível por agentes e mais documentado**. Para vibe coding, isso vale mais do que qualquer microvantagem técnica.
