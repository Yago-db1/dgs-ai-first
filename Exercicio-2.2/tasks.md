# Tasks — Query Endpoint

> Gerado a partir de `plan.md` via SDD.  
> Aprovação necessária do Tech Lead antes de iniciar qualquer implementação (Gate 2).

---

## Legenda
- **Estimativa:** P = pequeno (< 2h) | M = médio (2–4h) | G = grande (> 4h)  
- **Status:** `[ ]` pendente | `[x]` concluído | `[~]` em andamento

---

## TASK-001 — Definir tipos TypeScript do domínio

**Arquivo:** `src/shared/types.ts`  
**Estimativa:** P  
**Dependências:** nenhuma

**Descrição:**  
Definir as interfaces e tipos TypeScript que representam o contrato do query endpoint e seus serviços internos. Estes tipos são a base para todos os outros módulos.

**Tipos a criar:**
- `QueryRequest` — input do POST /api/query
- `QueryResponse` — output estruturado com `source_document`
- `SearchChunk` — chunk retornado pelo Azure AI Search
- `SourceDocument` — referência de fonte (id, title, section, vigency)
- `PromptContext` — estrutura montada antes do envio ao modelo
- `ConfidenceLevel` — enum: `HIGH | LOW | NOT_FOUND`

**Critérios de aceite:**
- [ ] Todos os tipos exportados em `src/shared/types.ts`
- [ ] `QueryResponse` obrigatoriamente contém o campo `source_document` (não opcional)
- [ ] `SourceDocument` contém campos: `document_id`, `title`, `section`, `vigency_date`
- [ ] Nenhum tipo usa `any` — TypeScript strict mode sem supressões
- [ ] Tipos compilam sem erros com `tsc --noEmit`

---

## TASK-002 — Implementar configuração de ambiente

**Arquivo:** `src/shared/config.ts`  
**Estimativa:** P  
**Dependências:** nenhuma

**Descrição:**  
Centralizar leitura de variáveis de ambiente com validação na inicialização. Falha rápida (fail-fast) se variável obrigatória estiver ausente — nunca silenciar configuração ausente.

**Variáveis obrigatórias:**
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT_NAME` (GPT-4o)
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`
- `AZURE_SEARCH_ENDPOINT`
- `AZURE_SEARCH_API_KEY`
- `AZURE_SEARCH_INDEX_NAME`

**Critérios de aceite:**
- [ ] Função `getConfig()` exportada retorna objeto tipado com todas as variáveis
- [ ] Se qualquer variável obrigatória estiver ausente, lança `ConfigurationError` com nome da variável faltante
- [ ] Nenhum valor default silencioso para variáveis de segurança (endpoints, keys)
- [ ] Compilação sem erros

---

## TASK-003 — Implementar logger com pino

**Arquivo:** `src/shared/logger.ts`  
**Estimativa:** P  
**Dependências:** TASK-002

**Descrição:**  
Criar instância do logger pino como singleton exportável. Nunca usar `console.log` no projeto — todo output de log passa por este módulo.

**Critérios de aceite:**
- [ ] Logger exportado como `logger` (instância pino)
- [ ] Nível de log configurável via env var `LOG_LEVEL` (default: `info`)
- [ ] Nenhum `console.log`, `console.error` ou `console.warn` no arquivo
- [ ] Logger inclui campo `service: "novatech-assistant"` em todos os registros
- [ ] Compilação sem erros

---

## TASK-004 — Implementar custom errors

**Arquivo:** `src/shared/errors.ts`  
**Estimativa:** P  
**Dependências:** nenhuma

**Descrição:**  
Definir hierarquia de erros customizados do projeto. Erros devem ser identificáveis por tipo (instanceof) e carregar contexto suficiente para logging estruturado.

**Erros a criar:**
- `NovaTechError` — base class com `code` e `context`
- `ConfigurationError` — variável de ambiente ausente/inválida
- `ValidationError` — input inválido do cliente (HTTP 400)
- `SearchServiceError` — falha no Azure AI Search (HTTP 502)
- `CompletionServiceError` — falha no Azure OpenAI (HTTP 502)
- `NotFoundError` — nenhum chunk relevante encontrado (retorno controlado, não exceção)

**Critérios de aceite:**
- [ ] Todos os erros estendem `NovaTechError`
- [ ] Cada erro tem `code` único (string enum estilo `VALIDATION_ERROR`)
- [ ] `ValidationError` aceita campo `field` para identificar qual campo falhou
- [ ] `instanceof` funciona corretamente para cada tipo
- [ ] Compilação sem erros

---

## TASK-005 — Implementar validação de input com Zod

**Arquivo:** `src/functions/query/validator.ts`  
**Estimativa:** P  
**Dependências:** TASK-001, TASK-004

**Descrição:**  
Schema Zod que valida o body do POST /api/query antes de qualquer processamento. Esta é a primeira barreira de defesa do endpoint.

**Schema esperado:**
```typescript
{
  question: string,      // obrigatório, não-vazio, max 1000 chars
  session_id?: string,   // opcional, UUID v4
  attendant_id?: string  // opcional, para logging/auditoria
}
```

**Critérios de aceite:**
- [ ] Schema Zod exportado como `QueryRequestSchema`
- [ ] `question` vazia (`""`) ou só espaços → falha de validação com mensagem clara
- [ ] `question` > 1000 caracteres → falha de validação
- [ ] `session_id` inválido (não-UUID) → falha de validação
- [ ] Em caso de falha, lança `ValidationError` (TASK-004) com campo e mensagem
- [ ] Input válido retorna objeto tipado como `QueryRequest` (TASK-001)
- [ ] Testes unitários passam para casos: válido, question vazia, question muito longa, session_id inválido

---

## TASK-006 — Implementar serviço de embedding

**Arquivo:** `src/services/completion.ts` (função `generateEmbedding`)  
**Estimativa:** M  
**Dependências:** TASK-001, TASK-002, TASK-003, TASK-004

**Descrição:**  
Converter a pergunta do atendente em vetor de embedding via Azure OpenAI. Implementar retry com exponential backoff para resiliência contra falhas transientes.

**Comportamento esperado:**
- Recebe `question: string`
- Chama Azure OpenAI Embeddings API com o deployment configurado
- Retry: 3 tentativas, backoff: 1s → 2s → 4s
- Em falha definitiva, lança `CompletionServiceError`

**Critérios de aceite:**
- [ ] Função `generateEmbedding(question: string): Promise<number[]>` exportada
- [ ] Retry com exponential backoff implementado (não é retry simples)
- [ ] Cada tentativa logada com pino (logger de TASK-003), nível `debug`
- [ ] Falha definitiva lança `CompletionServiceError` com código HTTP original
- [ ] Nenhum `console.log`
- [ ] Compilação sem erros

---

## TASK-007 — Implementar serviço de busca no Azure AI Search

**Arquivo:** `src/services/search.ts`  
**Estimativa:** M  
**Dependências:** TASK-001, TASK-002, TASK-003, TASK-004, TASK-006

> **Aprendizado do protótipo (Dev 1.3):** O `busca.py` com ChromaDB identificou dois problemas críticos que esta task DEVE resolver na versão de produção:
> 1. **Conflito de versão:** PROC-042 v1 e v2 apareceram simultaneamente no top-5 em 3 dos 5 testes (Testes 1, 4 e 5). Sem `_check_version_conflict()`, o LLM silenciosamente misturava multiplicadores de versões diferentes. Em produção, o `vigency_status` do Azure AI Search substitui essa detecção manual.
> 2. **Dominância de FAQ:** chunks do FAQ dominavam ranks 1-2 para queries conversacionais (`filter_faq_if_formal_covers` com threshold 0.40 foi necessário). Azure AI Search com semantic ranking tende a mitigar isso, mas o comportamento deve ser validado com as mesmas 5 queries do protótipo.

**Comportamento esperado:**
- Recebe `embedding: number[]`
- Executa vector search retornando pool de candidatos; seleciona top-5 por score
- Documentos com `vigency_status: "obsolete"` têm score penalizado (equivalente ao `VERSION_CONFLICT_BASES` do protótipo)
- Quando v1 e v2 do mesmo documento aparecerem juntos: preencher `vigency_warning` em todos os chunks do documento obsoleto
- Retry com exponential backoff (mesma política de TASK-006)
- Retorna `SearchChunk[]` (TASK-001)

**Critérios de aceite:**
- [ ] Função `searchChunks(embedding: number[]): Promise<SearchChunk[]>` exportada
- [ ] Retorna no máximo 5 chunks
- [ ] Chunks com `vigency_status: "obsolete"` nunca aparecem sem `vigency_warning` preenchido
- [ ] Se duas versões do mesmo `document_id` base aparecerem: todos os obsoletos recebem `vigency_warning: "Versão substituída por [document_id vigente]"`
- [ ] Se retornar 0 chunks, retorna array vazio (não lança exceção — quem decide é o handler)
- [ ] Retry com exponential backoff
- [ ] Cada busca logada com pino: query_id, chunks_returned, latency_ms, version_conflict (boolean)
- [ ] Compilação sem erros

---

## TASK-008 — Implementar prompt builder com context budget

**Arquivo:** `src/services/prompt-builder.ts`  
**Estimativa:** M  
**Dependências:** TASK-001, TASK-002

> **Aprendizado do protótipo (Dev 1.3):** O `prompt_builder.py` identificou dois comportamentos críticos que esta task DEVE implementar na versão de produção:
> 1. **Lost-in-the-middle** (`_reorder_for_attention`): o LLM perde informação nos chunks do meio. Ordem correta: chunk rank-1 (primeiro), chunk rank-2 (último), demais no meio. Validado nos testes 3 e 5 do protótipo onde SLA-2024-A e PROC-042v2-B estavam nos ranks 1-2 e foram os mais utilizados pelo modelo.
> 2. **Conflito de versão no prompt** (`VERSION_CONFLICT_TEMPLATE`): quando duas versões do mesmo documento estão nos chunks, o prompt deve incluir instrução condicional explícita ao LLM para priorizar a versão mais recente. Sem isso, o LLM silenciosamente combina valores de v1 e v2 (Teste 4: Sudeste 1.0 vs 1.1).

**Comportamento esperado:**
- Recebe: `systemPrompt: string`, `chunks: SearchChunk[]`, `question: string`
- Aplica reordenação anti-lost-in-the-middle: rank-1 primeiro, rank-2 último, demais no meio
- Aplica budget (ADR-0002): ~4K tokens system + ~8K chunks; descarta chunks de menor score se necessário
- Quando há `vigency_warning` em algum chunk: injeta instrução de conflito de versão no system prompt
- Estimativa de tokens: 1 token ≈ 4 caracteres (calibrado para PT-BR conforme análise 1.1)
- Retorna `PromptContext` com os campos: `system`, `context_chunks`, `user_question`, `tokens_used`

**Critérios de aceite:**
- [ ] Função `buildPromptContext(...)` exportada retorna `PromptContext`
- [ ] Nunca ultrapassa budget de 12K tokens no total (system + chunks)
- [ ] Chunks reordenados: rank-1 no índice 0, rank-2 no índice final, demais no meio
- [ ] Se algum chunk tem `vigency_warning`: system prompt inclui `"Quando houver versões conflitantes do mesmo documento, priorize sempre a versão mais recente e informe o atendente que existe versão anterior."`
- [ ] Se chunks ultrapassam budget, descarta os de menor score (não os mais recentes)
- [ ] Campo `tokens_used` sempre preenchido no retorno
- [ ] Log de warning quando budget é atingido e chunks são descartados
- [ ] Compilação sem erros

---

## TASK-009 — Implementar serviço de completion (GPT-4o)

**Arquivo:** `src/services/completion.ts` (função `generateCompletion`)  
**Estimativa:** M  
**Dependências:** TASK-001, TASK-002, TASK-003, TASK-004, TASK-008

**Descrição:**  
Enviar o prompt montado ao GPT-4o via Azure OpenAI e retornar a resposta. Retry com exponential backoff. A resposta deve ser estruturada para extração de `source_document`.

**Comportamento esperado:**
- Recebe `PromptContext`
- Chama Azure OpenAI Chat Completions com `deployment: GPT-4o`
- Temperatura: 0 (respostas determinísticas)
- Retry: 3 tentativas, backoff: 1s → 2s → 4s
- Em falha definitiva, lança `CompletionServiceError`

**Critérios de aceite:**
- [ ] Função `generateCompletion(context: PromptContext): Promise<string>` exportada
- [ ] Temperatura fixada em 0 (não configurável por chamada)
- [ ] Retry com exponential backoff implementado
- [ ] Latência total da chamada logada com pino
- [ ] Falha definitiva lança `CompletionServiceError` com HTTP status original
- [ ] Nenhum `console.log`
- [ ] Compilação sem erros

---

## TASK-010 — Implementar response builder

**Arquivo:** `src/functions/query/response-builder.ts`  
**Estimativa:** P  
**Dependências:** TASK-001, TASK-004

**Descrição:**  
Montar o objeto de resposta final do endpoint garantindo que `source_document` sempre esteja presente. Determinar `confidence_level` baseado nos chunks encontrados.

**Comportamento esperado:**
- Recebe: `answer: string`, `chunks: SearchChunk[]`, `question: string`
- Monta `QueryResponse` com todos campos obrigatórios
- `confidence_level: LOW` quando chunks têm score < 0.75 ou count < 2
- `confidence_level: NOT_FOUND` quando `chunks` está vazio
- Prefixo de aviso na `answer` quando `confidence_level !== HIGH`

**Critérios de aceite:**
- [ ] Função `buildQueryResponse(...)` exportada retorna `QueryResponse`
- [ ] `source_document` NUNCA é `null` ou `undefined` no retorno
- [ ] Quando `chunks` vazio, retorna resposta padrão de "não encontrado" em português formal
- [ ] `confidence_level: LOW` inclui aviso: `"⚠️ Informação com baixa confiança — recomendamos verificação com supervisor"`
- [ ] Compilação sem erros

---

## TASK-011 — Implementar validador determinístico de resposta (harness)

**Arquivo:** `src/services/response-validator.ts`  
**Estimativa:** M  
**Dependências:** TASK-001, TASK-004

> **Aprendizado do protótipo (Dev 1.3):** O Teste 2 ("Posso devolver carga perigosa?") mostrou que sem o filtro FAQ, o `FAQ-Atendimento — item 3` dominava o rank 1 (sim=0.5672) e poderia suavizar a proibição. A seção §3.2 da POL-001 foi chunkeada como `negacao_critica` exatamente para preservar a integridade do "NÃO são elegíveis para devolução". Em produção, essa proteção NÃO pode depender do LLM respeitar o prompt — deve ser **determinística via código**.

**Regras a implementar:**
- Se `question` contém termos de carga perigosa (classes 1-6 ANTT) + qualquer variação de "devolução" → forçar resposta negativa explícita, independente do que o LLM gerou
- Se `answer` contém valor numérico (prazo, multiplicador) não presente literalmente em nenhum `chunk.content` → logar warning e remover o trecho (prevenção de alucinação de valores — cf. Incidente 1 dos guardrails)

**Critérios de aceite:**
- [ ] Função `validateResponse(answer: string, question: string, chunks: SearchChunk[]): string` exportada
- [ ] Pergunta sobre devolução de carga perigosa SEMPRE retorna negativa explícita em português formal, independente do conteúdo do `answer` recebido
- [ ] Detecção de carga perigosa cobre: "carga perigosa", "classe 1" a "classe 6", "ANTT" — case-insensitive, com e sem acento
- [ ] Valores numéricos na resposta não encontrados em nenhum `chunk.content` → warning logado + trecho removido
- [ ] Compilação sem erros

---

## TASK-012 — Implementar HTTP trigger handler

**Arquivo:** `src/functions/query/handler.ts`  
**Estimativa:** M  
**Dependências:** TASK-003, TASK-005, TASK-006, TASK-007, TASK-008, TASK-009, TASK-010, TASK-011

**Descrição:**  
Orquestrar o fluxo completo: validar input → gerar embedding → buscar chunks → montar prompt → gerar completion → validar resposta → retornar. É a única task que une todos os serviços. Implementar como Azure Function v4 HTTP trigger.

**Fluxo:**
```
POST /api/query
  → validateInput (TASK-005)
  → generateEmbedding (TASK-006)
  → searchChunks (TASK-007)
  → buildPromptContext (TASK-008)
  → generateCompletion (TASK-009)
  → validateResponse (TASK-011)
  → buildQueryResponse (TASK-010)
  → HTTP 200 { answer, source_document, confidence_level }
```

**Critérios de aceite:**
- [ ] Registrado como Azure Function v4 com `app.http('query', { ... })`
- [ ] Rota: `POST /api/query`
- [ ] Input inválido → HTTP 400 com mensagem de erro em português
- [ ] Erro de serviço Azure → HTTP 502 (nunca expõe stack trace ao cliente)
- [ ] Toda requisição logada: `request_id`, `question_length`, `chunks_found`, `latency_ms`
- [ ] `source_document` sempre presente no body de resposta HTTP 200
- [ ] Nenhum `console.log`
- [ ] Compilação sem erros

---

## Mapa de dependências

```
TASK-001 (tipos)
TASK-002 (config)
TASK-003 (logger)         → depende de: 002
TASK-004 (errors)         → depende de: nenhuma
TASK-005 (validator Zod)  → depende de: 001, 004
TASK-006 (embedding)      → depende de: 001, 002, 003, 004
TASK-007 (search)         → depende de: 001, 002, 003, 004, 006
TASK-008 (prompt builder) → depende de: 001, 002
TASK-009 (completion)     → depende de: 001, 002, 003, 004, 008
TASK-010 (resp builder)   → depende de: 001, 004
TASK-011 (resp validator) → depende de: 001, 004
TASK-012 (handler)        → depende de: 003, 005, 006, 007, 008, 009, 010, 011
```

## Ordem sugerida de implementação

| Fase | Tasks | Podem ser paralelas? |
|------|-------|----------------------|
| 1 — Foundation | 001, 002, 004 | ✅ Sim |
| 2 — Infra | 003, 005, 010 | ✅ Sim |
| 3 — Serviços base | 006, 008, 011 | ✅ Sim |
| 4 — Serviços dependentes | 007, 009 | ✅ Sim |
| 5 — Orquestração | 012 | ❌ Não (aguarda todas) |
