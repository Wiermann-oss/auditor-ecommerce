# CLAUDE.md

> Manual de operação do agente neste projeto. Lido em TODA sessão. Atualizado quando convenções mudam.

---

## 1. Stack e versões

| Camada | Tecnologia | Versão | Papel |
|---|---|---|---|
| Linguagem | Python | 3.11+ | Runtime principal |
| Automação de navegador | Playwright (Python) | 1.40+ | Camadas A e B — browser automation |
| Performance | Lighthouse CLI | última | Core Web Vitals via CLI |
| Banco local | SQLite (via sqlite3 stdlib) | — | Histórico de auditorias |
| Validação de config | Pydantic | 2+ | Parse e validação do YAML de config |
| Config | PyYAML | 6+ | Leitura do audit-config.yaml |
| CLI | Typer | 0.9+ | Interface de linha de comando |
| Tipos | mypy (type hints nativos) | 1+ | Verificação estática |
| Lint/Format | ruff + black | última | Lint e formatação |
| Testes | pytest + pytest-asyncio | última | Testes unitários e de integração |
| Templates HTML | Jinja2 | 3+ | Geração do relatório HTML |

### Bibliotecas permitidas por tipo de problema
- **HTTP requests diretos:** httpx (se necessário além do Playwright)
- **Datas:** datetime (stdlib). NUNCA dateutil sem motivo.
- **JSON:** json (stdlib)
- **Paths:** pathlib.Path. NUNCA os.path.

### Bibliotecas proibidas
- **requests** — usar httpx se precisar de HTTP fora do Playwright
- **BeautifulSoup** — o Playwright já acessa o DOM; não fazer scraping manual

---

## 2. Convenções de código

### Nomenclatura
- **Arquivos:** snake_case com sufixo de responsabilidade (ex: `flow_runner.py`, `page_health_checker.py`, `html_reporter.py`)
- **Funções:** verbo + objeto específico. NUNCA `handle_*`, `process_*`, `manage_*` genéricos.
- **Variáveis:** sem abreviações (`check_result` ✓; `cr` ✗; `res` ✗)
- **Booleans:** prefixo `is_`, `has_`, `can_`, `should_`
- **Constantes:** SCREAMING_SNAKE_CASE apenas para constantes globais imutáveis
- **Classes:** PascalCase

### Tamanho
- Função: 5 a 25 linhas. Se passar, divida.
- Arquivo: até 400 linhas. Se passar, divida por responsabilidade.
- Indentação: máximo 2 níveis de if/for aninhados. Use early returns e funções auxiliares.

### Tipos
- Sempre explícitos em parâmetros e retornos (`def run_check(url: str) -> CheckResult:`).
- Nunca `Any` sem comentário explicando o porquê.
- Modelos de dados sempre como `dataclass` ou `pydantic.BaseModel`, nunca `dict` solto.

### Erros
- Mensagem inclui o valor que causou o problema e o que era esperado.
- Exemplo: `CheckError: botão '#add-to-cart' não encontrado em https://loja.com/products/foo após 5000ms`
- Nunca catch silencioso — sempre re-raise ou log estruturado + raise.

### Async
- Playwright é async. Toda função que usa Playwright deve ser `async def`.
- Não misturar sync e async no mesmo módulo sem necessidade clara.
- Entry point do CLI usa `asyncio.run()` para entrar no loop.

---

## 3. Estrutura de pastas obrigatória

```
auditor-ecommerce/
├── CLAUDE.md
├── ARCHITECTURE.md
├── PRODUCT.md
├── README.md
├── .gitignore
├── .env.example
├── pyproject.toml               ← dependências + config de ferramentas
│
├── config/
│   └── audit-config.yaml        ← ÚNICO arquivo que o operador edita
│
├── docs/
│   ├── specs/                   ← spec por feature antes de implementar
│   │   └── README.md
│   ├── decisions/               ← ADRs
│   │   └── README.md
│   └── sessions/                ← log por sessão
│
├── reports/                     ← relatórios gerados (JSON + HTML), não versionados
│
├── src/
│   └── auditor/
│       ├── __init__.py
│       ├── cli.py               ← entry point Typer
│       ├── engine.py            ← orquestra a auditoria completa
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   ├── loader.py        ← lê e valida audit-config.yaml via Pydantic
│       │   └── models.py        ← modelos Pydantic do config
│       │
│       ├── layers/
│       │   ├── __init__.py
│       │   ├── layer_a.py       ← Camada A: verificação funcional dos fluxos
│       │   ├── layer_b.py       ← Camada B: saúde técnica das páginas
│       │   └── popup_checker.py ← checagens específicas de popup
│       │
│       ├── reporters/
│       │   ├── __init__.py
│       │   ├── json_reporter.py ← gera relatório JSON
│       │   └── html_reporter.py ← gera relatório HTML via Jinja2
│       │
│       ├── storage/
│       │   ├── __init__.py
│       │   └── history.py       ← persistência SQLite
│       │
│       └── types.py             ← dataclasses: AuditRun, CheckResult, etc.
│
└── tests/
    ├── unit/                    ← testes de lógica pura (sem browser)
    └── integration/             ← testes com browser real (Playwright)
```

**O que NÃO vai em cada pasta:**
- `cli.py`: nenhuma lógica de negócio. Só parse de args e chamada ao engine.
- `engine.py`: nenhuma lógica de checagem. Só orquestração.
- `layers/`: nenhuma lógica de relatório ou persistência.
- `config/`: nenhuma lógica de execução.
- `reporters/`: nenhuma lógica de checagem.

---

## 4. Regras invioláveis

### R1. Todas as checagens são determinísticas e binárias (ou numéricas).
- **Motivo:** o princípio central do sistema. Nenhuma fonte de subjetividade.
- **Violação:** qualquer checagem que dependa de julgamento humano ou de IA.

### R2. Nenhuma checagem escreve dados na loja ou submete transações reais.
- **Motivo:** o sistema é somente leitura. Checkout vai até a etapa de confirmação de dados, nunca submete pagamento.
- **Violação:** formulário submetido, pedido criado, pagamento processado.

### R3. O arquivo `config/audit-config.yaml` é a única fonte de configuração editável pelo operador.
- **Motivo:** o operador não deve precisar tocar em código.
- **Violação:** hardcodar URL, limiar ou fluxo no código em vez do config.

### R4. Todo CheckResult tem `error_detail` preenchido quando `result = 'fail'`.
- **Motivo:** o relatório precisa de detalhe técnico, não só "falhou".
- **Violação:** `result = 'fail'` com `error_detail = None`.

### R5. Relatório nunca tem prosa, opinião ou interpretação.
- **Motivo:** saída estruturada e limpa, como definido no PRODUCT.md.
- **Violação:** frases como "parece que", "provavelmente", "recomendamos".

### R6. Nunca catch silencioso.
- **Motivo:** erro escondido = bug invisível no diagnóstico.
- **Violação:** `except Exception: pass` ou `except Exception as e: print(e)` sem re-raise.

### R7. Regra de negócio nunca mistura com I/O.
- **Motivo:** testabilidade — lógica de checagem deve ser testável sem browser.
- **Violação:** lógica de pass/fail misturada com código de Playwright ou de arquivo.

### R8. Histórico é append-only. Nunca deletar ou editar registros passados.
- **Motivo:** integridade do histórico para comparação temporal.
- **Violação:** DELETE ou UPDATE em registros de AuditRun ou CheckResult passados.

### R9. `status` (job) e `resultado` (loja) são sempre campos separados. Nunca colapsar.
- **Motivo:** uma execução pode terminar com `status='concluida'` e `resultado='com_falhas'` (auditor rodou, loja tem problema) ou `status='falhou'` com `resultado=null` (auditor quebrou — nada se sabe da loja). São eixos independentes.
- **Violação:** qualquer campo único que tente codificar os dois ao mesmo tempo.

### R10. Relatório e config falam em páginas e fluxos — nunca em "Camada A/B".
- **Motivo:** "Camada A/B" é vocabulário interno de arquitetura, não do problema. O operador entende "checkout travou no passo X", não "Camada A falhou".
- **Violação:** campo `layer: A` ou texto "Camada B" em relatório HTML, JSON de saída ou arquivo de config.
- **Correto no dado:** campo `categoria` com valor `'fluxo'` ou `'saude_tecnica'`.

---

## 5. Glossário do domínio

> Espelho compacto do PRODUCT.md. Use estes termos no código.

| Termo | Definição (1 linha) | No código |
|---|---|---|
| AuditRun | uma execução completa do auditor | classe `AuditRun`, tabela `audit_runs` |
| CheckResult | resultado de uma checagem atômica | classe `CheckResult`, tabela `check_results` |
| CriticalPage | URL configurada para ser auditada | classe `CriticalPage` em config/models.py |
| Flow | sequência de ações que simula um comprador | classe `Flow`, executado em `layer_a.py` |
| Step | ação atômica dentro de um Flow | classe `Step` em config/models.py |
| Popup | elemento sobreposto que pode travar o fluxo | verificado em `popup_checker.py` |
| Threshold | limiar numérico que define falha | campo `threshold` em `CheckResult` |
| Layer A | camada de verificação funcional (fluxos) | módulo `layers/layer_a.py` |
| Layer B | camada de saúde técnica (HTTP, JS, perf) | módulo `layers/layer_b.py` |
| Viewport | desktop ou mobile | enum `Viewport` em types.py |

---

## 6. Padrões de implementação canônicos

### Como adicionar uma nova checagem à Camada B
1. Identificar se é uma checagem binária ou numérica.
2. Implementar como função `async def check_[nome](page: Page, config: CriticalPage) -> CheckResult` em `layer_b.py`.
3. Adicionar ao loop de checagens em `layer_b.run_page_health_checks()`.
4. Se tem limiar configurável, adicionar campo em `config/models.py` → `CriticalPage`.
5. Atualizar `config/audit-config.yaml` com o campo e valor padrão.

### Como adicionar um novo passo a um fluxo
1. Editar `config/audit-config.yaml` na seção do fluxo correspondente.
2. Se o passo requer lógica nova que não existe no `layer_a.py`, implementar função `async def step_[acao](page: Page, step: Step) -> StepResult`.
3. Não criar nova função se o padrão já existe (clique, aguardar elemento, verificar URL).

### Como criar um novo módulo de suporte
1. Criar pasta em `src/auditor/[nome]/` com `__init__.py`.
2. Seguir a convenção de nomes de arquivo (`[responsabilidade].py`).
3. Atualizar `ARCHITECTURE.md` seção 2.
4. Criar spec em `docs/specs/` antes de implementar se a feature é não-trivial.

### Como rodar localmente
```bash
# Instalar dependências
pip install -e ".[dev]"

# Instalar browsers do Playwright
playwright install chromium

# Instalar Lighthouse CLI
npm install -g lighthouse

# Rodar auditoria
python -m auditor run

# Rodar auditoria em uma URL específica
python -m auditor run --url https://minimalclub.com.br

# Ver histórico
python -m auditor diff --since 7d

# Type check
mypy src/

# Lint
ruff check src/ tests/

# Testes
pytest tests/unit/
pytest tests/integration/  # requer conexão com internet
```

**Variáveis de ambiente:** copiar `.env.example` para `.env`.

---

## 7. Anti-patterns explícitos

### Anti-pattern 1: Lógica de checagem dentro do engine
**Ruim:**
```python
async def run_audit(config):
    page = await browser.new_page()
    response = await page.goto(url)
    if response.status != 200:
        results.append(CheckResult(result='fail', ...))  # lógica aqui!
```
**Bom:**
```python
# engine.py
layer_b_results = await run_page_health_checks(page, config.critical_pages)

# layer_b.py
async def check_http_status(page, critical_page) -> CheckResult:
    response = await page.goto(critical_page.url)
    passed = response.status == 200
    return CheckResult(result='pass' if passed else 'fail', ...)
```

### Anti-pattern 2: Hardcodar URL ou limiar no código
**Ruim:** `await page.goto("https://minimalclub.com.br")`
**Bom:** `await page.goto(critical_page.url)` (vem do config)

### Anti-pattern 3: Catch silencioso em checagem
**Ruim:**
```python
try:
    await page.click('#add-to-cart')
except:
    pass  # silencia erro
```
**Bom:**
```python
try:
    await page.click('#add-to-cart', timeout=5000)
except TimeoutError as e:
    return CheckResult(result='fail', error_detail=f"Botão não clicável após 5000ms: {e}")
```

### Anti-pattern 4: Dict solto como modelo de dados
**Ruim:** `result = {"check": "http_status", "result": "pass", "url": url}`
**Bom:** `result = CheckResult(check_name="http_status", result="pass", page_url=url)`

### Anti-pattern 5: Misturar relatório e checagem
**Ruim:** gerar HTML dentro de `layer_b.py`
**Bom:** `layer_b.py` retorna `list[CheckResult]`; `html_reporter.py` consome e gera o HTML

---

## 8. Comportamento esperado do Claude

1. **Antes de qualquer código:** ler `ARCHITECTURE.md`.
2. **Antes de implementar feature nova:** confirmar quais módulos serão tocados e quais CheckResult serão afetados.
3. **Quando em dúvida sobre se uma checagem é determinística:** perguntar. Não inventar critério.
4. **Ao terminar sessão:** atualizar `ARCHITECTURE.md` + criar `docs/sessions/YYYY-MM-DD-*.md`.
5. **Se encontrar inconsistência entre ARCHITECTURE.md e código:** parar e relatar.
6. **Nunca tocar `config/audit-config.yaml` com dados reais de URL sem confirmar com o operador.**
7. **Nunca adicionar dependência** sem perguntar primeiro.
8. **Nunca contornar R1 (determinismo)** — se uma checagem parece subjetiva, ela não entra.
9. **Escrever funções pequenas e nomeadas.** Uma checagem = uma função.
10. **Quando refatorar:** sessão dedicada, com ADR antes se a mudança é estrutural.
