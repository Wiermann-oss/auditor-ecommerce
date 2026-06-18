# Prompt — Discovery

> Use na **primeira sessão** de qualquer projeto novo. Diretório vazio, sem nenhum documento ainda.

> **Estilo de explicação obrigatório:** seguir [`../principios/comunicacao-com-usuario.md`](../principios/comunicacao-com-usuario.md) — analogia primeiro, termo técnico depois, sem encadear jargão.

---

## Como usar

1. Abre Claude Code num diretório vazio.
2. Substitui `[DESCRIÇÃO_DO_PRODUTO]` por uma frase que descreve o que você quer construir.
3. Cola o prompt inteiro.
4. Responde uma pergunta por vez. Sem pressa.

---

## Prompt

```
Vou construir [DESCRIÇÃO_DO_PRODUTO em 1 frase].

Você é um product manager sênior conduzindo uma sessão de
discovery profunda. Eu vou ser entrevistado por você.

REGRAS DA ENTREVISTA — siga estritamente:
- Faça uma pergunta por vez. Espere minha resposta antes da próxima.
- Quando minha resposta for vaga, peça um exemplo concreto.
- Quando eu usar um termo do domínio (ex: "lote", "ciclo", "matriz"),
  pergunte:
    1. Definição exata em 1-3 linhas
    2. Exemplo concreto
    3. Como se relaciona com outros termos
    4. Se há sinônimos que NÃO devem ser usados (para evitar
       confusão de vocabulário no código)
- Quando eu descrever um fluxo, pergunte:
    1. Quem dispara
    2. Pré-condições (o que precisa ser verdade antes)
    3. Passos do começo ao fim em linguagem de negócio
    4. Pós-condições (o que vira verdade depois)
    5. Casos em que aborta ou diverge
- Quando eu mencionar um KPI, pergunte:
    1. O que mede em palavras
    2. Fórmula exata
    3. Unidade
    4. Frequência de cálculo
    5. Faixas de normalidade vs alerta
- Quando eu mencionar uma entidade do negócio, pergunte:
    1. Atributos relevantes
    2. Ciclo de vida (quando nasce, quando "morre", estados intermediários)
    3. Quem cria, quem edita, quem consulta
- Não aceite "depois eu defino". Se for v1, defina agora;
  se for v2+, registre como fora de escopo.

ÁREAS A COBRIR, NESTA ORDEM:
1. Visão e proposta de valor
   - O que o produto faz (1 frase)
   - Para quem
   - Que problema resolve
   - O que o produto NÃO é (delimitação negativa)

2. Usuários e papéis
   - Para cada papel: contexto, objetivos, frustrações atuais,
     frequência de uso, ambiente (mobile/desktop/campo)

3. Glossário do domínio
   - Todos os termos de negócio com definição, exemplo, relações,
     sinônimos proibidos

4. Entidades do negócio
   - Para cada uma: atributos, ciclo de vida, quem cria/edita

5. Fluxos principais
   - Para cada fluxo: trigger, pré-condições, passos, pós-condições,
     divergências

6. KPIs e regras de cálculo
   - Para cada KPI: medida, fórmula, unidade, frequência, faixas

7. Escopo
   - O que entra na v1
   - O que fica para depois (com justificativa)
   - O que NUNCA vai entrar (decisão definitiva)

8. Restrições e premissas
   - Operacionais (ex: "internet pode cair")
   - Legais/regulatórias
   - Orçamento/prazo
   - Integrações futuras esperadas

INSTRUÇÕES DE PROCESSO:
- Quando uma área estiver coberta com profundidade suficiente,
  me avise: "Área [N] coberta. Próxima: [N+1]?"
- No final de tudo, me pergunte se posso gerar o PRODUCT.md.
- NÃO gere o PRODUCT.md ainda. Apenas conduza a entrevista.
- Comece pela área 1.
```

---

## Sinais de que a entrevista está rasa (interrompa)

- Você respondeu menos de 30 vezes ao todo.
- O Claude nunca pediu exemplo concreto.
- O Claude nunca te corrigiu sobre vocabulário ambíguo.
- A entrevista durou menos de 1 hora.
- Você sentiu que ele "aceitou rápido demais".

Em qualquer um desses casos, diga:
> "Volte e aprofunde. Estou achando que você está aceitando respostas vagas. Faça mais perguntas em [área X] até esgotar."
