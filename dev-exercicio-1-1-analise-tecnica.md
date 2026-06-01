# Análise Técnica de Viabilidade — Pipeline de RAG NovaTech

**Exercício:** Desenvolvedor 1.1 — Análise de viabilidade técnica com fundamentos de LLM e engenharia de contexto  
**Projeto:** Assistente de IA para atendimento NovaTech  
**Data:** 28/05/2026

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
3. Nunca dividir uma tabela por limite de tokens — se a tabela exceder 500 tokens, expandir o limite do chunk para acomodá-la inteira.
4. Fluxogramas: processar com **GPT-4o Vision** para gerar descrição textual indexável.
5. Metadado obrigatório em cada chunk de tabela: `doc_id`, `versão`, `data_emissão`, `nome_da_seção`.

---

### 1.2 PDFs Escaneados (~15% da base = ~120 documentos)

**Desafio para o pipeline de RAG**

Documentos escaneados não contêm texto — contêm imagens de texto. O OCR introduz erros silenciosos: o pipeline ingere o resultado sem nenhum sinal de falha. Erros em caracteres numéricos são críticos em logística: `1.8` pode virar `l.8` ou `18`; `500kg` pode virar `500kq`. O embedding gerado a partir de texto com OCR ruim fica semanticamente correto (o retriever encontra o chunk), mas o valor retornado pelo LLM está errado.

Adicionalmente: tabelas em documentos escaneados têm bordas de células detectadas de forma inconsistente — o problema de estrutura tabular se soma ao problema de OCR.

**Impacto na qualidade das respostas**

Médio-alto. A falha é especialmente insidiosa porque o retriever continua funcionando corretamente (o chunk é encontrado), mas o conteúdo recuperado está corrompido. O LLM repete o erro com confiança.

**Estratégia de tratamento**

1. Pré-processamento com **Azure AI Document Intelligence (Read model)** — OCR com score de confiança por palavra.
2. Flagging automático: chunks com confiança média abaixo de 0,85 entram em fila de revisão humana antes de serem indexados.
3. Esses ~120 documentos devem ser priorizados na fase de curadoria — não entram automaticamente no índice.
4. Para fluxogramas: GPT-4o Vision para descrição textual associada ao documento.

---

### 1.3 Wiki Confluence com Links Internos e Macros Customizadas

**Desafio para o pipeline de RAG**

Links internos criam dependências de contexto: uma página wiki pode referenciar outra sem conter o conteúdo relevante. O chunk recuperado pelo retriever é um dead end — a resposta está em outro documento que pode ou não ser recuperado na mesma query.

Macros customizadas do Confluence (info boxes, `{include}`, `{table-of-contents}`) não são renderizadas no HTML exportado — aparecem como markup literal ou texto vazio, produzindo chunks com baixa densidade semântica que consomem orçamento de contexto sem contribuir com informação.

**Impacto na qualidade das respostas**

Médio. Chunks com links não resolvidos produzem respostas incompletas ou forçam o LLM a inferir o conteúdo do link referenciado (alucinação por gap de contexto). Macros não renderizadas reduzem a qualidade do embedding do chunk.

**Estratégia de tratamento**

1. Exportar via **Confluence REST API** (`/wiki/rest/api/content/{id}?expand=body.storage`) — formato de armazenamento, não HTML renderizado.
2. Resolver links internos: ao processar uma página, registrar IDs das páginas vinculadas como metadado `linked_pages`. O retriever pode usar esse grafo para busca em duas etapas quando necessário.
3. Macros `{include}`: substituir pelo conteúdo da página incluída no momento da ingestão. Macros desconhecidas: logar e pular.
4. Páginas com mais de 50% de conteúdo de macros não resolvidas: marcar para revisão manual antes de indexar.

---

### 1.4 Planilhas com Fórmulas Interdependentes

**Desafio para o pipeline de RAG**

Planilhas armazenam dois tipos de conteúdo: fórmulas (`=VLOOKUP(A1, TabelaFretes, 3, FALSE)`) e valores computados. Para o pipeline de RAG, apenas os valores computados têm significado semântico — fórmulas indexadas como texto não são recuperáveis por busca semântica para perguntas como "qual o valor do frete para 600kg no Sudeste?".

Fórmulas interdependentes entre abas criam um grafo de dependência que o pipeline de ingestão simples não rastreia. Uma célula pode exibir `1.3` porque referencia outra aba que pode não estar sendo exportada.

**Impacto na qualidade das respostas**

Alto para consultas numéricas. O retriever encontra os chunks (relevância semântica pela estrutura textual), mas o LLM não consegue extrair valores concretos de células com fórmulas. Pior: planilhas de referência mensais desatualizadas podem estar indexadas com valores do mês anterior sem nenhum alerta.

**Estratégia de tratamento**

1. Exportar via `openpyxl` com `data_only=True` — retorna valores computados, não fórmulas.
2. Cada aba = documento separado com metadados: nome do arquivo, nome da aba, data de exportação.
3. Converter para CSV limpo com cabeçalhos explícitos antes de gerar embeddings.
4. Para tabelas de referência mensais: trigger automático de reindexação quando novo arquivo é depositado na pasta de rede (event-driven, não manual).
5. Células com referências externas (`[OutroArquivo.xlsx]Aba!Célula`): sinalizar — o valor pode estar desatualizado se o arquivo de origem não estiver acessível no momento da exportação.

---

## 2. Estimativa de Tamanho da Base em Tokens

| Fonte | Cálculo | Palavras | Tokens (÷ 0,75) |
|---|---|---|---|
| 800 PDFs × 10 páginas × 250 palavras/pág | 800 × 2.500 | 2.000.000 | **~2.667.000** |
| 400 páginas wiki × 1.500 palavras | 400 × 1.500 | 600.000 | **~800.000** |
| 50 planilhas × 3 abas × 100 linhas × 8 colunas × 2 palavras/célula | 50 × 4.800 | 240.000 | **~320.000** |
| **Total** | | **~2.840.000** | **~3.787.000 (~3,8M tokens)** |

**Interpretação:** A base completa possui aproximadamente **3,8 milhões de tokens** — cerca de **30× maior** que a janela de contexto máxima do GPT-4o (128K tokens). Isso confirma que a abordagem RAG é necessária: enviar toda a documentação a cada query é tecnicamente inviável e economicamente inaceitável.

**Nota sobre a estimativa de planilhas:** A estimativa de 240.000 palavras pode ser conservadora. Planilhas de tabelas de frete com histórico mensal acumulado ou referências cruzadas entre abas podem ser significativamente maiores. Recomenda-se uma amostragem das planilhas reais antes de dimensionar o pipeline de ingestão.

---

## 3. Análise de Orçamento de Contexto

### Composição de contexto por query

| Componente | Natureza | Tokens estimados |
|---|---|---|
| System prompt + guardrails | Estático (toda query) | ~2.000 |
| Metadados do cliente (tier, contrato) | Dinâmico por sessão | ~150–200 |
| Histórico da conversa no Teams | Dinâmico crescente | 0 → ~8.000* |
| Pergunta do atendente | Dinâmico por query | ~30–100 |
| Chunks recuperados | Dinâmico por query | variável |

*Após 10 turnos de conversa, o histórico pode consumir ~8.000 tokens.

### Quantos chunks de 500 tokens cabem por query?

**Cenário inicial (primeira pergunta da sessão):**

```
128.000 − 2.000 (system) − 200 (metadados) − 100 (pergunta) = ~125.700 tokens disponíveis
125.700 ÷ 500 tokens/chunk = ~251 chunks (máximo teórico)
```

**Cenário realista (5ª pergunta de sessão longa no Teams):**

```
128.000 − 2.000 − 200 − 3.500 (histórico) − 100 = ~122.200 tokens disponíveis
122.200 ÷ 500 = ~244 chunks (ainda alto em termos absolutos)
```

### O limite real não é o token budget — é o efeito lost in the middle

Pesquisas (Liu et al., 2023) demonstram que LLMs prestam significativamente menos atenção a informações posicionadas no centro de contextos longos. Com 10+ chunks no contexto, a acurácia de recuperação de informação pode cair de ~95% (posições inicial e final) para ~50–60% (posição central). Enviar 20 chunks não é melhor que enviar 5 — pode ser pior, porque os chunks mais relevantes ficam enterrados no meio enquanto chunks irrelevantes ocupam posições de alta atenção.

### Impacto na estratégia de retrieval

- **Número de chunks recomendado:** 4–6 por query (2.000–3.000 tokens de conteúdo documental)
- **Ordenação no prompt:** chunk mais relevante na posição 1, segundo mais relevante na posição final, demais no meio (explorar os picos de atenção nas extremidades)
- **Gestão do histórico:** à medida que o histórico cresce na sessão do Teams, reduzir o número de chunks recuperados proporcionalmente — preservar orçamento para conteúdo crítico
- **Reranking:** após retrieval por similaridade semântica (top 20 candidatos), aplicar reranker cross-encoder para selecionar os top 5 mais relevantes antes de construir o prompt final

---

## 4. Estratégia de Chunking Recomendada

### Por que chunking fixo de 512 tokens é inadequado para a NovaTech

**Problema 1 — Corte de tabelas:** A tabela de multiplicadores da PROC-042-v2 tem ~150 tokens. Com chunking fixo de 512, ela será combinada com conteúdo textual da seção anterior ou posterior. Se a tabela começa próxima ao limite de tokens de uma seção anterior, pode ser cortada ao meio: cabeçalhos em um chunk, valores em outro.

**Problema 2 — Fragmentação de regras de exceção:** A seção 3.2 da POL-001 lista 3 categorias de carga não elegíveis para devolução. Com chunking fixo, a terceira categoria pode ficar em um chunk separado, sem o cabeçalho "NÃO são elegíveis". O LLM, ao receber esse chunk isolado, pode interpretar a categoria como elegível — invertendo a regra.

**Problema 3 — Documentos contraditórios sem metadado de versão:** Os multiplicadores da PROC-042 v1 e v2 podem ser recuperados juntos numa mesma query sobre frete. Sem metadado de versão explícito no chunk, o LLM não tem base para distinguir qual valor é vigente.

### Estratégia recomendada: Chunking semântico por seção com metadados de versão

**Regra de chunking:**

- Unidade base = subseção delimitada por heading (ex: `#### 3.2. Exceções ao prazo geral`)
- Se a subseção couber em 600 tokens: chunk único
- Se exceder 600 tokens: dividir em parágrafos com overlap de 80–100 tokens nas fronteiras (não cortar no meio de frases, listas ou tabelas)
- Tabelas: sempre chunk independente, nunca dividir

**Metadados obrigatórios em cada chunk:**

```json
{
  "doc_id": "PROC-042-v2",
  "versao": "2.0",
  "data_emissao": "2023-11-10",
  "secao_path": "PROC-042-v2 > Seção 2 > 2.1",
  "titulo_secao": "Multiplicadores regionais (atualizados em novembro/2023)",
  "tipo_conteudo": "tabela",
  "status_documento": "sem_indicacao_vigencia"
}
```

**Tratamento especial para documentos contraditórios (PROC-042 v1 e v2):**

1. Ambas as versões são indexadas — não descartar a v1 automaticamente (pode ser necessária para chamados em transição, conforme seção 5 da v2)
2. O system prompt instrui o LLM a priorizar a versão com data mais recente quando houver conflito de valores
3. O texto de cada chunk inclui aviso explícito: `[ATENÇÃO: existe versão anterior PROC-042-v1 (2023-03-03) com multiplicadores diferentes. Versão atual: PROC-042-v2 (2023-11-10)]`
4. Quando os dois chunks são recuperados na mesma query, o LLM deve apresentar ambos os valores ao atendente com indicação de versão — não silenciosamente escolher um

### Justificativa pelo tipo de pergunta

As perguntas dos atendentes da NovaTech são temáticas e procedurais: "qual o prazo de devolução para carga refrigerada?", "como calcular frete especial para 600kg no Norte?", "qual o SLA de resolução para cliente Gold?". Elas mapeiam diretamente para seções específicas de documentos.

O chunking por seção semântica maximiza a probabilidade de que o chunk correto contenha a resposta completa dentro de um único chunk, reduzindo a necessidade de múltiplos chunks por query e mitigando diretamente o efeito lost in the middle.

Com chunks fixos de 512 tokens, uma pergunta sobre devolução de carga perigosa poderia exigir 2–3 chunks para reconstituir a regra completa (seção 3.1 com o prazo geral + seção 3.2 com a exceção). Com chunking por seção, a seção 3.2 inteira — incluindo a lista de exceções e o ramal 4500 para Gestão de Riscos — está em um único chunk autocontido.
