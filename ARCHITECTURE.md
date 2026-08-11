# ARCHITECTURE.md

> Mapa vivo do sistema. Lido em TODA sessão. Atualizado ao FIM de toda sessão.

---

## 1. Visão geral em 1 página

O Auditor é uma ferramenta CLI em Python que executa uma auditoria técnica determinística de uma loja Shopify. Quando rodada, ela percorre as páginas e fluxos críticos configurados em `config/audit-config.yaml` (a lista de páginas é substituída por `config/pages.yaml` quando esse arquivo existe — ver `config/loader.py::_merge_pages`) usando um navegador Chromium headless via Playwright. Coleta dois tipos de dados: (A) resultados funcionais — se elementos existem, se cliques funcionam, se o fluxo de compra completa — e (B) dados de saúde técnica — status HTTP, erros de console JavaScript, requisições de rede com falha, e métricas de performance via Lighthouse CLI. Cada verificação produz um `CheckResult` binário (pass/fail) ou com valor numérico comparado a um limiar. Ao final, gera um relatório JSON + HTML em `reports/` e persiste o resultado no histórico SQLite. Não há IA, não há interpretação — toda saída é estruturada e determinística.

**Estado real em produção (atualizado 2026-08-11):** o auditor roda diariamente e sem intervenção via GitHub Actions (`.github/workflows/audit.yml`, cron configurável pelo dashboard) desde 19/06/2026 — 63+ execuções até a data desta atualização. Cada execução publica na branch `gh-pages`, servida como dashboard estático em `wiermann-oss.github.io/auditor-ecommerce` (gerado por `scripts/publish_pages.py`): última execução, histórico completo, cobertura (páginas/fluxos/popups ativos, editável via workflows do GitHub Actions sem tocar em código) e análise de tendência. Existe também um dashboard local (`python -m auditor server`, FastAPI + APScheduler) para uso manual/ad-hoc — é um mecanismo de agendamento separado do cron do GitHub Actions, só ativo enquanto o processo local estiver rodando.

---

## 2. Diagrama de módulos

### Lista de módulos

#### config
- **Responsabilidade:** ler, validar e expor a configuração do arquivo YAML como objetos tipados
- **Depende de:** PyYAML, Pydantic
- **Quem depende:** engine
- **Estado:** implementado — em produção

#### engine
- **Responsabilidade:** orquestrar a execução de uma auditoria completa (coordena layers, storage e reporters)
- **Depende de:** config, layers, storage, reporters, types
- **Quem depende:** cli
- **Estado:** implementado — em produção

#### layer-a
- **Responsabilidade:** verificação funcional dos fluxos (navegação, cliques, asserções de fluxo, popups)
- **Depende de:** Playwright, types, config
- **Quem depende:** engine
- **Estado:** implementado — em produção

#### layer-b
- **Responsabilidade:** saúde técnica das páginas (HTTP status, JS errors, network failures, performance via Lighthouse)
- **Depende de:** Playwright, Lighthouse CLI (subprocess), types, config
- **Quem depende:** engine
- **Estado:** implementado — em produção

#### popup-checker
- **Responsabilidade:** checagens dedicadas do popup de captura Klaviyo (dispara, fecha, não bloqueia scroll/clique, não aparece no checkout, não reaparece em loop)
- **Depende de:** Playwright, types, config, `_screenshot.dismiss_known_popups`
- **Quem depende:** engine
- **Estado:** implementado — em produção. Checagem "dispara após delay" falha com frequência em produção (ver seção 6) e derruba em cascata as demais checagens do popup via `_skip_remaining`

#### server (dashboard local)
- **Responsabilidade:** FastAPI + APScheduler — dashboard web local (`python -m auditor server`), API para disparar auditoria manual, editar overrides de páginas/fluxos ativos, configurar agendamento local e GA4
- **Depende de:** FastAPI, uvicorn, APScheduler, engine, storage, config
- **Quem depende:** ninguém (é um entry point alternativo ao cli)
- **Estado:** implementado. Mecanismo de agendamento **separado** do cron do GitHub Actions — só ativo enquanto o processo estiver rodando na máquina local

#### scripts (automação de publicação)
- **Responsabilidade:** `publish_pages.py` gera o dashboard estático publicado em `gh-pages` a cada execução do workflow; `manage_pages.py` edita `config/pages.yaml` via workflow_dispatch; `update_schedule.py` reescreve o cron de `.github/workflows/audit.yml`
- **Depende de:** PyYAML, storage (para ler o histórico)
- **Quem depende:** workflows do GitHub Actions (`audit.yml`, `manage-pages.yml`, `sync-pages.yml`, `update-schedule.yml`)
- **Estado:** implementado — em produção

#### storage
- **Responsabilidade:** persistir AuditRun e CheckResult no SQLite; consultar histórico para comparação temporal
- **Depende de:** sqlite3 (stdlib), types
- **Quem depende:** engine, cli (para diff)
- **Estado:** implementado — em produção

#### reporters
- **Responsabilidade:** gerar relatório JSON e HTML a partir dos resultados de uma auditoria
- **Depende de:** Jinja2, types
- **Quem depende:** engine
- **Estado:** implementado — em produção

#### cli
- **Responsabilidade:** entry point Typer — parse de argumentos, chamada ao engine ou ao storage
- **Depende de:** Typer, engine, storage
- **Quem depende:** ninguém (é o topo)
- **Estado:** implementado — em produção

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
| run_id | TEXT | sim | UUID v4 | PK |
| started_at | TEXT | sim | — | ISO 8601 UTC |
| finished_at | TEXT | não | null | ISO 8601 UTC; null enquanto em_andamento |
| status | TEXT | sim | 'em_andamento' | **Eixo 1 — saúde do job:** 'em_andamento' \| 'concluida' \| 'falhou' \| 'cancelada' |
| resultado | TEXT | não | null | **Eixo 2 — saúde da loja:** 'tudo_ok' \| 'com_falhas'; null quando status ≠ 'concluida' |
| trigger | TEXT | sim | — | 'manual' \| 'agendado' |
| config_version | TEXT | sim | — | MD5 do audit-config.yaml usado (reprodutibilidade) |
| execution_error | TEXT | não | null | detalhe técnico se status = 'falhou' |
| total_checks | INTEGER | não | null | preenchido ao finalizar |
| total_passou | INTEGER | não | null | preenchido ao finalizar |
| total_falhou | INTEGER | não | null | preenchido ao finalizar |
| total_erro | INTEGER | não | null | checagens que não conseguiram rodar |

- **Soft delete:** não (histórico é append-only; nunca apagar)
- **Invariantes:**
  - `status` e `resultado` são independentes: uma execução pode ter `status='concluida'` com `resultado='com_falhas'` (auditor rodou, loja tem problema) ou `status='falhou'` com `resultado=null` (auditor quebrou, nada se sabe da loja)
  - `resultado` só é preenchido quando `status = 'concluida'`
  - `total_passou + total_falhou + total_erro = total_checks` quando `status = 'concluida'`

### check_results
| Coluna | Tipo | Obrigatório | Default | Notas |
|---|---|---|---|---|
| id | TEXT | sim | UUID v4 | PK |
| run_id | TEXT | sim | — | FK → audit_runs.run_id |
| check_id | TEXT | sim | — | identificador estável para comparação histórica (ex: 'http_status') |
| check_name | TEXT | sim | — | nome legível (ex: 'Status HTTP — Home') |
| categoria | TEXT | sim | — | 'fluxo' \| 'saude_tecnica' (nunca 'Camada A/B' no dado armazenado) |
| page_url | TEXT | não | null | URL absoluta da página verificada |
| flow_name | TEXT | não | null | nome do fluxo (se categoria = 'fluxo') |
| viewport | TEXT | sim | — | 'desktop' \| 'mobile' |
| status | TEXT | sim | — | 'passou' \| 'falhou' \| 'erro' |
| detail | TEXT | não | null | detalhe técnico; obrigatório quando status ≠ 'passou' |
| value | REAL | não | null | valor numérico da métrica (ex: 2340) |
| unit | TEXT | não | null | unidade da métrica (ex: 'ms', 'count', 'score') |
| threshold | REAL | não | null | limiar usado na checagem (preservado para comparação futura honesta) |
| duration_ms | INTEGER | não | null | tempo de execução da checagem em ms |
| created_at | TEXT | sim | — | ISO 8601 UTC |

- **Chaves estrangeiras:** `run_id → audit_runs.run_id`
- **Índices:** `(run_id)`, `(check_id, status)`, `(page_url, check_id)`
- **Soft delete:** não (imutável após criação — append-only)
- **Distinção de status:**
  - `'passou'`: checagem executou e o valor está dentro do esperado
  - `'falhou'`: checagem executou e encontrou problema na loja — investigar a loja
  - `'erro'`: checagem não conseguiu executar (seletor sumiu, timeout de config) — investigar o auditor/config
- **Invariantes:**
  - `detail` deve ser não-nulo quando `status ∈ {'falhou', 'erro'}`
  - `page_url` ou `flow_name` deve estar preenchido (não ambos nulos)

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
| 2026-06-19 | Dashboard estático em GitHub Pages (não o dashboard local) como interface principal do operador | Roda em nuvem, não depende da máquina local ligada; publicável via workflow já existente | Toda mudança de UI passa por commit+push, não é um app vivo | — |
| 2026-08-11 | `config/pages.yaml` substitui `critical_pages` do audit-config.yaml quando existe | Permite ao operador editar a lista de páginas pelo editor web do GitHub, sem tocar em YAML de fluxo/threshold | `critical_pages` no audit-config.yaml fica morto/decorativo assim que pages.yaml existe — fonte de confusão, documentar sempre que alguém for mexer na lista de páginas | — |
| 2026-08-11 | Espera de popup como `wait` step no config (não timeout maior no `dismiss_known_popups`) | Um timeout maior no dismiss rodaria em CADA clique do fluxo, inflando o tempo de execução mesmo após o popup já fechado; o wait step roda uma vez só, no início do fluxo | Precisa ser adicionado manualmente em cada fluxo vulnerável — não é automático para fluxos novos | — |
| 2026-08-11 | F4 ancorado em página de produto (`/products/camisa-minimal-overshirt`), não em coleção | A pedido do operador: fluxos devem funcionar a partir de página de produto real, alinhados com o que participa da auditoria de saúde técnica (`config/pages.yaml`); a coleção `desconto-progressivo-1` tem UX de kit-builder (modal), incompatível com o padrão de clique-e-navega | Se o produto `camisa-minimal-overshirt` for desativado/descontinuado, o F4 quebra — precisa atualizar a URL junto | — |

---

## 6. Pontos frágeis conhecidos

### Popups dinâmicos (temporização variável) — quantificado em 2026-08-11
- **Onde:** `layers/_screenshot.py::dismiss_known_popups`, `layers/popup_checker.py`, `audit-config.yaml` (wait steps de F1/F3/F8/F4)
- **Por que é frágil:** medido em produção (headed + headless, com vídeo de evidência): o popup Klaviyo leva **6-8s** para aparecer — bem mais que os 4.5s do `popup_delay` configurado. Um `dismiss_known_popups` chamado cedo demais conclui "sem popup" e o clique real seguinte cai na janela em que o popup está terminando de renderizar, sendo recusado pelo Playwright como "subtree intercepts pointer events" (falso positivo — confirmado com clique físico de mouse nas mesmas coordenadas, que funciona normalmente)
- **O que já estourou:** cascata de falhas em F1/F2/F3/F4/F6/F7/F8 — a maioria dos `erro` do relatório eram passos pulados por `abort_on_failure`, não problemas reais da loja
- **Mitigação aplicada:** wait step de 8000ms uma vez no início de cada fluxo vulnerável (F1, F3, F4, F8 — commitados); `dismiss_known_popups` usa `mouse.click` em vez de `locator.click` e espera `state=hidden` antes de prosseguir; retry genérico de clique em `layer_a.py` quando o `expect` falha
- **Ainda aberto:** F2 e F6 resolvidos só no mobile (desktop ainda falha às vezes — 8s nem sempre é suficiente); F7 (mobile) ainda falha. `popup_checker.py`'s "dispara após delay" falha com frequência em produção mesmo com 4.5s de espera própria — mesma causa raiz, ainda não corrigido lá
- **Plano:** considerar aumentar o wait para ~10-12s, ou passar `config.timeouts.popup_delay` para `dismiss_known_popups` como fonte única de verdade em vez de constante hardcoded

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

### `layer_a.py` não tem retry-on-429 (assimetria com `layer_b.py`)
- **Onde:** `layers/layer_a.py::_perform_action`, caso `ActionType.GOTO`
- **Por que é frágil:** `layer_b.py::_goto_with_retry` já trata HTTP 429 com backoff; o `goto` de um fluxo não tem equivalente — uma navegação dentro de um fluxo que bate rate-limit falha direto, sem segunda chance
- **O que vai estourar primeiro:** execuções manuais/testes com muitos requests seguidos contra a loja em pouco tempo (visto em 2026-08-11: dezenas de execuções de diagnóstico na mesma sessão pareceram acionar proteção do Cloudflare, impedindo validação contínua do F4)
- **Plano:** avaliar extrair `_goto_with_retry` para um helper compartilhado entre `layer_a.py` e `layer_b.py`

---

## 7. Inventário de arquivos críticos

| Caminho | Responsabilidade | Quem deve mexer | Quem NÃO deve mexer |
|---|---|---|---|
| config/audit-config.yaml | Fonte de configuração de thresholds, popups e fluxos. **Atenção:** o bloco `critical_pages` é ignorado sempre que `config/pages.yaml` existir | operador/dev com cuidado | engine (só lê, nunca escreve) |
| config/pages.yaml | Fonte **real** da lista de páginas auditadas em saúde técnica quando presente — substitui `critical_pages` por inteiro (`config/loader.py::_merge_pages`) | operador (via editor web do GitHub, botão no dashboard) | engine (só lê, nunca escreve) |
| src/auditor/types.py | Contratos de dados do sistema (CheckResult, AuditRun, etc.) | Claude com cautela — mudança quebra tudo | qualquer outro módulo sem atualizar storage e reporters |
| src/auditor/storage/history.py | Schema SQLite e migrações | Claude com ADR antes | ninguém sem planejar migração |
| src/auditor/engine.py | Orquestração central | Claude com spec antes | ninguém sem entender o fluxo completo |
| src/auditor/layers/_screenshot.py | Screenshot de evidência + `dismiss_known_popups` (usado por layer_a, layer_b e no retry de clique) | Claude com cuidado — mudança afeta timing de todos os fluxos | ninguém sem rodar validação real contra a loja (não só unitária) |
