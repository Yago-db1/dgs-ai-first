# Exercício 2.2 — Implementação de Spec com Spec Driven Development

**Papel:** Desenvolvedor  
**Ferramentas usadas:** GitHub Copilot (geração de tasks e código)

---

## O que foi feito

### Tarefa 1 — Conversão do plan.md em tasks.md

**Input:** `plan.md` simulado do query endpoint (fornecido no enunciado do exercício)

**Output:** [`tasks.md`](./tasks.md)

O plan foi decomposto em **12 tasks atômicas**, cada uma com:
- ID único (`TASK-001` a `TASK-012`)
- Arquivo-alvo no repositório
- Descrição detalhada
- Critérios de aceite verificáveis (checklists com itens objetivos)
- Dependências entre tasks explícitas
- Estimativa P/M/G

**Ordem de implementação sugerida:**

| Fase | Tasks | Paralelas? |
|------|-------|------------|
| 1 — Foundation | TASK-001, 002, 004 | ✅ |
| 2 — Infra | TASK-003, 005, 010 | ✅ |
| 3 — Serviços base | TASK-006, 008, 011 | ✅ |
| 4 — Serviços dependentes | TASK-007, 009 | ✅ |
| 5 — Orquestração | TASK-012 | ❌ (aguarda todas) |

---

### Tarefa 2 — Implementação da primeira task (setup do endpoint com validação de input)

**Ferramenta:** GitHub Copilot  
**Tasks implementadas:** TASK-001 a TASK-005 + handler do TASK-012 (parcial)

#### Arquivos gerados

| Arquivo | Task | Descrição |
|---------|------|-----------|
| `codigo/src/shared/types.ts` | TASK-001 | Tipos TypeScript do domínio |
| `codigo/src/shared/errors.ts` | TASK-004 | Hierarquia de erros customizados |
| `codigo/src/shared/config.ts` | TASK-002 | Leitura e validação de variáveis de ambiente |
| `codigo/src/shared/logger.ts` | TASK-003 | Instância pino singleton |
| `codigo/src/functions/query/validator.ts` | TASK-005 | Schema Zod + função de validação |
| `codigo/src/functions/query/handler.ts` | TASK-012 (parcial) | Azure Function v4 com orquestração e error handling |

#### Padrões do plan seguidos ✅

- **TypeScript strict** — sem `any`, todos os tipos explícitos
- **Azure Functions v4** — registro com `app.http()`, tipos `HttpRequest`/`HttpResponseInit`/`InvocationContext`
- **Zod** — `safeParse` para validação sem exception não tipada; lança `ValidationError` do domínio
- **pino** — zero `console.log`; logger singleton com campo `service` fixo
- **Custom errors** — hierarquia com `NovaTechError` base; `instanceof` correto via `Object.setPrototypeOf`
- **Fail-fast config** — `getConfig()` lança `ConfigurationError` imediatamente se variável obrigatória ausente
- **Error handling HTTP** — 400 para `ValidationError`, 502 para serviços Azure, 500 para erros inesperados; stack trace nunca exposto ao cliente

#### Stubs documentados para próximas tasks

O handler contém TODOs explícitos com referência às tasks pendentes:
```
// TODO: TASK-006 — const embedding = await generateEmbedding(input.question);
// TODO: TASK-007 — const chunks = await searchChunks(embedding);
// TODO: TASK-008 — const promptContext = buildPromptContext(...);
// TODO: TASK-009 — const rawAnswer = await generateCompletion(promptContext);
// TODO: TASK-011 — const safeAnswer = validateResponse(...);
// TODO: TASK-010 — const response = buildQueryResponse(...);
```

---

### Tarefa 3 — Revisão crítica

**Output:** [`revisao-critica.md`](./revisao-critica.md)

Dois problemas reais identificados no código gerado pelo Copilot:

1. **`request.json().catch(() => null)`** — engole erro de parse e retorna mensagem enganosa ao cliente (diz que `question` está ausente quando o problema é o body inteiro não ser JSON)
2. **`crypto.randomUUID()` em vez de `context.invocationId`** — logs não ficam correlacionados com o Azure Monitor/Application Insights, quebrando observabilidade em produção

Ver detalhes com ajustes propostos em [`revisao-critica.md`](./revisao-critica.md).

---

## Processo de Geração com GitHub Copilot

### Prompts utilizados

**Prompt 1 — Tipos de domínio (`types.ts`)**
```
Define TypeScript interfaces for a RAG query endpoint:
- QueryRequest with question (string), optional session_id (UUID) and attendant_id
- QueryResponse that always includes source_document (never null)
- SearchChunk with id, content, score, source_document, vigency_status (active|obsolete)
- PromptContext with system prompt, context_chunks array, user_question, tokens_used
- ConfidenceLevel as union type: HIGH | LOW | NOT_FOUND
Use strict TypeScript, no any types.
```

**Prompt 2 — Handler Azure Functions v4 (`handler.ts`)**
```
Create an Azure Functions v4 HTTP trigger for POST /api/query.
Stack: TypeScript strict, pino logger (no console.log), Zod validation via validateQueryInput(),
custom error hierarchy (ValidationError → 400, SearchServiceError/CompletionServiceError → 502).
Register with app.http(). Include structured logging with requestId on every log entry.
Leave TODO comments for the pipeline steps (embedding, search, completion) not yet implemented.
```

**Prompt 3 — Validação Zod (`validator.ts`)**
```
Write a Zod schema for validating the query endpoint input.
Fields: question (required string, trimmed, min 1, max 1000 chars), 
session_id (optional UUID v4), attendant_id (optional string).
Export a validateQueryInput(body: unknown) function that throws a typed ValidationError
(with field name) instead of a raw Zod error.
```

---

### Ciclo v1 → v2: `handler.ts`

Após a revisão crítica, dois problemas foram identificados e corrigidos. Os arquivos `handler.v1.ts` (Copilot original) e `handler.ts` (revisado) mostram o delta completo.

#### Correção 1 — JSON parse silencioso → erro semântico correto

```typescript
// ❌ v1 — gerado pelo Copilot
const body = await request.json().catch(() => null);
const input = validateQueryInput(body);
// Problema: body inválido retorna null → "question é obrigatório"
// Mensagem correta tecnicamente, mas causa errada — confunde o cliente

// ✅ v2 — após revisão crítica
let body: unknown;
try {
  body = await request.json();
} catch {
  throw new ValidationError('O body da requisição deve ser um JSON válido', 'body');
}
const input = validateQueryInput(body);
// Agora: body inválido → "body deve ser JSON válido" — causa correta
```

**Por que importa:** em produção, um cliente enviando `Content-Type: application/x-www-form-urlencoded` receberia HTTP 400 com `field: "question"` em vez de `field: "body"`. Impossível debugar sem conhecer o código interno.

#### Correção 2 — UUID local → `context.invocationId` do Azure

```typescript
// ❌ v1 — gerado pelo Copilot
const requestId = crypto.randomUUID();
logger.info({ requestId }, 'Query request received');
// Problema: requestId no pino ≠ invocationId no Azure Monitor
// Em produção: impossível correlacionar logs do pino com traces do Application Insights

// ✅ v2 — após revisão crítica
const requestId = context.invocationId;
logger.info(
  { requestId, traceParent: context.traceContext?.traceParent },
  'Query request received',
);
// Agora: requestId é o mesmo ID que o Azure Monitor usa
// traceParent habilita distributed tracing W3C com Teams/API Gateway
```

**Por que importa:** o Azure Functions runtime correlaciona logs via `invocationId`. Usar um UUID próprio cria dois sistemas de rastreamento paralelos — em incidentes de produção, não é possível ver o trace completo em um único lugar no Application Insights.

---



No Cenário 1 (Dev 1.3), foi construído um **protótipo funcional de RAG** usando Python, ChromaDB e `sentence-transformers`. Esse protótipo validou a abordagem e produziu **descobertas concretas** que informam diretamente as tasks deste exercício.

### O que foi validado

| Decisão | Evidência do protótipo | Tasks afetadas |
|---------|----------------------|----------------|
| Top-5 chunks é o número correto | 5 testes executados: resultados acima de 5 não melhoravam qualidade | TASK-007 |
| `vigency_status` obrigatório no metadado | Testes 1, 4 e 5: PROC-042 v1 e v2 apareceram juntos em 3/5 testes — sem controle de versão o LLM misturava multiplicadores | TASK-001, TASK-007 |
| Instrução de conflito de versão no prompt | `VERSION_CONFLICT_TEMPLATE` foi necessário para o LLM priorizar v2 explicitamente | TASK-008 |
| Reordenação anti-lost-in-the-middle | `_reorder_for_attention()`: rank-1 primeiro, rank-2 último — validado nos Testes 3 e 5 | TASK-008 |
| Guardrail de carga perigosa deve ser determinístico | Teste 2: sem `filter_faq_if_formal_covers`, o FAQ-03 dominava rank 1 (sim=0.5672) e poderia suavizar a proibição de devolução | TASK-011 |
| Token ratio 0.70 para PT-BR | Protótipo: ratio 0.75 superestimava budget em português; 0.70 é calibrado para tokenização BPE em PT-BR | TASK-008 |

### O que mudou de protótipo para produção

| Componente | Protótipo (Cenário 1) | Produção (Cenário 2) | Motivo |
|---|---|---|---|
| Linguagem | Python 3.11 | TypeScript (strict) | Stack do projeto — ADR-0001 |
| Embeddings | `sentence-transformers` (local) | Azure OpenAI Embeddings | Integração com ecossistema Microsoft — ADR-0001 |
| Vector store | ChromaDB (local, disco) | Azure AI Search | Escalabilidade e SLA de produção — ADR-0001 |
| Detecção de conflito | `_check_version_conflict()` manual | `vigency_status` como metadado indexado | Azure AI Search suporta filtros por metadado nativamente |
| Runtime | Script Python standalone | Azure Functions v4 HTTP trigger | Arquitetura serverless definida na fase de discovery |
| Geração | Claude via prompt colado manualmente | GPT-4o via Azure OpenAI (temperatura=0) | ADR-0001: janela 128K e integração Microsoft Teams |

### Problemas do protótipo NÃO resolvidos nesta task (escopo futuro)

- **Sem cross-encoder/reranker:** o protótipo identificou que ANN por similaridade retorna chunks semanticamente próximos mas não necessariamente os mais úteis. Teste 4 ("frete para 600kg para Manaus"): PROC-042v2-B (tabela de multiplicadores) ficou fora do top-5. Azure AI Search com semantic ranker mitiga parcialmente — mas precisará das mesmas 5 queries do protótipo como benchmark de validação.
- **Tabelas sem serialização NL:** Teste 3 mostrou que tabelas em markdown puro (`| Gold | Até 2h |`) embeddavam mal. O Azure AI Search pode ter comportamento diferente — validar com o benchmark do Anexo B.



| Critério | Atendido? | Evidência |
|----------|-----------|-----------|
| Tasks são realmente atômicas | ✅ | Cada task tem 1 arquivo-alvo e pode ser testada isoladamente |
| Critérios de aceite verificáveis | ✅ | Checklists com itens objetivos (ex: "lança `ValidationError` com campo `field`") |
| Código funcional e segue padrões do plan | ✅ | TypeScript strict, Zod, pino, Azure Functions v4 — todos aplicados |
| Revisão crítica identifica problemas reais | ✅ | Dois bugs concretos com reprodução e ajuste proposto |
