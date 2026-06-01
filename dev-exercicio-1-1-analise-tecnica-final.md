# Análise Técnica de Viabilidade — Pipeline de RAG NovaTech

**Exercício:** Desenvolvedor 1.1 — Análise de viabilidade técnica com fundamentos de LLM e engenharia de contexto  
**Projeto:** Assistente de IA para atendimento NovaTech  
**Data:** 28/05/2026  
**Versão:** 2.0 (revisão pós devil's advocate)

---

## 1. Análise por Tipo de Fonte

### 1.1 PDFs com Tabelas Complexas (15+ colunas)

**Desafio para o pipeline de RAG**

Ferramentas padrão de extração de texto (PyMuPDF, pdfplumber) linearizam tabelas: transformam estrutura bidimensional em sequência de tokens, quebrando a relação coluna–valor. Uma tabela de multiplicadores de frete com 5 colunas pode se tornar `"Sul 1.3 Sudeste 1.1 Norte 1.8"` — sem os cabeçalhos, os valores perdem referência.

Evidência concreta: a PROC-042-v2 (seção 2.1) contém a tabela de multiplicadores regionais. Extraída sem estrutura, um chunk poderia conter apenas os valores numéricos sem o cabeçalho "Região | Multiplicador". O LLM ao receber esse chunk pode associar o valor `1.1` à região errada, gerando erros de cálculo de frete com aparência de resposta correta.

Fluxogramas embutidos como imagens são completamente ignorados pela extração de texto padrão — seu conteúdo é silenciosamente perdido.

**Impacto na qualidade das respostas**

Alto. Erros em tabelas de frete são especialmente perigosos: a resposta parece bem formatada e confiante, mas o valor numérico está atribuído à região errada. O atendente não tem como detectar o erro sem consultar o documento original — o que elimina o benefício do assistente.

**Estratégia de tratamento**

1. Usar **Azure AI Document Intelligence (Layout model)** para extração com reconhecimento de estrutura tabular — retorna tabelas como JSON com cabeçalhos preservados.
2. Cada tabela = chunk independente, sempre com a linha de cabeçalho incluída no texto do chunk.
3. Nunca dividir uma tabela por limite de tokens. Se a tabela exceder **2.000 tokens (teto máximo)**, dividir horizontalmente por grupos de linhas com o cabeçalho completo repetido em cada sub-chunk. Tabelas acima de 2.000 tokens sem divisão lógica natural são candidatas a revisão manual de estrutura.
4. Fluxogramas: processar com **GPT-4o Vision** para gerar descrição textual indexável.
5. Metadado obrigatório em cada chunk de tabela: `doc_id`, `versão`, `data_emissão`, `nome_da_seção`.

---

### 1.2 PDFs Escaneados (~15% da base = ~120 documentos)

**Desafio para o pipeline de RAG**

Documentos escaneados não contêm texto — contêm imagens de texto. O OCR introduz erros silenciosos: o pipeline ingere o resultado sem nenhum sinal de falha. Erros em caracteres numéricos são críticos em logística: `1.8` pode virar `l.8` ou `18`; `500kg` pode virar `500kq`. O embedding gerado a partir de texto com OCR ruim fica semanticamente correto (o retriever encontra o chunk), mas o valor retornado pelo LLM está errado.

Adicionalmente: tabelas em documentos escaneados têm bordas de células detectadas de forma inconsistente — o problema de estrutura tabular se soma ao problema de OCR. Documentos escaneados tipicamente não possuem headings digitais estruturados, o que **inviabiliza o chunking semântico por seção** descrito na seção 4. Esse é um caso especial que exige estratégia de chunking própria.

**Impacto na qualidade das respostas**

Médio-alto. A falha é especialmente insidiosa porque o retriever continua funcionando corretamente (o chunk é encontrado), mas o conteúdo recuperado está corrompido. O LLM repete o erro com confiança.

**Estratégia de tratamento**

1. Pré-processamento com **Azure AI Document Intelligence (Layout model)** — OCR com score de confiança por palavra e detecção de estrutura tabular. O Layout model é necessário (não o Read model) para viabilizar a detecção de seções e tabelas nesses documentos.
2. Flagging automático: chunks com confiança média abaixo de 0,85 entram em fila de revisão humana antes de serem indexados.
3. **Chunking alternativo para escaneados:** chunking por parágrafo com overlap de 100 tokens, sem dependência de heading estruturado. Tabelas detectadas pelo Layout model seguem a mesma regra de chunk independente da seção 1.1.
4. Esses ~120 documentos devem ser priorizados na fase de curadoria — não entram automaticamente no índice.
5. Para fluxogramas: GPT-4o Vision para descrição textual associada ao documento.

---

### 1.3 Wiki Confluence com Links Internos e Macros Customizadas

**Desafio para o pipeline de RAG**

Links internos criam dependências de contexto: uma página wiki pode referenciar outra sem conter o conteúdo relevante. O chunk recuperado pelo retriever é um dead end — a resposta está em outro documento que pode ou não ser recuperado na mesma query.

Macros customizadas do Confluence (info boxes, `{include}`, `{table-of-contents}`) não são renderizadas no HTML exportado — aparecem como markup literal ou texto vazio, produzindo chunks com baixa densidade semântica que consomem orçamento de contexto sem contribuir com informação. O formato de armazenamento (`body.storage`) retorna XML com tags e macros que requerem parser específico de Confluence — não é suficiente apenas remover tags HTML.

**Impacto na qualidade das respostas**

Médio. Chunks com links não resolvidos produzem respostas incompletas ou forçam o LLM a inferir o conteúdo do link referenciado (alucinação por gap de contexto). Macros não renderizadas reduzem a qualidade do embedding do chunk.

**Estratégia de tratamento**

1. Exportar via **Confluence REST API** (`/wiki/rest/api/content/{id}?expand=body.storage`) — formato de armazenamento, não HTML renderizado.
2. Usar parser de **Confluence Storage Format** (ex: `confluencetables` ou implementação customizada) para converter XML em texto limpo antes de gerar embeddings — não é suficiente strip de tags HTML.
3. Resolver links internos: ao processar uma página, registrar IDs das páginas vinculadas como metadado `linked_pages`. O retriever pode usar esse grafo para busca em duas etapas quando necessário.
4. Macros `{include}`: substituir pelo conteúdo da página incluída no momento da ingestão. Macros desconhecidas: logar e pular.
5. **Detecção de documentos alterados:** usar campo `version.when` da REST API para filtrar páginas modificadas desde a última execução — evitar reindexação total a cada ciclo.
6. Páginas com mais de 50% de conteúdo de macros não resolvidas: marcar para revisão manual antes de indexar.

---

### 1.4 Planilhas com Fórmulas Interdependentes

**Desafio para o pipeline de RAG**

Planilhas armazenam dois tipos de conteúdo: fórmulas (`=VLOOKUP(A1, TabelaFretes, 3, FALSE)`) e valores computados. Para o pipeline de RAG, apenas os valores computados têm significado semântico — fórmulas indexadas como texto não são recuperáveis por busca semântica para perguntas como "qual o valor do frete para 600kg no Sudeste?".

Fórmulas interdependentes entre abas criam um grafo de dependência que o pipeline de ingestão simples não rastreia. Uma célula pode exibir `1.3` porque referencia outra aba que pode não estar sendo exportada.

**Impacto na qualidade das respostas**

Alto para consultas numéricas. O retriever encontra os chunks (relevância semântica pela estrutura textual), mas o LLM não consegue extrair valores concretos de células com fórmulas. Pior: planilhas de referência mensais desatualizadas podem estar indexadas com valores do mês anterior sem nenhum alerta.

**Estratégia de tratamento**

1. **Amostrar 5–10 planilhas reais** antes de finalizar o dimensionamento do pipeline: medir min/max/p95 de linhas por aba. Tabelas de frete com histórico acumulado podem ter milhares de linhas por aba — a estimativa padrão de 100 linhas/aba é conservadora por ordem de grandeza para esse tipo de conteúdo.
2. Exportar via `openpyxl` com `data_only=True` — retorna valores computados, não fórmulas.
3. Cada aba = documento separado com metadados: nome do arquivo, nome da aba, data de exportação.
4. Converter para CSV limpo com cabeçalhos explícitos antes de gerar embeddings.
5. Para tabelas de referência mensais: trigger automático de reindexação quando novo arquivo é depositado na pasta de rede (event-driven, não manual).
6. Células com referências externas (`[OutroArquivo.xlsx]Aba!Célula`): sinalizar — o valor pode estar desatualizado se o arquivo de origem não estiver acessível no momento da exportação.
7. **Detecção de alterações:** hash SHA-256 do arquivo na ingestão; comparar em cada execução agendada para reindexar apenas arquivos modificados.

---

## 2. Estimativa de Tamanho da Base em Tokens

| Fonte | Cálculo | Palavras | Tokens (÷ 0,70)* |
|---|---|---|---|
| 800 PDFs × 10 páginas × 250 palavras/pág | 800 × 2.500 | 2.000.000 | **~2.857.000** |
| 400 páginas wiki × 1.500 palavras | 400 × 1.500 | 600.000 | **~857.000** |
| 50 planilhas × estimativa a validar** | a confirmar | a confirmar | **a confirmar** |
| **Total (sem planilhas)** | | **~2.600.000** | **~3.714.000** |

> \* O divisor padrão de 0,75 (palavras/tokens) é calibrado para inglês. Conteúdo em português com tokenização BPE (GPT-4/GPT-4o) apresenta ratio de 0,68–0,72 devido à morfologia mais longa e caracteres especiais (ã, ç, ê). Usar 0,70 como estimativa conservadora; validar com `tiktoken` sobre amostra real.

> \*\* **Estimativa de planilhas suspensa até amostragem.** Tabelas de frete com histórico acumulado mensal podem ter 1.000–24.000 linhas por aba (10 regiões × 20 faixas de peso × 12 meses = 2.400 combinações/ano). Recomendar amostragem de 5–10 planilhas reais antes de dimensionar o pipeline de ingestão e o vector store.

**Interpretação:** A base de PDFs + wiki possui aproximadamente **3,7 milhões de tokens** — cerca de **29× maior** que a janela de contexto máxima do GPT-4o (128K tokens). Isso confirma que a abordagem RAG é necessária. O volume real, incluindo planilhas, depende da amostragem recomendada acima.

---

## 3. Análise de Orçamento de Contexto

### Composição de contexto por query

| Componente | Natureza | Tokens estimados |
|---|---|---|
| System prompt + guardrails | Estático (toda query) | ~2.000 |
| Metadados do cliente (tier, contrato) | Dinâmico por sessão | ~150–200 |
| Histórico da conversa no Teams | Dinâmico crescente | 0 → ~18.000* |
| Pergunta do atendente | Dinâmico por query | ~30–100 |
| Chunks recuperados | Dinâmico por query | variável |

> \* Sessões longas (15–20 turnos) são comuns em atendimentos de disputa logística. Com respostas detalhadas de 600–1.000 tokens por turno, o histórico pode consumir 15.000–18.000 tokens — não os 8.000 estimados para sessões curtas. Ver política de truncação abaixo.

### Política de gestão do histórico (sessões longas)

Quando o histórico ultrapassar **8.000 tokens** (aproximadamente 10 turnos), acionar sumarização automática: os turnos mais antigos são comprimidos por uma chamada LLM separada (modelo menor, ex: GPT-4o-mini) gerando um resumo de ~500 tokens. O prompt passa a conter: resumo comprimido + últimos 3 turnos completos + query atual.

Custo estimado da sumarização: ~1.500 tokens de input × $0,00015/1K = ~$0,0002 por ativação. Latência adicional: ~300–500ms; aceitável por ocorrer apenas a cada 10 turnos.

### Quantos chunks de 500 tokens cabem por query?

```
Cenário inicial (primeira pergunta da sessão):
128.000 − 2.000 (system) − 200 (metadados) − 100 (pergunta) = ~125.700 tokens disponíveis

Cenário realista (5ª pergunta, histórico de 3.500 tokens):
128.000 − 2.000 − 200 − 3.500 (histórico) − 100 = ~122.200 tokens disponíveis

Cenário sessão longa (15º turno, histórico comprimido de 500 tokens + 3 turnos recentes de 2.400 tokens):
128.000 − 2.000 − 200 − 2.900 − 100 = ~122.800 tokens disponíveis
```

### O limite real não é o token budget — é o efeito lost in the middle

Pesquisas (Liu et al., 2023) demonstram que LLMs prestam significativamente menos atenção a informações posicionadas no centro de contextos longos. Com 10+ chunks no contexto, a acurácia de recuperação de informação pode cair de ~95% (posições inicial e final) para ~50–60% (posição central). Enviar 20 chunks não é melhor que enviar 5 — pode ser pior, porque os chunks mais relevantes ficam enterrados no meio enquanto chunks irrelevantes ocupam posições de alta atenção.

> **Nota:** o fenômeno foi documentado com modelos anteriores ao GPT-4o. A magnitude exata para o GPT-4o deve ser validada empiricamente com o benchmark de avaliação descrito na seção 6.

### Impacto na estratégia de retrieval

- **Número de chunks recomendado:** 4–6 por query (2.000–3.000 tokens de conteúdo documental)
- **Ordenação no prompt:** chunk mais relevante na posição 1, segundo mais relevante na posição final, demais no meio. Essa reordenação **requer implementação customizada** — LangChain e LlamaIndex não expõem essa lógica nativamente. Validar com benchmark antes de comprometer com a implementação.
- **Gestão do histórico:** aplicar política de sumarização descrita acima; não apenas "reduzir chunks proporcionalmente"
- **Reranking:** após retrieval por similaridade semântica (top-20 candidatos), aplicar reranker para selecionar os top-5 mais relevantes antes de construir o prompt final. Ver seção 5 para discussão de latência.
- **Threshold de similaridade mínimo:** rejeitar chunks com cosine similarity < 0,75 e acionar fallback descrito na seção 7.

---

## 4. Estratégia de Chunking Recomendada

### Por que chunking fixo de 512 tokens é inadequado para a NovaTech

**Problema 1 — Corte de tabelas:** A tabela de multiplicadores da PROC-042-v2 tem ~150 tokens. Com chunking fixo de 512, ela será combinada com conteúdo textual da seção anterior ou posterior. Se a tabela começa próxima ao limite de tokens de uma seção anterior, pode ser cortada ao meio: cabeçalhos em um chunk, valores em outro.

**Problema 2 — Fragmentação de regras de exceção e listas:** A seção 3.2 da POL-001 lista 3 categorias de carga não elegíveis para devolução. Com chunking fixo, a terceira categoria pode ficar em um chunk separado sem o cabeçalho "NÃO são elegíveis". O LLM, ao receber esse chunk isolado, pode interpretar a categoria como elegível — invertendo a regra. O mesmo risco se aplica a qualquer lista ordenada/não-ordenada com cabeçalho semântico crítico (negação, condicional, exceção).

**Problema 3 — Documentos contraditórios sem metadado de versão:** Os multiplicadores da PROC-042 v1 e v2 podem ser recuperados juntos numa mesma query sobre frete. Sem metadado de versão explícito no chunk, o LLM não tem base para distinguir qual valor é vigente.

### Estratégia recomendada: Chunking semântico por seção com metadados de versão

**Regra de chunking — PDFs digitais com headings:**

- Unidade base = subseção delimitada por heading (ex: `#### 3.2. Exceções ao prazo geral`)
- Se a subseção couber em 600 tokens: chunk único
- Se exceder 600 tokens: dividir em parágrafos com overlap de 80–100 tokens nas fronteiras (não cortar no meio de frases, listas ou tabelas)
- Tabelas: sempre chunk independente, nunca dividir; teto de 2.000 tokens (ver seção 1.1)
- **Listas com cabeçalho semântico crítico** (negação, exceção, condicional): tratar como unidade indivisível, igual a tabelas

**Regra de chunking — PDFs escaneados (sem headings confiáveis):**

- Chunking por parágrafo com overlap de 100 tokens
- Tabelas detectadas pelo Layout model seguem a mesma regra de chunk independente

**Metadados obrigatórios em cada chunk:**

```json
{
  "doc_id": "PROC-042-v2",
  "versao": "2.0",
  "data_emissao": "2023-11-10",
  "secao_path": "PROC-042-v2 > Seção 2 > 2.1",
  "titulo_secao": "Multiplicadores regionais (atualizados em novembro/2023)",
  "tipo_conteudo": "tabela",
  "vigencia_confirmada": false,
  "substituido_por": null,
  "hash_conteudo": "sha256:abc123..."
}
```

O campo `vigencia_confirmada` é boolean filtrável. O campo `substituido_por` permite encadear versões (ex: chunks da PROC-042-v1 terão `"substituido_por": "PROC-042-v2"`). O campo `hash_conteudo` permite detecção de duplicatas e controle de reindexação incremental.

**Tratamento especial para documentos contraditórios (PROC-042 v1 e v2):**

1. Ambas as versões são indexadas — não descartar a v1 automaticamente (pode ser necessária para chamados em transição, conforme seção 5 da v2)
2. O system prompt instrui o LLM a priorizar a versão com data mais recente quando houver conflito de valores
3. O texto de cada chunk inclui aviso explícito: `[ATENÇÃO: existe versão anterior PROC-042-v1 (2023-03-03) com multiplicadores diferentes. Versão atual: PROC-042-v2 (2023-11-10)]`
4. Quando os dois chunks são recuperados na mesma query, o LLM deve apresentar ambos os valores ao atendente com indicação de versão — não silenciosamente escolher um

### Justificativa pelo tipo de pergunta

As perguntas dos atendentes da NovaTech são temáticas e procedurais: "qual o prazo de devolução para carga refrigerada?", "como calcular frete especial para 600kg no Norte?", "qual o SLA de resolução para cliente Gold?". Elas mapeiam diretamente para seções específicas de documentos.

O chunking por seção semântica maximiza a probabilidade de que o chunk correto contenha a resposta completa dentro de um único chunk, reduzindo a necessidade de múltiplos chunks por query e mitigando diretamente o efeito lost in the middle.

Com chunks fixos de 512 tokens, uma pergunta sobre devolução de carga perigosa poderia exigir 2–3 chunks para reconstituir a regra completa (seção 3.1 com o prazo geral + seção 3.2 com a exceção). Com chunking por seção, a seção 3.2 inteira — incluindo a lista de exceções e o ramal 4500 para Gestão de Riscos — está em um único chunk autocontido.

---

## 5. Estratégia de Retrieval e Reranking

### Latência do pipeline e SLA

| Estágio | Latência estimada | Observação |
|---|---|---|
| Embedding da query | 50–100ms | API call, baixa latência |
| Vector search (top-20) | 20–50ms | Depende do vector store |
| Reranker (top-20 → top-5) | 200–500ms | Cross-encoder; ponto crítico |
| Construção do prompt | <10ms | Local |
| LLM inference (GPT-4o) | 1.000–3.000ms | Maior variável |
| **Total estimado** | **1,3–3,7 segundos** | — |

Para atendimento ao cliente com atendente aguardando ativamente, recomendar SLA de resposta ≤ 3 segundos (P95). Se o SLA for mais restritivo (≤ 2 segundos), o cross-encoder reranker deve ser substituído por reranker bi-encoder leve ou API de reranking otimizada para latência (ex: Cohere Rerank com endpoint de baixa latência).

> **Decisão de arquitetura pendente:** definir o SLA de latência antes de comprometer com a escolha do reranker.

### Estratégia de deduplicação

Documentos com o mesmo conteúdo aparecem em múltiplas fontes (ex: tabela de multiplicadores no PDF procedimento, no wiki e no material de treinamento). Sem deduplicação, o retriever retorna 3 chunks quase idênticos consumindo budget de contexto com redundância — e se uma cópia estiver desatualizada, o LLM pode gerar resposta inconsistente.

**Estratégia:** calcular hash SHA-256 do conteúdo de cada chunk. Chunks com similaridade cosseno > 0,98 entre si são candidatos a deduplicação — manter apenas o do documento canônico por hierarquia de fontes: PDF de procedimento > wiki > material de treinamento.

---

## 6. Avaliação do Pipeline

Sem um conjunto de avaliação formal, qualquer mudança de configuração (tamanho do chunk, modelo de embedding, número de chunks) é um experimento às cegas.

### Conjunto de avaliação mínimo

Criar 80–100 pares query–resposta correta a partir da base documental real, com anotação do chunk gold que contém a resposta. Distribuição recomendada:

- 30% perguntas sobre valores numéricos (frete, prazos, multiplicadores)
- 30% perguntas sobre regras e exceções (elegibilidade, SLA por tier)
- 20% perguntas que cruzam versões de documentos (PROC-042 v1 vs. v2)
- 20% perguntas cujas respostas não estão na base (para testar o fallback)

### Métricas mínimas

| Métrica | Definição | Meta inicial |
|---|---|---|
| Recall@5 | Chunk gold está nos top-5 recuperados? | ≥ 85% |
| Answer Faithfulness | Resposta está ancorada no chunk recuperado? | ≥ 90% |
| Hallucination Rate | Resposta contém informação não presente nos chunks? | ≤ 5% |
| Latência P95 | Tempo total da query ao início da resposta | ≤ SLA definido |
| Fallback Rate | % de queries que ativam o fallback por baixa similaridade | monitorar |

Executar o benchmark antes e depois de qualquer mudança de configuração do pipeline.

---

## 7. Estratégia de Fallback

Quando o retriever não encontra chunks suficientemente relevantes, o LLM não deve fabricar uma resposta.

**Regra de fallback:** se nenhum chunk recuperado tiver cosine similarity ≥ 0,75 com a query, ou se os top-5 chunks tiverem score médio < 0,70:

1. Não passar os chunks de baixa relevância para o LLM
2. Retornar resposta padrão ao atendente: *"Não encontrei informação suficiente na base de conhecimento para responder com segurança. Verificar com [contato/ramal específico por tipo de questão]."*
3. Logar a query, os scores e o timestamp para análise posterior — queries que ativam o fallback indicam lacunas na base documental

Essa resposta é mais segura que uma resposta fabricada pelo LLM com aparência de confiança.

---

## 8. Reindexação Incremental

### Estratégia por fonte

| Fonte | Detecção de alteração | Frequência sugerida |
|---|---|---|
| PDFs (pasta de rede) | Hash SHA-256 do arquivo | Verificação diária; reindexação apenas de arquivos com hash alterado |
| Confluence | Campo `version.when` da REST API | Verificação a cada 6 horas; reindexar páginas modificadas desde última execução |
| Planilhas | Hash SHA-256 + event-driven trigger | Trigger imediato ao depositar novo arquivo; verificação diária como fallback |

### Reindexação total vs. incremental

**Reindexação total (toda a base):** necessária apenas quando o modelo de embedding for substituído. Com ~3,7M tokens (PDFs + wiki) a ~$0,02/1M tokens, custa ~$0,07 em embeddings — o custo dominante é o processamento Azure DI (~$80 para 8.000 páginas de PDFs). Tempo estimado: ~67 minutos apenas para extração via Azure DI.

**Reindexação incremental (documentos alterados):** operação rotineira. Manter log de `doc_id` + hash + timestamp de última indexação para comparação.

> **Atenção:** se o modelo de embedding for atualizado, todo o vector store precisa ser reindexado do zero. O modelo deve ser fixado na documentação de arquitetura e mudanças coordenadas com planejamento de downtime ou índice em paralelo.

---

## 9. Estimativa de Custo Operacional

### Ingestão inicial

| Componente | Volume | Custo estimado |
|---|---|---|
| Azure DI Layout — PDFs digitais | ~6.400 págs (800 PDFs × 8 págs úteis) | ~$64 |
| Azure DI Layout — PDFs escaneados | ~1.200 págs (120 docs × 10 págs) | ~$12 |
| GPT-4o Vision — fluxogramas | ~120 imagens | ~$5–10 |
| Embeddings — PDFs + wiki (text-embedding-3-small) | ~3,7M tokens | ~$0,07 |
| **Total ingestão inicial** | | **~$81–86** |

### Custo por query em produção

| Componente | Custo por query |
|---|---|
| Embedding da query | ~$0,000001 |
| Reranker (Cohere Rerank — 20 candidatos) | ~$0,001 |
| GPT-4o — contexto de 4K tokens + resposta 500 tokens | ~$0,02–0,05 |
| **Total por query** | **~$0,021–0,051** |

Com 500 queries/dia: **~$10–26/dia (~$300–780/mês)** em custos de inferência, excluindo hospedagem do vector store e infraestrutura.

---

## 10. Resumo de Decisões Pendentes

| Decisão | Impacto | Quem decide |
|---|---|---|
| SLA de latência de resposta | Define viabilidade do cross-encoder reranker | Tech Lead + PO |
| Modelo de embedding (fixar versão) | Mudança futura = reindexação total | Arquiteto |
| Amostragem de planilhas reais | Dimensiona vector store e custo de ingestão | Engenheiro de dados |
| Hierarquia canônica de fontes para deduplicação | Define qual cópia é mantida em duplicatas | Tech Lead + negócio |
