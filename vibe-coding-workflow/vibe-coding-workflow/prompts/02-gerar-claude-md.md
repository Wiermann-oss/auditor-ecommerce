# Prompt — Gerar CLAUDE.md

> Use após `PRODUCT.md` aprovado, em sessão nova.

> **Estilo de explicação obrigatório:** seguir [`../principios/comunicacao-com-usuario.md`](../principios/comunicacao-com-usuario.md) — analogia primeiro, termo técnico depois, sem encadear jargão.

---

## Pré-requisitos

- [ ] `PRODUCT.md` aprovado e na raiz do projeto.
- [ ] Stack escolhido (use `referencia/stack-recomendado.md` se em dúvida).

---

## Prompt

```
Leia o PRODUCT.md inteiro antes de qualquer coisa.
Quando terminar, me diga em 2 frases o que entendeu do produto
e do domínio.

Em seguida, vamos criar o CLAUDE.md deste projeto.

CLAUDE.md é o manual de operação do agente neste projeto. Ele é
lido em TODA sessão futura. Se for raso, todo o trabalho futuro
sai raso.

ESTRUTURA OBRIGATÓRIA — 9 SEÇÕES, sem pular:

# CLAUDE.md

## 1. Stack e versões
- [Tecnologia, versão exata, papel no sistema] para cada camada
- Bibliotecas permitidas por tipo de problema (ex: "datas:
  date-fns; nunca moment")
- Bibliotecas proibidas (lista com motivo)

## 2. Convenções de código
- Nomenclatura de arquivos (com exemplos)
- Nomenclatura de funções (verbo+objeto específico; nunca
  handle/process/manage genéricos)
- Nomenclatura de variáveis (sem abreviações)
- Tamanho máximo de função: 4-20 linhas
- Tamanho máximo de arquivo: 500 linhas
- Indentação máxima: 2 níveis (early returns sobre nested ifs)
- Tipos sempre explícitos; nunca `any`
- Como tratar erros (mensagem inclui valor que causou + forma esperada)

## 3. Estrutura de pastas obrigatória
Diagrama de árvore com COMENTÁRIO em cada pasta principal:
- O que vai lá
- O que NÃO vai lá

## 4. Regras invioláveis
Lista numerada (R1, R2, R3...). Para cada regra:
- A regra
- Motivo curto
- Consequência da violação

Inclua obrigatoriamente regras de:
- Segurança (RLS, validação, autenticação)
- Dados (soft delete, auditoria, migrations reversíveis quando
  possível)
- Separação de camadas (regra de negócio nunca mistura com I/O)
- Tipos (sem any, validação na fronteira)

## 5. Glossário do domínio
Espelho compacto do PRODUCT.md. Para cada termo:
- Termo
- Definição em 1 linha
- Como aparece no código (nome de tabela, variável, função)

Esse glossário é o que o agente usa ao nomear código.

## 6. Padrões de implementação canônicos
Para cada tipo de tarefa comum, passos exatos:

### Como criar um novo módulo CRUD
1. ...
2. ...

### Como adicionar uma migration
1. ...

### Como criar um componente de UI
1. ...

### Como expor um endpoint
1. ...

### Como adicionar uma regra de negócio nova
1. ...

Sem isso, o agente reinventa o caminho a cada feature.

## 7. Anti-patterns explícitos
Para cada anti-pattern, código RUIM e código BOM lado a lado:

### Anti-pattern: [nome]
Ruim:
```código```
Bom:
```código```
Por quê: [explicação]

Cubra ao menos:
- Função grande misturando responsabilidades
- Catch silencioso
- Tipos `any` ou type assertion sem justificativa
- Comentário óbvio (// pega o usuário pelo id)
- Abstração prematura (DRY mal aplicado)
- Nomes genéricos (handler, data, manager)

## 8. Como rodar e testar localmente
- Comandos exatos para subir o projeto
- Como rodar testes
- Como rodar lint/typecheck
- Como conectar com banco local
- Como ver logs

## 9. Comportamento esperado do Claude
- Antes de qualquer código: ler ARCHITECTURE.md
- Antes de implementar: confirmar entendimento (3 entidades + conexões + risco)
- Quando em dúvida: perguntar, não inventar
- Ao terminar: atualizar ARCHITECTURE.md + criar log de sessão
- Se encontrar inconsistência entre ARCHITECTURE.md e código:
  PARAR e relatar antes de mexer
- Nunca tocar arquivos fora do plano sem perguntar
- Nunca adicionar dependência nova sem perguntar

STACK QUE DEVO USAR (substitua pelo stack real do projeto):
- [Stack camada 1]
- [Stack camada 2]
- ...

PRINCÍPIOS DE CÓDIGO PARA AS SEÇÕES 2, 4 E 7:
Aplique os princípios de Clean Code para LLM (Akita):
- Funções pequenas (4-20 linhas)
- SRP (uma responsabilidade por função/módulo)
- Nomes únicos com poucos hits no grep
- Tipos explícitos sempre
- Sem aninhamento profundo (max 2 níveis)
- Erros com contexto (valor + forma esperada)
- Estrutura de diretório previsível

REGRAS DE GERAÇÃO:
- Se algo precisar ser específico do domínio (ex: regras especiais
  de validação para "lote"), inclua na seção 4 com referência ao
  glossário.
- Se faltar informação para alguma seção, pergunte antes de gerar.
- Não invente bibliotecas que não estão no stack.
- Salve como CLAUDE.md na raiz do projeto.
```

---

## Validação após geração

- [ ] Stack está exatamente como você escolheu.
- [ ] Glossário cobre todos os termos do PRODUCT.md.
- [ ] Regras invioláveis numeradas (R1, R2, ...) com motivo e consequência.
- [ ] Padrões de implementação têm passos concretos, não genéricos.
- [ ] Anti-patterns têm exemplo ruim **e** bom.
- [ ] Comandos para rodar localmente estão exatos (não "configure conforme docs").

Se faltar profundidade em alguma seção, peça correção pontual.
