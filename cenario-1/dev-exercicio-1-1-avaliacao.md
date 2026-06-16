# Avaliação — Exercício 1.1
**Papel:** Desenvolvedor | **Cenário:** 1 — Entendimento e Contexto | **Exercício:** 1.1 — Análise de Viabilidade Técnica com Fundamentos de LLM e Engenharia de Contexto

---

## Resumo

O entregável produz dois documentos: uma análise inicial (v1) e uma versão revisada pós devil's advocate (v2, 10 seções). A v2 expande substantivamente a v1 — passa de 4 para 10 seções, corrige decisões técnicas incorretas (Read model → Layout model para escaneados), ajusta o ratio de tokenização para português e suspende a estimativa de planilhas com recomendação de amostragem prévia. O resultado final é uma análise de viabilidade utilizável como insumo real de arquitetura, com custo, latência, métricas de avaliação e decisões pendentes documentadas.

---

## Scores por Dimensão

| Dimensão | Score | Justificativa |
|---|---|---|
| D1 — Domínio Conceitual | **3** | Demonstra compreensão dos mecanismos de falha, não apenas dos sintomas: linearização de tabelas quebrando relação coluna-valor, OCR silencioso corrompendo conteúdo sem sinal de falha, fragmentação semântica de listas de exceção invertendo a semântica ("NÃO elegível" separado do cabeçalho → LLM interpreta como elegível). O ajuste do ratio de 0,75 para 0,70 para português em v2 mostra profundidade técnica real. Ponto de atenção: estimativa de tokens de ~3,8M fica abaixo da faixa esperada (8–15M na rubrica), provavelmente por usar 250 palavras/página — conservador para documentos técnicos densos. |
| D2 — Uso de Ferramentas | **3** | A v2 é explicitamente rotulada como "revisão pós devil's advocate" e as mudanças são concretas e rastreáveis: correção do modelo Azure DI (Read → Layout para escaneados), suspend da estimativa de planilhas com recomendação de amostragem, nova estratégia de chunking para escaneados sem headings, adição de `version.when` para detecção incremental no Confluence, e seções inteiras novas (5 a 10). O ciclo identificação → incorporação é verificável pela comparação entre os dois arquivos. |
| D3 — Qualidade do Entregável | **3** | A v2 está completa e utilizável por outro engenheiro sem esclarecimentos: inclui tabela de latência por estágio, métricas com metas iniciais (Recall@5 ≥ 85%, Hallucination Rate ≤ 5%), estratégia de fallback com threshold explícito (cosine similarity < 0,75), custo estimado de ingestão e por query, e seção de decisões pendentes com responsável sugerido. Específico ao NovaTech — referencia PROC-042, POL-001, Azure stack, sessões do Teams. |
| D4 — Pensamento Crítico | **3** | Insights não-óbvios presentes: (a) listas com cabeçalho semântico crítico (negação, exceção) tratadas como unidades indivisíveis — igual a tabelas; (b) "a magnitude exata do lost in the middle para GPT-4o deve ser validada empiricamente" — não aceita Liu et al. 2023 como verdade absoluta; (c) reordenação de chunks nas extremidades "requer implementação customizada — LangChain e LlamaIndex não expõem essa lógica nativamente"; (d) suspender estimativa de planilhas ao invés de inventar um número é julgamento correto. |
| D5 — Aplicabilidade ao Projeto | **3** | Todos os exemplos são âncoras NovaTech: PROC-042-v2 seção 2.1 como caso concreto de tabela linearizada incorretamente, POL-001 seção 3.2 como caso concreto de fragmentação semântica, Azure DI como stack consistente com infraestrutura já mencionada. O volume de 500 queries/dia é assumido explicitamente na estimativa de custo operacional — rastreável. |

**Score do exercício: 3.0**

---

## Verificação de Armadilhas

Nenhuma armadilha obrigatória listada para este exercício na skill do Desenvolvedor.

---

## Pontos Fortes

1. **Problema de fragmentação semântica antecipado com precisão:** A identificação de que chunking fixo pode separar o cabeçalho "NÃO são elegíveis" do corpo da lista — invertendo a semântica da regra — é o tipo de risco que só aparece quando o participante pensa nos documentos reais da NovaTech, não em documentos genéricos. Esse insight antecipa diretamente a armadilha do exercício 1.2.

2. **Decisões explicitamente não tomadas por falta de informação:** A suspensão da estimativa de planilhas com recomendação de amostragem, a latência do reranker marcada como "decisão de arquitetura pendente", e a seção 10 com tabela de decisões pendentes mostram maturidade de engenharia — saber o que não se sabe é tão importante quanto o que se sabe.

3. **Iteração cirúrgica, não reescrita:** A v2 corrige erros específicos da v1 (modelo Azure DI, ratio de tokenização, estratégia de escaneados) sem descartar o que funcionou. A progressão é rastreável e cada mudança tem justificativa técnica.

---

## Pontos de Melhoria

1. **Estimativa de tokens subestimada:** O total de ~3,8M tokens fica abaixo da faixa razoável para o volume da NovaTech (~8–15M). A raiz é o uso de 250 palavras/página — conservador para documentos técnicos procedurais (PDFs de procedimentos de frete têm tipicamente 400–600 palavras/página). A v2 reconhece incerteza para planilhas, mas não revisita os PDFs. Uma re-estimativa com 450 palavras/página e amostragem real de 2–3 PDFs teria fechado o gap.

2. **Estratégia de reordenação de chunks não detalhada:** A recomendação de posicionar o chunk mais relevante na posição 1 e o segundo mais relevante na posição final é correta, mas a observação de que "LangChain e LlamaIndex não expõem essa lógica nativamente" fica em aberto — sem indicar como implementar. Uma nota sobre a abordagem (ex: construção manual da lista de mensagens antes de passar ao LLM) completaria o raciocínio.

3. **Ausência de transcript do devil's advocate:** A v2 referencia a sessão com Claude, mas não há log ou resumo das perguntas que geraram as correções. Para fins de rastreabilidade da trilha, documentar as 3–5 perguntas do devil's advocate que produziram as mudanças mais impactantes tornaria o processo reproduzível por outros participantes.

---

## Classificação

**Aprovado com distinção (3.0)**

---

## Tópicos da Trilha para Reforço

Não aplicável — score 3.0.
