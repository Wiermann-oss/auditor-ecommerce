# Prompt — Pedir Spec

> Use após `prompts/04-inicio-sessao.md`, antes de qualquer código de feature nova.

> **Estilo de explicação obrigatório:** seguir [`../principios/comunicacao-com-usuario.md`](../principios/comunicacao-com-usuario.md) — analogia primeiro, termo técnico depois, sem encadear jargão.

---

## Como usar

1. Confirme que você está em sessão com início feito (Claude já confirmou A, B, C, D).
2. Substitua `[NOME_DA_FEATURE]` por um nome curto e descritivo.
3. Substitua `[CONTEXTO_OPCIONAL]` por qualquer detalhe que ajude (ou apague a linha).
4. Cole o prompt.

---

## Prompt

```
Antes de implementar [NOME_DA_FEATURE], vamos criar a spec.

[CONTEXTO_OPCIONAL: ex.: "esta feature aparece como módulo X
no ARCHITECTURE.md"]

PASSO 1 — perguntas críticas:
Antes de gerar a spec, faça 3 perguntas críticas sobre o domínio
desta feature que o PRODUCT.md NÃO responde claramente. Espere
minhas respostas. Não gere nada ainda.

PASSO 2 — quando eu responder, gere a spec em
docs/specs/[NOME_DA_FEATURE].md com a estrutura abaixo.
Não pule seções. Se faltar informação, pare e pergunte.

ESTRUTURA OBRIGATÓRIA:

# Spec — [Nome da feature]

## 1. Resumo em 1 parágrafo
O que faz, para quem, por quê. Tem que dar para entender a
feature lendo só esta seção.

## 2. Comportamento funcional
### 2.1 Caminho feliz
Passos do usuário do início ao fim, numerados.
### 2.2 Caminhos alternativos
O que pode acontecer no meio (cancelar, voltar, editar).
### 2.3 Casos de erro visíveis ao usuário
Para cada erro: quando ocorre, o que o usuário vê, como recupera.

## 3. Dados envolvidos
### 3.1 Entidades lidas
Lista de entidades do ARCHITECTURE.md que esta feature LÊ.
### 3.2 Entidades criadas/atualizadas/deletadas
Lista com tipo de operação por entidade.
### 3.3 Campos novos
Para cada campo novo: nome, tipo, default, validação,
em qual tabela.
### 3.4 Migrations necessárias
Descritas em palavras (não SQL):
- O que altera
- Reversível? Se não, por quê

## 4. Regras de negócio explícitas
Lista numerada (R1, R2, ...). Cada regra em linguagem do
domínio, usando EXATAMENTE os termos do glossário do CLAUDE.md.

Exemplo de boa regra:
"R1. Um lote não pode ser fechado se houver matrizes vivas
associadas."

## 5. UI/UX
### 5.1 Telas afetadas
Lista de telas (existentes ou novas).
### 5.2 Componentes novos necessários
Lista com responsabilidade de cada um.
### 5.3 Estados visuais
Para cada tela: loading, vazio, erro, sucesso (o que aparece
em cada estado).
### 5.4 Permissões
Para cada papel do PRODUCT.md: o que pode ver, o que pode editar.

## 6. Casos de borda específicos desta feature
NÃO genéricos. Pense em:
- Ações repetidas (clicar duas vezes seguidas)
- Valores limite (zero, negativo, máximo, vazio)
- Deleções a montante (se o dado pai for apagado)
- Concorrência (dois usuários ao mesmo tempo)
- Estado inconsistente (refresh no meio de uma operação)

Para cada caso: o que esperamos que aconteça.

## 7. Critérios de aceite testáveis
Lista de afirmações binárias verificáveis no navegador.
Formato: "Quando [ação], o sistema [resposta]."
Cada caminho da seção 2 vira ao menos um critério.

## 8. Riscos e impactos
- Módulos existentes que podem quebrar (com nomes do
  ARCHITECTURE.md)
- Reversibilidade da mudança
- Que dado em produção (se houvesse) seria afetado

REGRAS DE GERAÇÃO:
- Use SEMPRE termos do glossário do CLAUDE.md.
- Se uma regra de negócio não está clara no PRODUCT.md, pergunte.
- Não invente comportamento "razoável" — confirme.
- Não escreva código nesta sessão.
- Salve como docs/specs/[NOME_DA_FEATURE].md.
```

---

## Verificação após geração da spec

Leia a spec inteira e cheque (use `03-checklist-nova-feature.md` Passo 3.2 para detalhe):

- [ ] Glossário foi respeitado (mesmos termos).
- [ ] Cada caminho funcional virou ao menos um critério de aceite.
- [ ] Casos de borda são específicos, não genéricos.
- [ ] Migrations descritas com reversibilidade.
- [ ] Riscos citam módulos pelo nome.

**Se algo está raso, peça correção pontual:**
```
Corrija a spec, seção [X]: [problema específico].
A regra/comportamento que faltou: [descrição em linguagem
de negócio].
```
