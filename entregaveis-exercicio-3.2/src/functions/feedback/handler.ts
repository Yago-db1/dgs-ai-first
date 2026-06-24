import { app, HttpRequest, HttpResponseInit, InvocationContext } from '@azure/functions';
import { CosmosClient, type Container } from '@azure/cosmos';
import { ConfigurationError, ValidationError } from '../../shared/errors.js';
import { logger } from '../../shared/logger.js';
import { validateFeedbackInput } from './validator.js';

const DATABASE_ID = 'novatech';
const CONTAINER_ID = 'feedbacks';

let feedbackContainer: Container | null = null;

function getFeedbackContainer(): Container {
  const connectionString = process.env['COSMOS_CONNECTION_STRING'];

  if (!connectionString) {
    throw new ConfigurationError(
      'A variável COSMOS_CONNECTION_STRING é obrigatória para persistir feedback',
      'COSMOS_CONNECTION_STRING',
    );
  }

  if (feedbackContainer) {
    return feedbackContainer;
  }

  const client = new CosmosClient(connectionString);
  feedbackContainer = client.database(DATABASE_ID).container(CONTAINER_ID);

  return feedbackContainer;
}

export async function feedbackHandler(
  request: HttpRequest,
  context: InvocationContext,
): Promise<HttpResponseInit> {
  const requestId = context.invocationId;

  logger.info(
    { requestId, traceParent: context.traceContext?.traceParent },
    'Feedback request received',
  );

  try {
    let body: unknown;

    try {
      body = await request.json();
    } catch {
      throw new ValidationError('O body da requisição deve ser um JSON válido', 'body');
    }

    const input = validateFeedbackInput(body);
    const timestamp = new Date().toISOString();

    await getFeedbackContainer().items.create({
      queryId: input.queryId,
      rating: input.rating,
      comment: input.comment,
      attendantEmail: input.attendantEmail,
      timestamp,
    });

    logger.info(
      {
        requestId,
        queryId: input.queryId,
        rating: input.rating,
        hasComment: input.comment !== undefined,
      },
      'Feedback persisted',
    );

    return {
      status: 201,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: 'Feedback registrado com sucesso',
        queryId: input.queryId,
        timestamp,
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

  if (error instanceof ConfigurationError) {
    logger.error({ requestId, variable: error.variable, code: error.code }, error.message);
    return {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: 'Configuração inválida do serviço de feedback.',
        code: error.code,
      }),
    };
  }

  logger.error({ requestId, error }, 'Unexpected error while processing feedback');
  return {
    status: 500,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ error: 'Erro interno. Por favor, contate o suporte.' }),
  };
}

app.http('feedback', {
  methods: ['POST'],
  authLevel: 'function',
  route: 'feedback',
  handler: feedbackHandler,
});
