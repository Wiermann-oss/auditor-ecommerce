# Auditor Automático de E-commerce

> Documento de produto. Fonte de verdade do **domínio** e do **comportamento esperado**. Lido por todos os outros documentos. Atualizado quando o produto muda.

---

## 1. Visão e proposta de valor

**Em uma frase:** O Auditor é um sistema determinístico que responde, sem nenhuma subjetividade, à pergunta "existe alguma variável técnica quebrada ou degradada na loja agora?".

**Para quem, qual problema, como resolve:**
A Minimal precisa garantir que nenhum problema técnico da loja — página fora do ar, botão quebrado, checkout travado, JS com erro, performance degradada — passe despercebido. Hoje esse teste é feito manualmente, é lento, depende da atenção de quem executa e não gera histórico. O Auditor automatiza essa verificação: percorre as páginas e fluxos críticos da loja, coleta sinais técnicos objetivos (HTTP status, erros de console, recursos que falharam, tempos de carregamento, métricas de performance) e produz um relatório estruturado de pass/fail. Executa sob demanda e de forma agendada. Qualquer falha é registrada com detalhe técnico — sem interpretação.

**O que este produto NÃO é:**
- Não avalia copy, oferta, headline, design, layout ou qualquer aspecto qualitativo
- Não diagnostica a causa de queda de faturamento (pode estar em CPM, criativo, sazonalidade, atribuição)
- Não é um sistema de monitoramento em tempo real (é uma auditoria pontual, executada sob demanda ou agenda)
- Não tem nenhuma camada de IA ou julgamento — todas as checagens são determinísticas e binárias (ou métricas numéricas)

---

## 2. Usuários e papéis

### Operador da Minimal
- **Contexto:** membro do time que gerencia a loja; pode não ter background técnico; usa o sistema via linha de comando ou resultado do agendamento automático
- **Objetivos no sistema:** saber, rápido e sem ambiguidade, se existe alguma variável técnica quebrada na loja neste momento
- **Frustrações atuais:** fazer teste manual é chato, demora, e depois da décima página a atenção cai; não há registro histórico; quando o faturamento cai, não se sabe se é técnica ou estratégia
- **Frequência de uso:** diária (agendamento automático) + sob demanda quando há suspeita de problema

### Dev / Claude (executor)
- **Contexto:** quem adiciona ou edita checagens e fluxos no arquivo de config; tem background técnico
- **Objetivos no sistema:** estender o sistema sem mexer no código de engine; adicionar URLs, fluxos, limiares via config
- **Frustrações atuais:** n/a (papel novo)
- **Frequência de uso:** eventual (quando a loja muda de estrutura ou fluxo)

---

## 3. Glossário do domínio

### Auditoria (Audit Run)
- **Definição:** uma execução completa do sistema, que percorre todas as páginas e fluxos configurados e produz um relatório
- **Exemplo:** rodar `python -m auditor run` às 09h de uma segunda-feira e obter o relatório daquela execução
- **Relações:** composta de múltiplas Checagens; gera um Relatório; é armazenada no Histórico
- **NÃO confundir com:** checagem (que é um único passo dentro da auditoria)

### Checagem (Check)
- **Definição:** uma verificação atômica e binária (pass/fail) ou numérica que o sistema executa sobre uma URL ou fluxo
- **Exemplo:** "status HTTP da home é 200", "botão 'Adicionar ao carrinho' é clicável", "nenhum erro de JS na página de produto"
- **Relações:** pertence a uma Página ou a um Fluxo; é o menor resultado do sistema
- **NÃO confundir com:** auditoria (conjunto de checagens)

### Página Crítica (Critical Page)
- **Definição:** URL da loja que o sistema visita e audita; definida no arquivo de configuração
- **Exemplo:** home (`/`), coleção (`/collections/all`), página de produto (`/products/[slug]`), carrinho (`/cart`)
- **Relações:** tem N checagens associadas; pertence ao resultado de uma Auditoria
- **NÃO confundir com:** fluxo (que é uma sequência de ações, não uma URL isolada)

### Fluxo (Flow)
- **Definição:** sequência ordenada de ações num navegador que simula o caminho real de um comprador
- **Exemplo:** home → selecionar produto → adicionar ao carrinho → ir ao checkout → preencher dados → confirmar
- **Relações:** composto de Passos; cada Passo tem uma asserção binária; o fluxo falha se qualquer passo falhar
- **NÃO confundir com:** página crítica (que é auditada de forma estática, sem interação sequencial)

### Passo (Step)
- **Definição:** ação atômica dentro de um Fluxo com uma asserção binária associada
- **Exemplo:** "clicar no botão 'Comprar agora'" + asserção "próxima URL contém /cart"
- **Relações:** pertence a um Fluxo; tem resultado pass/fail com detalhe técnico do erro

### Popup
- **Definição:** elemento que aparece sobre o conteúdo da página (newsletter, cupom, intenção de saída, cookies, aviso) e pode travar o fluxo de compra
- **Exemplo:** popup de newsletter que abre após 3 segundos na home; banner de cookies que bloqueia cliques
- **Relações:** verificado dentro do Fluxo funcional; tem checagens específicas (dispara, fecha, não bloqueia)
- **NÃO confundir com:** modal de produto (que é parte do fluxo de compra, não um interruptor)

### Relatório (Report)
- **Definição:** saída estruturada de uma Auditoria, com resultado por página e por checagem
- **Exemplo:** arquivo `reports/2026-06-17T09-00-00.json` + `reports/2026-06-17T09-00-00.html`
- **Relações:** gerado ao fim de cada Auditoria; armazenado no Histórico
- **NÃO confundir com:** histórico (que é o conjunto de todos os relatórios ao longo do tempo)

### Histórico (History)
- **Definição:** banco SQLite que armazena todas as auditorias passadas, permitindo comparação temporal
- **Exemplo:** consultar "qual foi o primeiro dia em que a home começou a retornar status 500?"
- **Relações:** alimentado por cada Auditoria; consultado pelo módulo de comparação
- **NÃO confundir com:** relatório (que é a saída de uma execução específica)

### Limiar (Threshold)
- **Definição:** valor numérico que determina quando uma métrica conta como falha
- **Exemplo:** load time > 5000ms = falha; LCP > 4000ms = falha
- **Relações:** definido no arquivo de configuração; aplicado pelo módulo de saúde técnica
- **NÃO confundir com:** asserção binária (que não tem limiar — ou passa ou falha)

---

## 4. Entidades do negócio

### AuditRun
- **Atributos relevantes:** id, started_at, finished_at, status (success/partial/failed), trigger (manual/scheduled), config_snapshot
- **Ciclo de vida:** criado quando auditoria inicia → populated com resultados à medida que checagens executam → finalizado ao término
- **Quem cria:** engine (ao rodar `auditor run`)
- **Quem edita:** engine (durante a execução)
- **Quem consulta:** operador (via relatório/HTML), dev (via SQLite)

### CheckResult
- **Atributos relevantes:** id, audit_run_id, page_url ou flow_name, check_name, layer (A/B), result (pass/fail), value (numérico, opcional), threshold (numérico, opcional), error_detail (texto técnico, null se pass), duration_ms, viewport (desktop/mobile)
- **Ciclo de vida:** criado quando a checagem é executada; imutável após criação
- **Quem cria:** engine (camadas A e B)
- **Quem edita:** ninguém (imutável)
- **Quem consulta:** módulo de relatório, módulo de histórico

### Config
- **Atributos relevantes:** versão, lista de critical_pages (URL + checagens habilitadas + limiares), lista de flows (nome + passos + dispositivos), thresholds globais, popups esperados
- **Ciclo de vida:** criado manualmente; atualizado quando a loja muda
- **Quem cria:** dev/operador (editando `config/audit-config.yaml`)
- **Quem edita:** dev/operador
- **Quem consulta:** engine ao iniciar uma Auditoria

---

## 5. Fluxos principais

### Fluxo 1 — Auditoria sob demanda
- **Quem dispara:** operador via `python -m auditor run`
- **Pré-condições:** config/audit-config.yaml válido; loja acessível via internet; Playwright instalado
- **Passos:**
  1. Engine lê e valida `config/audit-config.yaml`
  2. Cria registro de AuditRun no SQLite
  3. Para cada página crítica: executa Camada B (saúde técnica) em desktop e mobile
  4. Para cada fluxo configurado: executa Camada A (funcional) em desktop e mobile
  5. Para cada popup configurado: executa checagens de popup dentro da Camada A
  6. Consolida todos os CheckResult no AuditRun
  7. Gera relatório JSON + HTML em `reports/`
  8. Imprime resumo no terminal (total de checagens, quantas falharam, link para o HTML)
- **Pós-condições:** AuditRun salvo no histórico; relatório disponível em `reports/`
- **Divergências:** se a loja estiver completamente inacessível (timeout na home), a auditoria aborta com status `failed` e registra o erro

### Fluxo 2 — Auditoria agendada
- **Quem dispara:** cron (GitHub Actions ou cron do SO)
- **Pré-condições:** mesmas do Fluxo 1; credenciais de ambiente configuradas
- **Passos:** idênticos ao Fluxo 1 (o agendamento apenas chama o mesmo comando)
- **Pós-condições:** relatório salvo; histórico atualizado
- **Divergências:** falha de execução é registrada no log da action/cron

### Fluxo 3 — Comparação temporal
- **Quem dispara:** operador via `python -m auditor diff --since 7d`
- **Pré-condições:** ao menos 2 auditorias no histórico SQLite
- **Passos:**
  1. Consulta histórico no período especificado
  2. Compara cada CheckResult da última auditoria com os anteriores
  3. Identifica checagens que passaram a falhar (regressões) e que pararam de falhar (recuperações)
  4. Gera saída estruturada com o delta
- **Pós-condições:** delta impresso no terminal e/ou salvo como JSON
- **Divergências:** se não há auditorias no período, informa e encerra

---

## 6. KPIs e regras de cálculo

### Taxa de Pass
- **Mede:** percentual de checagens que passaram na auditoria
- **Fórmula:** (total_pass / total_checks) × 100
- **Unidade:** %
- **Frequência:** por auditoria
- **Normal:** 100%
- **Alerta:** < 100% (qualquer falha é relevante)

### Contagem de Falhas por Camada
- **Mede:** quantas checagens falharam em cada camada (A: funcional, B: saúde técnica)
- **Fórmula:** count(result = 'fail') GROUP BY layer
- **Unidade:** número inteiro
- **Frequência:** por auditoria
- **Normal:** 0
- **Alerta:** ≥ 1

### Load Time
- **Mede:** tempo até o evento `load` da página (DOMContentLoaded → load)
- **Fórmula:** navigation_timing.load_event_end - navigation_timing.fetch_start (ms)
- **Unidade:** ms
- **Frequência:** por página por auditoria
- **Normal:** ≤ 3000ms
- **Alerta:** > 5000ms (configurável por limiar)

### LCP (Largest Contentful Paint)
- **Mede:** tempo até o maior elemento visível carregar (Core Web Vital)
- **Fórmula:** Lighthouse LCP metric
- **Unidade:** ms
- **Frequência:** por página por auditoria
- **Normal:** ≤ 2500ms
- **Alerta:** > 4000ms (configurável)

### Erros de Console
- **Mede:** número de erros de JavaScript capturados no console durante o carregamento da página
- **Fórmula:** count(console.error events)
- **Unidade:** número inteiro
- **Frequência:** por página por auditoria
- **Normal:** 0
- **Alerta:** ≥ 1

### Requisições com Falha
- **Mede:** número de requisições de rede que retornaram status ≥ 400 ou falharam (timeout, DNS)
- **Fórmula:** count(network_requests WHERE status >= 400 OR failed = true)
- **Unidade:** número inteiro
- **Frequência:** por página por auditoria
- **Normal:** 0
- **Alerta:** ≥ 1

---

## 7. Escopo

### 7.1 Entra na v1
- Camada A: automação de navegador para fluxo completo home → produto → carrinho → checkout (desktop e mobile)
- Camada A: checagens de popup (dispara, fecha, não bloqueia fluxo)
- Camada B: status HTTP, erros de console, requisições com falha, recursos não carregados
- Camada B: load time via Navigation Timing API (Playwright)
- Camada B: Core Web Vitals (LCP, CLS, FID) via Lighthouse CLI
- Camada C: relatório JSON + HTML por execução
- Camada C: histórico SQLite
- Configuração via YAML editável sem tocar no código
- Execução sob demanda (CLI)
- Execução agendada via GitHub Actions (config de workflow inclusa)
- Comparação temporal simples (`diff --since Nd`)

### 7.2 Fica para depois
- Dashboard web interativo — *Justificativa: relatório HTML cobre a v1; dashboard requer backend*
- Notificações automáticas (Slack, e-mail, WhatsApp) ao detectar falha — *Justificativa: agendamento via GH Actions já notifica por e-mail em falha; alertas customizados são próximo passo*
- Teste de checkout com transação real — *Justificativa: requer credencial de pagamento de teste e integração com gateway; complexidade alta para v1*
- Monitoramento contínuo em tempo real — *Justificativa: auditoria pontual cobre o caso de uso; real-time aumenta custo de operação*

### 7.3 Nunca vai entrar
- Avaliação de copy, oferta, design ou qualquer aspecto qualitativo — *Motivo: fora de escopo por princípio; existe fluxo separado para isso*
- Diagnóstico de causa de queda de faturamento — *Motivo: o sistema isolada a hipótese técnica, não diagnostica*

---

## 8. Restrições e premissas

### Operacionais
- O sistema precisa de acesso à internet para acessar a loja
- A loja é Shopify (pode ter apps de terceiros que afetam o DOM)
- Playwright deve rodar em modo headless (sem interface gráfica) para execução agendada
- Lighthouse CLI deve estar instalado no ambiente de execução
- A auditoria não deve fazer compras reais; o fluxo de checkout vai até a página de confirmação de dados, não submete pagamento

### Legais / regulatórias
- A auditoria é executada sobre a própria loja da Minimal; não há implicações de privacidade de terceiros
- O sistema não armazena dados de clientes; apenas dados técnicos de execução

### Orçamento / prazo
- Execução por auditoria deve ser enxuta (objetivo: < 10 minutos para auditoria completa)
- Sem dependências de serviços pagos além do que já existe (GH Actions free tier cobre)

### Integrações futuras esperadas
- Notificações Slack quando auditoria detectar falha (não para implementar agora)
- Integração com sistema de alertas da Minimal (não para implementar agora)
