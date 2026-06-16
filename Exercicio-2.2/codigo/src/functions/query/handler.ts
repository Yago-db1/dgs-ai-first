import { app, HttpRequest, HttpResponseInit, InvocationContext } from '@azure/functions';
import { logger } from '../../shared/logger.js';
import {
  ValidationError,
  SearchServiceError,
  CompletionServiceError,
  NovaTechError,
} from '../../shared/errors.js';
import { validateQueryInput } from './validator.js';

async function queryHandler(
  request: HttpRequest,
  context: InvocationContext,
): Promise<HttpResponseInit> {
  // Fix 1: use context.invocationId for Azure Monitor correlation
  // Copilot v1 generated crypto.randomUUID() — those logs are invisible in Application Insights
  const requestId = context.invocationId;
  const startTime = Date.now();

  logger.info(
    { requestId, traceParent: context.traceContext?.traceParent },
    'Query request received',
  );

  try {
    // Fix 2: distinguish JSON parse errors from missing-field errors
    // Copilot v1 silenced parse failures with .catch(() => null), producing a misleading
    // "question is required" error when the real problem was an invalid JSON body
    let body: unknown;
    try {
      body = await request.json();
    } catch {
      throw new ValidationError('O body da requisição deve ser um JSON válido', 'body');
    }
    const input = validateQueryInput(body);

    logger.info(
      { requestId, questionLength: input.question.length, attendantId: input.attendant_id },
      'Input validated',
    );

    // TODO: TASK-006 — const embedding = await generateEmbedding(input.question);
    // TODO: TASK-007 — const chunks = await searchChunks(embedding);
    // TODO: TASK-008 — const promptContext = buildPromptContext(systemPrompt, chunks, input.question);
    // TODO: TASK-009 — const rawAnswer = await generateCompletion(promptContext);
    // TODO: TASK-011 — const safeAnswer = validateResponse(rawAnswer, input.question, chunks);
    // TODO: TASK-010 — const response = buildQueryResponse(safeAnswer, chunks, input.question);

    const latencyMs = Date.now() - startTime;
    logger.info({ requestId, latencyMs }, 'Query pipeline completed');

    // Placeholder response until pipeline tasks are implemented
    return {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: 'Endpoint operacional — pipeline em implementação',
        request_id: requestId,
      }),
    };
  } catch (error) {
    return handleError(error, requestId);
  }
}

function handleError(error: unknown, requestId: string): HttpResponseInit {
  if (error instanceof ValidationError) {
    logger.warn({ requestId, field: error.field, code: error.code }, error.message);
    return {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: error.message,
        field: error.field,
        code: error.code,
      }),
    };
  }

  if (error instanceof SearchServiceError || error instanceof CompletionServiceError) {
    logger.error({ requestId, code: error.code, context: error.context }, error.message);
    return {
      status: 502,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: 'Serviço temporariamente indisponível. Tente novamente em instantes.',
        code: error.code,
      }),
    };
  }

  if (error instanceof NovaTechError) {
    logger.error({ requestId, code: error.code, context: error.context }, error.message);
    return {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'Erro interno. Por favor, contate o suporte.' }),
    };
  }

  logger.error({ requestId, error }, 'Unexpected error');
  return {
    status: 500,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ error: 'Erro interno. Por favor, contate o suporte.' }),
  };
}

app.http('query', {
  methods: ['POST'],
  authLevel: 'function',
  route: 'query',
  handler: queryHandler,
});
