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
  const requestId = crypto.randomUUID();
  const startTime = Date.now();

  logger.info({ requestId }, 'Query request received');

  try {
    const body = await request.json().catch(() => null);
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
