# Avaliação — Exercício 1.2
**Papel:** Desenvolvedor | **Cenário:** 1 — Entendimento e Contexto | **Exercício:** 1.2 — Prototipação de Prompt com Engenharia de Contexto

---

## Resumo

O entregável documenta um ciclo completo de três iterações (v1 → v2 → v3.1) com análise crítica detalhada de cada rodada, mapeamento estático/dinâmico com estimativa de tokens e um scorecard comparativo final. O arquivo `dev-exercicio-1-2-prompt-system-v1.md` adiciona uma camada de sofisticação extra, tratando metadados de OCR, vigência de documentos e hierarquia de confiança — indicando que o participante foi além do mínimo exigido. O trabalho é fortemente rastreável: cada mudança entre versões tem motivação documentada com evidência no output testado.

---

## Scores por Dimensão

| Dimensão | Score | Justificativa |
|---|---|---|
| D1 — Domínio Conceitual | **3** | Usa terminologia precisa e com nuance: "alucinação contextual", "context rot", "espaço de respostas possíveis", distinção entre chunk fragmentado vs. completo, e o insight central de que o v1 falhou porque o modelo se posicionou como "especialista em logística" e não como "leitor estrito de documentos". Não é uso genérico do conceito — é identificação do mecanismo exato de falha. |
| D2 — Uso de Ferramentas | **3** | Três rodadas documentadas com setup explícito (qual prompt + quais chunks). Cada rodada gerou análise que produziu mudanças cirúrgicas e verificáveis na próxima versão. O ciclo gerar → avaliar → iterar está visível linha a linha. As versões são materialmente diferentes: v1 genérica, v2 adiciona proibições granulares e diferenciação ⚠️/❓, v3.1 adiciona hierarquia de fontes e separação recusa total vs. resposta parcial. |
| D3 — Qualidade do Entregável | **3** | O entregável está completo: mapeamento com tokens, 9 respostas documentadas (3 por rodada), análise crítica por pergunta, scorecard final com comparativo por critério. O `dev-exercicio-1-2-prompt-system-v1.md` é uma versão ainda mais madura, com tratamento de metadados (`vigencia_confirmada`, `confianca_ocr < 0.85`, `substituido_por`) e ramais organizados por tipo de questão — utilizável diretamente em produção. |
| D4 — Pensamento Crítico | **3** | A análise da Rodada 1 não é superficial. O participante identificou: (a) que o ramal 4500 era invenção na Rodada 1 mas era dado real na Rodada 2 — distinguindo as duas situações; (b) que a confusão custo/prazo na Pergunta 3 Rodada 2 era um problema de domínio semântico, não de alucinação; (c) que a "recusa total indevida" do v2 na Pergunta 3 era um bug de lógica no próprio prompt — o modelo tinha a informação mas recusou mesmo assim. Nenhum desses pontos é óbvio. |
| D5 — Aplicabilidade ao Projeto | **3** | Todos os exemplos usam IDs reais: POL-001, PROC-042-v2, SLA-2024. As perguntas de teste são as três do enunciado. O prompt final referencia tiers (Gold), multiplicadores regionais, faixas de peso, vigência de contratos — dados específicos do NovaTech, não de um cenário genérico de logística. |

**Score do exercício: 3.0**

---

## Verificação de Armadilhas

**Armadilha obrigatória — "Prazo de devolução para carga perigosa":**

A resposta correta é negar categoricamente (POL-001, seção 3.2: "NÃO são elegíveis"). O v1 gerou: *"não é impossível — apenas requer tratamento especial"* — suavização explícita da proibição.

O participante identificou a falha e a nomeou corretamente:

> *"O comportamento correto esperado ❌ A resposta correta é negar categoricamente — POL-001 é explícito. O modelo suavizou a exceção."*

E corrigiu no v2/v3.1 com guardrail explícito: *"NUNCA suavize uma proibição explícita. Se o texto diz 'exceto X', a resposta é 'X não é permitido' — não 'X requer tratamento especial'."*

**Armadilha encontrada: ✅**

---

## Pontos Fortes

1. **Análise de causa raiz, não sintoma:** A Rodada 1 não foi descrita como "o modelo errou" — foi descrita como "o modelo interpretou seu papel como assistente prestativo de logística em vez de leitor estrito de chunks". Isso demonstra compreensão do mecanismo de falha, não apenas do output incorreto.

2. **Distinção recusa total vs. resposta parcial:** O gap identificado entre v2 e v3.1 (o modelo tinha o multiplicador 1.8 mas recusou totalmente a pergunta 3) é um problema sutil que muitos participantes não perceberiam — e a correção foi precisa: introduzir o marcador ❓ como categoria separada da recusa.

3. **Hierarquia de fontes como solução de engenharia:** O problema da contaminação FAQ-03 vs. POL-001 foi resolvido com uma regra estrutural (hierarquia de tipos de documento), não com mais proibições genéricas. Isso demonstra pensamento de design, não apenas patching.

---

## Pontos de Melhoria

1. **Teste de contradição entre versões de documentos não foi executado:** O v3.1 tem a seção `# TRATAMENTO DE DOCUMENTOS CONTRADITÓRIOS`, mas nenhuma das 3 perguntas testadas acionou esse path (PROC-042-v1 vs. v2 no mesmo contexto). Uma Rodada 3 com chunk conflitante deliberadamente injetado teria validado esse guardrail — ou encontrado um novo gap.

2. **O arquivo `prompt-system-v1.md` não está referenciado no documento de engenharia:** Trata metadados de OCR e vigência com sofisticação maior que o v3.1, mas não está explicado como ele se relaciona com a iteração documentada. É uma versão paralela? Uma refatoração após o v3.1? Deixar isso ambíguo reduz a rastreabilidade do processo.

3. **Orçamento de contexto usa GPT-4o como referência:** A tabela de tokens cita "janela GPT-4o: 128.000 tokens". Se o projeto NovaTech usará Claude (como sugerido pela trilha), o orçamento deveria referenciar os modelos Claude — que têm janelas de 200K tokens — o que muda as margens de segurança na análise de context rot.

---

## Classificação

**Aprovado com distinção (3.0)**

---

## Tópicos da Trilha para Reforço

Não aplicável — score 3.0. Se houver interesse em aprofundamento, os pontos acima (teste de contradição entre versões e validação de guardrails menos exercitados) são extensões naturais para o Cenário 2.
