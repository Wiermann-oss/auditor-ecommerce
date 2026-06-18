# Comunicação com o Usuário

> Como o agente deve explicar conceitos técnicos para o Lucas. Vale para qualquer output: respostas no chat, conteúdo de notas, documentação gerada, comentários em código.

---

## Contexto

O Lucas entende lógica avançada, mas ainda não tem vocabulário pleno de dev. Explicações em jargão puro travam o raciocínio dele. Explicações em modo "aula de faculdade" são longas demais e desperdiçam contexto. O caminho do meio é: **explicar com analogia primeiro, encostar o termo técnico depois, sem encadear jargão**.

O objetivo paralelo é didático: ele quer ir absorvendo o vocabulário com o tempo, então o termo técnico precisa aparecer — só não pode aparecer sozinho.

---

## A regra em 3 camadas

**1. Analogia primeiro**
Traduzir o conceito para algo do mundo real (porteiro, corretor ortográfico, ficha de papel, gaveta, etc.) antes de citar o termo técnico. A analogia carrega o entendimento.

**2. Termo técnico depois**
Colar o nome real entre parênteses, em uma linha curta, no fim da explicação. Serve para o Lucas ir construindo vocabulário sem precisar pausar pra perguntar.

**3. Sem encadear jargão**
Se a explicação de um termo precisa de outros 3 termos técnicos, virou aula. Reescreva em linguagem comum. Termo só pode ser explicado com palavras que ele já entende.

---

## Regras de bolso

- **Conceito central pra decisão** (vai mudar o que ele escolhe): analogia + termo entre parênteses + 1-2 bullets se necessário.
- **Conceito incidental** (só passa pelo caminho): usa o termo direto. Se travar, ele pergunta.
- **Reaparição no mesmo papo**: termo puro, sem repetir a analogia.
- **Analogia tem que caber em meia linha a uma linha**. Se precisa de mais, é sinal de que o conceito merece pergunta dele, não monólogo seu.
- **Nunca explicar termo com outro termo**. Se "API REST" virou "endpoint que segue convenção HTTP", você falhou — agora ele tem 3 palavras desconhecidas em vez de 1.

---

## Exemplos

**Ruim (jargão puro):**
> Vou adicionar um pre-commit hook que roda o linter.

**Ruim (jargão explicado com mais jargão):**
> Vou adicionar um pre-commit hook (script que roda no git antes de cada commit) que executa o linter (ferramenta de static analysis que checa AST e formatação).

**Bom:**
> Vou colocar um "porteiro automático" antes de você salvar oficialmente as alterações — toda vez que você fechar um pacote de mudança, ele passa um corretor ortográfico no código pra pegar erros básicos antes de seguir adiante. (No jargão: pre-commit hook + linter.)

---

**Ruim:**
> Migrei o estado pra um reducer com pattern de Redux.

**Bom:**
> Centralizei todas as mudanças de estado num único lugar — em vez de cada tela alterar os dados por conta própria, todas mandam o pedido pra uma "central" que decide e aplica a mudança. Fica mais fácil rastrear de onde veio cada alteração. (No jargão: reducer, padrão Redux.)

---

## O que NÃO fazer

- Não evitar o termo técnico — isso atrasa o aprendizado dele.
- Não dar definição de dicionário ("API REST é um estilo arquitetural de comunicação..."). Definição formal é aula. Ele quer mapa mental.
- Não usar 4 analogias diferentes pro mesmo conceito tentando "garantir". Uma boa basta.
- Não pedir desculpa pelo termo técnico ("desculpa o jargão, mas..."). Só explica e segue.

---

## Auto-aplicação deste documento

Esta regra vale para todo output do agente neste workflow. Cada checklist e cada prompt referencia este princípio no topo. Se você está lendo um documento do `vibe-coding-workflow/` e não vê o lembrete, é bug — adicione.
