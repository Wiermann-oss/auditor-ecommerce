# Prompt — Validação de Contexto

> Use depois que a spec está aprovada e antes de pedir implementação.
> 2 minutos que economizam horas. O Claude conduz a validação ponta-a-ponta.

> **Estilo de explicação obrigatório:** seguir [`../principios/comunicacao-com-usuario.md`](../principios/comunicacao-com-usuario.md) — analogia primeiro, termo técnico depois, sem encadear jargão.

---

## Como usar

1. Spec aprovada, em sessão nova ou na mesma.
2. Substitua `[NOME_DA_FEATURE]` pelo nome da spec.
3. Cole o prompt.
4. Claude conduz: responde, valida você mesmo, e te entrega o checklist pra revisão final.

---

## Prompt

```
PAPEL: você é um arquiteto sênior conduzindo validação de contexto
técnico antes da implementação de [NOME_DA_FEATURE].

NÃO ESCREVA CÓDIGO. Apenas conduza a validação descrita abaixo.

LEITURA PRÉVIA OBRIGATÓRIA. Antes de qualquer resposta, leia:
- CLAUDE.md
- ARCHITECTURE.md
- docs/specs/[NOME_DA_FEATURE].md

Para cada item 1–5, cite entre colchetes a seção do documento que
sustenta sua resposta. Ex: "(1) orders_raw [spec §3.1]".

1. ENTIDADES PRINCIPAIS
   Liste as 3 entidades mais centrais. Se houver secundárias
   relevantes, liste em sublista. Se passar de 5 totais, sinalize
   que a feature pode estar grande demais e proponha quebrar antes
   de prosseguir. Para cada: nome do glossário, por que é central,
   operação (ler/criar/atualizar/deletar).

2. CONEXÕES
   Para cada módulo do ARCHITECTURE.md que esta feature toca: cite
   o nome textual e descreva a chamada concreta (não "interage com
   X", mas "chama Y de X para fazer Z").

3. RISCO PRINCIPAL
   - Risco específico (não "performance" genérico)
   - Por que é o maior
   - Como mitigar

4. ARQUIVOS A TOCAR
   Existentes (caminho completo) e novos (caminho completo).
   NÃO toque arquivos fora dessa lista sem perguntar.

5. LACUNAS
   Identifique 1–3 coisas que você não sabe responder com confiança.
   Pergunte antes de continuar — ou declare "nenhuma lacuna" se
   estiver tudo claro.

VERIFICAÇÃO INTERNA antes de me entregar:
- Rode `ls` em cada arquivo existente listado em (4). Se algum não
  existir, refaça o item.
- Cada módulo do (2) aparece textualmente em ARCHITECTURE.md? Se
  não, refaça.
- Cada entidade do (1) aparece no glossário do CLAUDE.md ou na §3
  da spec? Se não, refaça.

ENTREGA. Após responder 1–5 e passar nas verificações, gere também:
- Um checklist de revisão pra mim (4 itens binários: entidades OK?
  conexões OK? risco plausível? arquivos OK?).
- Se eu apontar erro, refaça os 5 itens com a correção — não
  silenciosamente.

LEMBRE: NÃO escreva código. Apenas 1–5 + verificações + checklist.
```

---

## Quando pular esta validação

**Nunca**, se a feature toca regra de negócio, dinheiro ou dados.

**Pode pular**, se a feature é puramente cosmética (cor, texto, espaçamento).

Em dúvida → não pule.
