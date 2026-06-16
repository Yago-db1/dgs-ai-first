# SKILL: error-handling

> **Nível:** Foundation  
> **Frase-ativação:** "Vou implementar tratamento de erro" | "Preciso logar algo" | "Vou fazer retry de chamada Azure"  
> **Depende de:** `typescript-conventions`  
> **Consumida por:** `azure-functions-endpoint`, `azure-ai-search-integration`, `create-rag-endpoint`, `create-integration-test`

---

## Contexto

Todo arquivo que faz I/O (chamadas Azure, leitura de config, validação) DEVE seguir estas regras.
O Copilot, sem esta skill, gera `console.log`, `catch(e: any)` e expõe stack traces ao cliente.
Esta skill é lida antes de qualquer geração de serviço, handler ou função com `try/catch`.

---

## Regras Prescritivas

### Logging

- **DEVE** usar `logger` importado de `src/shared/logger.ts` — nunca `console.log`, `console.error` ou `console.warn`
- **DEVE** incluir campos estruturados no log: no mínimo `requestId` e o campo mais relevante do contexto (ex: `questionLength`, `chunksFound`, `latencyMs`)
- **DEVE** usar o nível correto: `logger.info` para fluxo normal, `logger.warn` para erros esperados (ex: ValidationError), `logger.error` para falhas de serviço
- **NÃO DEVE** logar objetos de erro brutos sem estruturar os campos relevantes

### Erros customizados

- **DEVE** usar a hierarquia de `src/shared/errors.ts` — nunca lançar `new Error('mensagem')` diretamente
- **DEVE** incluir `Object.setPrototypeOf(this, new.target.prototype)` em todo construtor de erro customizado (corrige `instanceof` em ES2022 compilado)
- **NÃO DEVE** usar `any` no tipo do parâmetro `catch` — usar `unknown` e estreitar com `instanceof`
- **NÃO DEVE** relançar erros sem adicionar contexto quando o erro original não tem informação suficiente

### Retry com exponential backoff

- **DEVE** implementar retry com no máximo 3 tentativas para toda chamada a Azure AI Search e Azure OpenAI
- **DEVE** usar backoff exponencial: espera 1s → 2s → 4s entre tentativas (nunca retry imediato em loop)
- **DEVE** logar cada tentativa com `logger.debug` incluindo o número da tentativa e o erro recebido
- **NÃO DEVE** usar retry para erros de cliente (HTTP 4xx) — só para erros de servidor (HTTP 5xx) e timeouts

### HTTP responses

- **NUNCA** expor `error.stack`, `error.message` de erros internos, ou nomes de serviços Azure na resposta HTTP ao cliente
- **DEVE** mapear erros para HTTP status: `ValidationError` → 400, `SearchServiceError`/`CompletionServiceError` → 502, demais `NovaTechError` → 500
- **DEVE** retornar mensagem em português para o cliente (ex: `"Serviço temporariamente indisponível. Tente novamente."`)

---

## Exemplos — DO ✅

### Logger com campos estruturados

```typescript
// ✅ Logger com contexto estruturado — campos buscáveis no Application Insights
import { logger } from '../../shared/logger.js';

logger.info(
  { requestId, questionLength: input.question.length },
  'Input validated',
);

logger.warn(
  { requestId, field: error.field, code: error.code },
  error.message,
);

logger.error(
  { requestId, code: error.code, httpStatus: error.httpStatus },
  'Azure AI Search call failed',
);
```

### Erro customizado com instanceof correto

```typescript
// ✅ Hierarquia de erros com prototype chain corrigido
export class NovaTechError extends Error {
  constructor(
    message: string,
    public readonly code: ErrorCode,
    public readonly context?: Record<string, unknown>,
  ) {
    super(message);
    this.name = this.constructor.name;
    Object.setPrototypeOf(this, new.target.prototype); // obrigatório para instanceof em ES2022
  }
}

export class SearchServiceError extends NovaTechError {
  constructor(message: string, public readonly httpStatus?: number) {
    super(message, 'SEARCH_SERVICE_ERROR', { httpStatus });
  }
}
```

### Catch com unknown e narrowing

```typescript
// ✅ catch com unknown — nunca any
try {
  const result = await callAzureSearch(embedding);
  return result;
} catch (error) {
  if (error instanceof SearchServiceError) {
    logger.error({ requestId, code: error.code }, error.message);
    throw error;
  }
  // erro inesperado: logar com contexto e relançar como NovaTechError
  logger.error({ requestId, error }, 'Unexpected error in searchChunks');
  throw new SearchServiceError('Azure AI Search returned unexpected error');
}
```

### Retry com exponential backoff

```typescript
// ✅ Retry com backoff exponencial — somente para erros de servidor
async function withRetry<T>(
  fn: () => Promise<T>,
  maxAttempts = 3,
): Promise<T> {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      const isRetryable =
        error instanceof SearchServiceError && (error.httpStatus ?? 500) >= 500;

      if (!isRetryable || attempt === maxAttempts) throw error;

      const waitMs = Math.pow(2, attempt - 1) * 1000; // 1s, 2s, 4s
      logger.debug({ attempt, waitMs }, 'Retrying after error');
      await new Promise((resolve) => setTimeout(resolve, waitMs));
    }
  }
  throw new SearchServiceError('Max retry attempts reached');
}
```

### Mapeamento de erros para HTTP

```typescript
// ✅ Nunca expõe detalhes internos ao cliente
function handleError(error: unknown, requestId: string): HttpResponseInit {
  if (error instanceof ValidationError) {
    logger.warn({ requestId, field: error.field }, error.message);
    return {
      status: 400,
      body: JSON.stringify({ error: error.message, field: error.field }),
    };
  }
  if (error instanceof SearchServiceError || error instanceof CompletionServiceError) {
    logger.error({ requestId, code: error.code }, error.message);
    return {
      status: 502,
      body: JSON.stringify({
        error: 'Serviço temporariamente indisponível. Tente novamente em instantes.',
      }),
    };
  }
  logger.error({ requestId, error }, 'Unexpected error');
  return {
    status: 500,
    body: JSON.stringify({ error: 'Erro interno. Por favor, contate o suporte.' }),
  };
}
```

---

## Exemplos — DON'T ❌

### console.log (anti-padrão #1 do Copilot)

```typescript
// ❌ Copilot gera isso quando não há guidance
console.log('Processing query:', question);
console.error('Error calling Azure Search:', error);
console.log(`Found ${chunks.length} chunks`);

// Por que é problemático:
// - console.log não aparece no Application Insights
// - Não tem campos estruturados — impossível filtrar por requestId
// - Em Azure Functions, pode aparecer em lugares inesperados
```

### catch(e: any)

```typescript
// ❌ Copilot usa any no catch quando não tem guidance de tipos
try {
  return await callAzure();
} catch (e: any) {         // ← any abre brecha para acessar propriedades inexistentes
  console.log(e.message);  // ← e.message pode ser undefined se e não for Error
  throw e;
}

// ✅ Correto: unknown + instanceof narrowing (ver seção DO)
```

### Stack trace exposto ao cliente

```typescript
// ❌ Copilot frequentemente inclui error.message e error.stack na resposta
return {
  status: 500,
  body: JSON.stringify({
    error: error.message,  // ← pode revelar nomes de serviços, paths internos, secrets
    stack: error.stack,    // ← expõe implementação interna — grave em produção
  }),
};
```

### Retry em loop simples sem backoff

```typescript
// ❌ Copilot gera retry ingênuo sem backoff — martela o serviço em falha
for (let i = 0; i < 3; i++) {
  try {
    return await callAzure();
  } catch {
    // sem espera entre tentativas → agrava throttling
  }
}
```

### catch vazio silenciando erro

```typescript
// ❌ Copilot às vezes gera catch vazio para "tratar" erros
try {
  config = await loadConfig();
} catch {
  // silently ignore — config remains undefined
}
// resultado: NullPointerException silencioso mais adiante
```

### Missing Object.setPrototypeOf

```typescript
// ❌ Copilot gera classes de erro sem correção do prototype chain
class SearchServiceError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'SearchServiceError';
    // sem Object.setPrototypeOf → instanceof SearchServiceError retorna false
    // em código TypeScript compilado para ES2022 com target older que ES6
  }
}
```

---

## Anti-padrões específicos de LLMs

| Anti-padrão | Por que LLMs geram | Impacto |
|---|---|---|
| `console.log` em vez de pino | É o padrão de logging mais comum em exemplos de Node.js na internet | Logs invisíveis no Azure Monitor |
| `catch (e: any)` | `any` resolve o erro de tipo sem exigir narrowing — caminho de menor resistência | Acesso inseguro a propriedades do erro |
| `error.message` na resposta HTTP | "Mensagem de erro útil para o usuário" — o LLM não sabe distinguir mensagem interna de mensagem pública | Exposição de detalhes de implementação |
| `Object.setPrototypeOf` omitido | Exemplos antigos de custom errors não incluíam — o LLM aprende dos exemplos | `instanceof` quebrado silenciosamente |
| Retry em loop `for` sem sleep | Estrutura de retry mais simples que o modelo conhece | Throttling agravado em serviços Azure |
| `throw new Error('...')` inline | Mais curto que criar classe de erro customizado | Erros sem tipagem, impossível tratar por tipo |

---

## Checklist de revisão

Antes de aprovar código gerado pelo Copilot que envolva I/O ou error handling:

- [ ] Nenhum `console.log`, `console.error`, `console.warn`
- [ ] Todo `catch` usa `unknown` (não `any`) e faz narrowing com `instanceof`
- [ ] Erros customizados têm `Object.setPrototypeOf` no constructor
- [ ] Todo log inclui `requestId` como campo estruturado
- [ ] Resposta HTTP ao cliente não contém `error.stack` ou `error.message` de erros internos
- [ ] Retry implementado com `Math.pow(2, attempt - 1) * 1000` (não loop simples)
- [ ] Retry não se aplica a HTTP 4xx (erros de cliente não são retryable)
