# Referência — Glossário do Workflow

> Glossário dos termos usados **neste guia**. Não confundir com o glossário do **domínio** de cada projeto, que vive no `PRODUCT.md` daquele projeto.

---

## ADR — Architecture Decision Record
Documento curto que registra uma **decisão arquitetural duradoura**. Mora em `docs/decisions/YYYY-MM-DD-[tema].md`. Estrutura: contexto, decisão, motivação, alternativas descartadas, consequências, o que essa decisão fecha como possibilidade futura. Origem: prática de Michael Nygard (2011).

## ARCHITECTURE.md
Documento na raiz de cada projeto. **Mapa vivo do sistema.** Contém: visão geral, módulos, modelo de dados, fluxos técnicos, decisões já tomadas, pontos frágeis, inventário de arquivos críticos. Lido em **toda** sessão. Atualizado ao **fim** de toda sessão.

## CLAUDE.md
Documento na raiz de cada projeto. **Manual de operação do agente** naquele projeto. Contém: stack, convenções, regras invioláveis, glossário compacto, padrões canônicos, anti-patterns, como rodar localmente, comportamento esperado do agente. Lido em **toda** sessão.

## Caso de borda
Cenário fora do caminho feliz que precisa ser tratado. Cliques duplos, valores limite, refresh no meio, concorrência, deleções a montante. Específicos por feature — não genéricos.

## Checklist (do trilho)
Documento neste guia com lista de itens marcáveis para cada fase. Há 4: sessão universal (`01`), novo projeto (`02`), nova feature (`03`), revisão (`04`).

## Contexto cirúrgico
Princípio: o agente recebe **apenas** o relevante para a tarefa atual — `CLAUDE.md`, `ARCHITECTURE.md`, spec da feature, código que toca, ADRs relacionados. Não joga "tudo que sabe". Antônimo de "contexto inflado" e de "contexto zero".

## Critérios de aceite
Lista de afirmações binárias verificáveis no navegador. Mora na **seção 7 da spec**. Cada caminho funcional vira ao menos um critério. Você usa para testar manualmente após implementação.

## Discovery
Fase 0. Sessão (ou várias) em que o agente entrevista você como product manager para extrair o domínio. Resultado: `PRODUCT.md` denso.

## docs/decisions/
Pasta dentro do projeto. Guarda **ADRs**.

## docs/sessions/
Pasta dentro do projeto. Guarda **logs de sessão**, um por sessão.

## docs/specs/
Pasta dentro do projeto. Guarda **specs por feature**, criadas antes de implementar.

## Fase
Etapa do trilho. Há 5: Fase 0 (Discovery), Fase 1 (Fundação documental), Fase 2 (Esqueleto técnico), Fase 3 (Módulos de negócio), Fase 4 (Revisão arquitetural).

## Janela limpa
Sessão nova do Claude Code, sem histórico de conversa anterior. Estado padrão para começar qualquer sessão importante.

## KPI
Métrica de negócio. No `PRODUCT.md`, cada KPI tem: o que mede, fórmula, unidade, frequência, faixas (normal vs alerta).

## Log de sessão
Arquivo em `docs/sessions/YYYY-MM-DD-[tema].md`. Criado ao **fim** de toda sessão. Contém: objetivo, o que foi feito, decisões, problemas, estado atual, próximo passo, atualizações em outros documentos.

## Mantra
Frase final em cada documento deste guia. Resume o princípio operacional do documento numa linha.

## PRODUCT.md
Documento na raiz de cada projeto. **Visão de produto e domínio.** Contém: visão, usuários, glossário do domínio, entidades, fluxos, KPIs, escopo (v1 vs depois vs nunca), restrições. Atualizado quando o produto muda.

## Regra inviolável
Regra do `CLAUDE.md` (seção 4) que **nunca** pode ser violada sem ADR explícito. Numerada (R1, R2, ...). Inclui motivo e consequência da violação.

## Revisão arquitetural
Sessão dedicada **só** a diagnóstico, sem implementação. Realizada a cada 3-5 features. Saída: lista de itens classificados por severidade + decisão por item.

## SRP — Single Responsibility Principle
Princípio: cada função/módulo tem **uma** responsabilidade. Teste prático: descreva em uma frase. Se aparecer "e", divida.

## Spec
Documento em `docs/specs/[feature].md`. Descreve **comportamento** da feature antes de implementar. Estrutura: resumo, comportamento funcional, dados, regras de negócio, UI/UX, casos de borda, critérios de aceite, riscos.

## Spec First
Prática de descrever o que vai ser construído **antes** de construir. Substituto do PRD em projetos pessoais. Origem: RFCs (Rust, React, Ember).

## Trilho
O sistema operacional descrito por este guia. As 5 fases + os checklists + os prompts + os templates + os princípios. Não é um framework rígido — é um **trilho que evita queda**.

## Validação de contexto
Etapa entre spec aprovada e implementação. O agente confirma entendimento (3 entidades + conexões + risco + arquivos a tocar) antes de escrever código. 2 minutos que economizam horas.

## Vibe coding
Prática (popularizada por Karpathy) de codar conversando com IA, sem revisar cada linha de código. **Vibe coding ingênuo** = sem rede de proteção. **Vibe coding maduro** = com trilho documental compensando a falta de revisão de código linha a linha.

---

## Mantra

> Vocabulário consistente é metade da comunicação. Use estes termos com precisão; não invente sinônimos.
