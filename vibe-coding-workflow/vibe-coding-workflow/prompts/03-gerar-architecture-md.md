# Prompt — Gerar ARCHITECTURE.md inicial

> Use após `CLAUDE.md` aprovado, em sessão nova.

> **Estilo de explicação obrigatório:** seguir [`../principios/comunicacao-com-usuario.md`](../principios/comunicacao-com-usuario.md) — analogia primeiro, termo técnico depois, sem encadear jargão.

---

## Pré-requisitos

- [ ] `PRODUCT.md` e `CLAUDE.md` na raiz do projeto.
- [ ] Você está disposto a tomar 1-3 decisões arquiteturais com o Claude.

---

## Prompt

```
Leia PRODUCT.md e CLAUDE.md inteiros antes de qualquer coisa.
Quando terminar, confirme que entendeu o domínio, stack e regras
em 3 frases.

Vamos criar o ARCHITECTURE.md inicial. É um PLANO. Não escreva
nenhum código de implementação nesta sessão.

ARCHITECTURE.md é o mapa vivo do sistema. Lido em toda sessão.
Atualizado ao fim de toda sessão. Se for raso, o projeto fica cego.

ANTES DE GERAR — DECISÕES PENDENTES:
Identifique 1 a 3 decisões arquiteturais com mais de uma opção
viável (ex: "essa entidade vira tabela única ou duas tabelas com
relação 1:1?"). NÃO escolha sozinho. Liste as decisões com
prós/contras de cada opção e me pergunte. Espere minhas respostas
antes de continuar.

ESTRUTURA OBRIGATÓRIA — 7 SEÇÕES, sem pular:

# ARCHITECTURE.md

## 1. Visão geral em 1 página
Parágrafo que explica o sistema inteiro a alguém novo, em
linguagem simples. Suficiente para entender o sistema só lendo
esta seção.

## 2. Diagrama de módulos
Para cada módulo:
- Nome
- Responsabilidade ÚNICA (1 frase, sem "e")
- Depende de: [módulos a montante]
- Quem depende: [módulos a jusante]
- Estado: planejado | em construção | pronto

Use representação ASCII se ajudar a visualizar dependências.

## 3. Entidades e modelo de dados
Para cada tabela:
- Nome da tabela
- Colunas com tipo, obrigatoriedade, default
- Chaves primárias e estrangeiras
- Índices necessários
- Políticas RLS (quem pode ler/escrever)
- Soft delete? Auditoria?
- Invariantes (regras que NUNCA podem ser violadas)

## 4. Fluxos de dados
Para cada fluxo principal do PRODUCT.md (seção 5), rastreie o
caminho técnico:
- Trigger (tela, evento, cron)
- Função/endpoint que recebe
- Validações aplicadas (com regra)
- Operações de banco (em ordem)
- Resposta para o usuário
- Side effects (e-mail, log, evento, webhook)

## 5. Decisões arquiteturais já tomadas
Lista resumida (cada item referencia docs/decisions/ se aplicável):
- Decisão
- Data
- Por quê
- O que isso IMPEDE de fazer no futuro

## 6. Pontos frágeis conhecidos
Lista honesta:
- Trecho frágil
- Por que é frágil
- O que vai estourar primeiro
- Plano (consertar agora? aceitar e monitorar?)

## 7. Inventário de arquivos críticos
Mini-índice (vai ficar parcialmente vazio agora, preenche depois):
- Caminho do arquivo
- Responsabilidade
- Quem deve mexer (e quem não deve)

REGRAS DE GERAÇÃO:
- Cada módulo tem UMA responsabilidade. Se a frase precisa de
  "e", divida em dois módulos.
- Toda tabela tem RLS, soft delete e auditoria, a menos que você
  justifique o contrário no campo "soft delete?".
- Toda entidade do PRODUCT.md vira ao menos uma tabela.
- Todo fluxo do PRODUCT.md aparece na seção 4.
- Se houver decisão arquitetural com mais de uma opção viável,
  ME PERGUNTE antes de escolher.
- Se faltar informação para alguma seção, me pergunte antes
  de gerar.
- Salve como ARCHITECTURE.md na raiz do projeto.
```

---

## Validação após geração

- [ ] Visão geral é compreensível sem contexto técnico.
- [ ] Cada módulo tem responsabilidade única (frase sem "e").
- [ ] Cada entidade do PRODUCT.md tem ao menos uma tabela.
- [ ] Cada fluxo do PRODUCT.md está rastreado tecnicamente.
- [ ] Pontos frágeis foram listados honestamente (lista vazia é red flag).
- [ ] Decisões com alternativa foram apresentadas a você antes da escolha.

Se algo está raso, peça aprofundamento pontual.
