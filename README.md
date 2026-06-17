# Auditor de E-commerce — Minimal

Sistema de verificação técnica automatizada da loja. Responde à pergunta: **"existe alguma variável técnica quebrada ou degradada na loja agora?"**

Para detalhes completos do produto, arquitetura e convenções de código, consulte:
- [PRODUCT.md](PRODUCT.md) — o que é, para quem, o que não é
- [ARCHITECTURE.md](ARCHITECTURE.md) — módulos, fluxos de dados, modelo de dados
- [CLAUDE.md](CLAUDE.md) — stack, regras, padrões para o agente

---

## Como rodar

### Pré-requisitos

```bash
# Python 3.11+
python --version

# Instalar dependências
pip install -e ".[dev]"

# Instalar browsers do Playwright
playwright install chromium

# Instalar Lighthouse CLI (requer Node.js)
npm install -g lighthouse
```

### Rodar uma auditoria

```bash
# Auditoria completa (usa config/audit-config.yaml)
python -m auditor run

# Ver histórico dos últimos 7 dias
python -m auditor diff --since 7d
```

O relatório é gerado em `reports/[timestamp].html` — abra no navegador.

---

## Como configurar o que é monitorado

Edite `config/audit-config.yaml`. Você pode:

- **Adicionar/remover páginas:** bloco em `critical_pages`
- **Ajustar limiares de performance:** seção `thresholds`
- **Adicionar/remover popups:** bloco em `popups`
- **Adicionar/remover passos do fluxo de compra:** bloco em `flows[].steps`

Não é necessário mexer em nenhum arquivo de código.

---

## Agendamento automático

O arquivo `.github/workflows/audit.yml` roda a auditoria diariamente às 09h (BRT). Para ativar, configure o repositório no GitHub e habilite o workflow.
