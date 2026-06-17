# ARCHITECTURE.md

> Mapa vivo do sistema. Lido em TODA sessão. Atualizado ao FIM de toda sessão.

---

## 1. Visão geral em 1 página

O Auditor é uma ferramenta CLI em Python que executa uma auditoria técnica determinística de uma loja Shopify. Quando rodada, ela percorre as páginas e fluxos críticos configurados em `config/audit-config.yaml` usando um navegador Chromium headless via Playwright. Coleta dois tipos de dados: (A) resultados funcionais — se elementos existem, se cliques funcionam, se o fluxo de compra completa — e (B) dados de saúde técnica — status HTTP, erros de console JavaScript, requisições de rede com falha, e métricas de performance via Lighthouse CLI. Cada verificação produz um `CheckResult` binário (pass/fail) ou com valor numérico comparado a um limiar. Ao final, gera um relatório JSON + HTML em `reports/` e persiste o resultado no histórico SQLite. O operador pode rodar manualmente (`python -m auditor run`) ou configurar execução agendada via GitHub Actions. Não há IA, não há interpretação — toda saída é estruturada e determinística.

---

## 2. Diagrama de módulos

### Lista de módulos

#### config
- **Responsabilidade:** ler, validar e expor a configuração do arquivo YAML como objetos tipados
- **Depende de:** PyYAML, Pydantic
- **Quem depende:** engine
- **Estado:** planejado

#### engine
- **Responsabilidade:** orquestrar a execução de uma auditoria completa (coordena layers, storage e reporters)
- **Depende de:** config, layers, storage, reporters, types
- **Quem depende:** cli
- **Estado:** planejado

#### layer-a
- **Responsabilidade:** verificação funcional dos fluxos (navegação, cliques, asserções de fluxo, popups)
- **Depende de:** Playwright, types, config
- **Quem depende:** engine
- **Estado:** planejado

#### layer-b
- **Responsabilidade:** saúde técnica das páginas (HTTP status, JS errors, network failures, performance via Lighthouse)
- **Depende de:** Playwright, Lighthouse CLI (subprocess), types, config
- **Quem depende:** engine
- **Estado:** planejado

#### storage
- **Responsabilidade:** persistir AuditRun e CheckResult no SQLite; consultar histórico para comparação temporal
- **Depende de:** sqlite3 (stdlib), types
- **Quem depende:** engine, cli (para diff)
- **Estado:** planejado

#### reporters
- **Responsabilidade:** gerar relatório JSON e HTML a partir dos resultados de uma auditoria
- **Depende de:** Jinja2, types
- **Quem depende:** engine
- **Estado:** planejado

#### cli
- **Responsabilidade:** entry point Typer — parse de argumentos, chamada ao engine ou ao storage
- **Depende de:** Typer, engine, storage
- **Quem depende:** ninguém (é o topo)
- **Estado:** planejado

### Diagrama (ASCII)

```
[cli]
  |
  ├──→ [engine]
  │       |
  │       ├──→ [config]         (lê audit-config.yaml)
  │       ├──→ [layer-a]        (fluxos funcionais via Playwright)
  │       ├──→ [layer-b]        (saúde técnica via Playwright + Lighthouse)
  │       ├──→ [storage]        (persiste no SQLite)
  │       └──→ [reporters]      (gera JSON + HTML)
  │
  └──→ [storage]                (consulta direta para diff/histórico)

[layer-a] e [layer-b] → produzem → [types.CheckResult]
[engine] → agrega → [types.AuditRun]
[reporters] → consome → [types.AuditRun + list[CheckResult]]
```

---

## 3. Entidades e modelo de dados

### audit_runs
| Coluna | Tipo | Obrigatório | Default | Notas |
|---|---|---|---|---|
| id | TEXT | sim | UUID v4 | PK |
| started_at | TEXT | sim | — | ISO 8601 UTC |
| finished_at | TEXT | não | null | ISO 8601 UTC; null se abortou |
| status | TEXT | sim | — | 'success' \| 'partial' \| 'failed' |
| trigger | TEXT | sim | — | 'manual' \| 'scheduled' |
| config_snapshot | TEXT | sim | — | JSON serializado do config usado |
| total_checks | INTEGER | não | null | preenchido ao final |
| total_pass | INTEGER | não | null | preenchido ao final |
| total_fail | INTEGER | não | null | preenchido ao final |

- **Soft delete:** não (histórico é append-only, nunca apagar)
- **Invariantes:**
  - `total_pass + total_fail = total_checks` quando `finished_at` não é null
  - `status = 'failed'` quando `finished_at` é null (auditoria abortada)

### check_results
| Coluna | Tipo | Obrigatório | Default | Notas |
|---|---|---|---|---|
| id | TEXT | sim | UUID v4 | PK |
| audit_run_id | TEXT | sim | — | FK → audit_runs.id |
| check_name | TEXT | sim | — | ex: 'http_status', 'js_errors', 'add_to_cart_flow' |
| layer | TEXT | sim | — | 'A' \| 'B' |
| scope_type | TEXT | sim | — | 'page' \| 'flow' |
| scope_url | TEXT | não | null | URL da página (se scope_type = 'page') |
| scope_flow | TEXT | não | null | nome do fluxo (se scope_type = 'flow') |
| viewport | TEXT | sim | — | 'desktop' \| 'mobile' |
| result | TEXT | sim | — | 'pass' \| 'fail' |
| value | REAL | não | null | valor numérico (ex: load_time_ms = 2340) |
| threshold | REAL | não | null | limiar configurado (ex: 5000) |
| error_detail | TEXT | não | null | detalhe técnico do erro; null se pass |
| duration_ms | INTEGER | não | null | tempo de execução da checagem |
| created_at | TEXT | sim | — | ISO 8601 UTC |

- **Chaves estrangeiras:** `audit_run_id → audit_runs.id`
- **Índices:** `(audit_run_id)`, `(check_name, result)`, `(scope_url, check_name)`
- **Soft delete:** não (imutável após criação)
- **Invariantes:**
  - `error_detail` deve ser não-nulo quando `result = 'fail'`
  - `scope_url` ou `scope_flow` deve estar preenchido (não ambos nulos)

---

## 4. Fluxos de dados

### Fluxo 1 — Execução de auditoria completa (`auditor run`)

1. **Trigger:** `python -m auditor run` (manual) ou GitHub Actions (agendado)
2. **Função que recebe:** `cli.py → app command "run"` → chama `engine.run_audit(config)`
3. **Validações:**
   - `config/loader.py` valida o YAML via Pydantic; erro com campo e valor se inválido
   - Verifica que todas as URLs no config são acessíveis (timeout 10s); aborta com `status='failed'` se home inacessível
4. **Operações em ordem:**
   - Cria `AuditRun` em `audit_runs` com `started_at` e `status='running'`
   - Para cada `CriticalPage` × `Viewport`: chama `layer_b.run_page_health_checks()` → insere N `CheckResult` em `check_results`
   - Para cada `Flow` × `Viewport`: chama `layer_a.run_flow()` → insere N `CheckResult` em `check_results`
   - Atualiza `AuditRun` com `finished_at`, `status`, totais
5. **Resposta para o usuário:**
   - Terminal: `✓ 47 checagens | ✗ 2 falhas | Relatório: reports/2026-06-17T09-00-00.html`
   - Arquivos: `reports/[timestamp].json` + `reports/[timestamp].html`
6. **Side effects:** nenhum externo (tudo local)

### Fluxo 2 — Comparação temporal (`auditor diff`)

1. **Trigger:** `python -m auditor diff --since 7d`
2. **Função que recebe:** `cli.py → app command "diff"` → chama `storage.history.get_diff(since=7d)`
3. **Validações:**
   - Verifica que há ao menos 2 auditorias no período
4. **Operações em banco (em ordem):**
   - Consulta `audit_runs` no período → ordena por `started_at`
   - Para cada par (anterior, posterior): compara `check_results` por `check_name + scope_url/flow + viewport`
   - Identifica: regressões (pass→fail), recuperações (fail→pass), novidades (check_name novo)
5. **Resposta para o usuário:** tabela no terminal com delta; opcional JSON em `reports/diff-[range].json`

### Fluxo 3 — Checagem de página (Camada B interna)

1. **Trigger:** chamado pelo engine para cada `CriticalPage × Viewport`
2. **Função:** `layer_b.run_page_health_checks(page, critical_page, viewport) → list[CheckResult]`
3. **Checagens executadas em ordem:**
   - `check_http_status`: navega para a URL, verifica `response.status == 200`
   - `check_console_errors`: captura eventos `console.error` durante o carregamento
   - `check_failed_requests`: captura eventos `requestfailed` e responses com status ≥ 400
   - `check_unloaded_resources`: verifica imagens, scripts, CSS com status de falha
   - `check_load_time`: mede via Navigation Timing API (`loadEventEnd - fetchStart`)
   - `check_lighthouse_metrics`: executa `lighthouse [url] --output=json` via subprocess; extrai LCP, CLS, FID
4. **Cada checagem retorna:** um `CheckResult` com `result`, `value`, `threshold`, `error_detail`

### Fluxo 4 — Verificação de fluxo (Camada A interna)

1. **Trigger:** chamado pelo engine para cada `Flow × Viewport`
2. **Função:** `layer_a.run_flow(browser, flow, viewport) → list[CheckResult]`
3. **Execução:** para cada `Step` no fluxo em ordem:
   - Executa a ação (goto, click, fill, wait_for)
   - Verifica a asserção (url_contains, element_visible, element_clickable)
   - Registra `StepResult` (pass/fail + error_detail)
   - Se step falha e `abort_on_failure=true`: encerra o fluxo, marca steps restantes como `skipped`
4. **Popup handling:** antes de cada step de fluxo crítico, tenta fechar popups conhecidos

---

## 5. Decisões arquiteturais já tomadas

| Data | Decisão | Por quê | Impede no futuro | ADR |
|---|---|---|---|---|
| 2026-06-17 | Python (não Node/TS) | Projeto é automação/CLI, não web app; Python é mais direto para scripting e tem suporte Playwright excelente | Dificulta integrar com uma futura dashboard Next.js no mesmo repo | — |
| 2026-06-17 | SQLite para histórico | Arquivo único, sem servidor, consultável com SQL, portátil; suficiente para volume de uma loja | Se histórico crescer para anos de dados diários com múltiplas lojas, migrar para Postgres | — |
| 2026-06-17 | Playwright (não Puppeteer/Selenium) | API moderna, suporte nativo a Python, CDP integrado para network/console, viewport mobile nativo | — | — |
| 2026-06-17 | Lighthouse via subprocess CLI | Lighthouse Python não é oficial; CLI é o padrão de mercado e mais estável | Depende de Node/npm no ambiente de execução além do Python | — |
| 2026-06-17 | YAML para config | Mais legível para não-programadores; suporta comentários (JSON não suporta); padrão para configs de CI | — | — |
| 2026-06-17 | Relatório JSON + HTML (sem dashboard) | HTML cobre 100% do caso de uso v1 sem backend; JSON garante processabilidade futura | — | — |

---

## 6. Pontos frágeis conhecidos

### Popups dinâmicos (temporização variável)
- **Onde:** `layer_a.py` → popup_checker
- **Por que é frágil:** popups de newsletter disparam com delay (ex: 3s após entrada); se o step do fluxo executa antes do delay, o popup não é testado; se executa depois, pode bloquear o step
- **O que vai estourar primeiro:** falsos negativos (popup não detectado) ou fluxo travado por popup não fechado
- **Plano:** aguardar X segundos configurável por popup; reavaliar se os delays do popup mudarem

### Seletores CSS hardcoded nos fluxos
- **Onde:** `config/audit-config.yaml` → steps → selector
- **Por que é frágil:** se o tema da loja mudar (atualização, redesign), seletores quebram silenciosamente ou com erro de timeout
- **O que vai estourar primeiro:** step com `TimeoutError` em seletor que não existe mais
- **Plano:** aceitar e monitorar; quando step falhar, atualizar o config

### Lighthouse via subprocess
- **Onde:** `layer_b.py` → `check_lighthouse_metrics`
- **Por que é frágil:** Lighthouse pode ter saída JSON com estrutura diferente entre versões; subprocess pode falhar sem retornar código de erro claro
- **O que vai estourar primeiro:** `KeyError` no parse do JSON do Lighthouse após upgrade
- **Plano:** parsear o JSON do Lighthouse de forma defensiva (`.get()` com fallback); verificar versão na inicialização

---

## 7. Inventário de arquivos críticos

| Caminho | Responsabilidade | Quem deve mexer | Quem NÃO deve mexer |
|---|---|---|---|
| config/audit-config.yaml | Única fonte de configuração editável pelo operador | operador/dev com cuidado | engine (só lê, nunca escreve) |
| src/auditor/types.py | Contratos de dados do sistema (CheckResult, AuditRun, etc.) | Claude com cautela — mudança quebra tudo | qualquer outro módulo sem atualizar storage e reporters |
| src/auditor/storage/history.py | Schema SQLite e migrações | Claude com ADR antes | ninguém sem planejar migração |
| src/auditor/engine.py | Orquestração central | Claude com spec antes | ninguém sem entender o fluxo completo |
