import { z } from 'zod';
import { logger } from '../shared/logger.js';

export const AssistantStructuredOutputSchema = z
  .object({
    answer: z
      .string({ required_error: 'O campo answer é obrigatório' })
      .trim()
      .min(1, 'O campo answer não pode ser vazio'),
    source_document: z
      .string({ required_error: 'O campo source_document é obrigatório' })
      .trim()
      .min(1, 'O campo source_document não pode ser vazio'),
    confidence_score: z
      .number({ required_error: 'O campo confidence_score é obrigatório' })
      .min(0, 'O campo confidence_score deve ser maior ou igual a 0')
      .max(1, 'O campo confidence_score deve ser menor ou igual a 1'),
  })
  .strict();

export type AssistantStructuredOutput = z.infer<typeof AssistantStructuredOutputSchema>;

const SAFE_FALLBACK_RESPONSE: AssistantStructuredOutput = {
  answer:
    'Nao consegui validar a resposta automaticamente. Consulte a documentacao oficial da NovaTech ou encaminhe o caso ao supervisor.',
  source_document: 'SYSTEM_FALLBACK',
  confidence_score: 0,
};

export function buildSafeFallbackResponse(): AssistantStructuredOutput {
  return { ...SAFE_FALLBACK_RESPONSE };
}

export function validateResponse(rawResponse: unknown): AssistantStructuredOutput {
  const parsedResponse = parseStructuredOutput(rawResponse);

  if (!parsedResponse.success) {
    logger.warn(
      { reason: parsedResponse.reason, details: parsedResponse.details },
      'Assistant response rejected by structured output validator',
    );
    return buildSafeFallbackResponse();
  }

  const structuredOutput = parsedResponse.data;

  if (!hasSourceDocument(structuredOutput)) {
    logger.warn(
      { reason: 'MISSING_SOURCE_DOCUMENT' },
      'Assistant response blocked because source_document is missing',
    );
    return buildSafeFallbackResponse();
  }

  if (violatesDangerousCargoReturnGuardrail(structuredOutput.answer)) {
    logger.warn(
      { reason: 'DANGEROUS_CARGO_RETURN_GUARDRAIL' },
      'Assistant response blocked by dangerous cargo return guardrail',
    );
    return buildSafeFallbackResponse();
  }

  return structuredOutput;
}

type ParsedStructuredOutputResult =
  | {
      success: true;
      data: AssistantStructuredOutput;
    }
  | {
      success: false;
      reason: 'INVALID_JSON' | 'SCHEMA_VALIDATION_FAILED';
      details: string;
    };

function parseStructuredOutput(rawResponse: unknown): ParsedStructuredOutputResult {
  const candidate = parseJsonIfNeeded(rawResponse);

  if (!candidate.success) {
    return candidate;
  }

  const result = AssistantStructuredOutputSchema.safeParse(candidate.data);

  if (!result.success) {
    const firstIssue = result.error.issues[0];
    const issuePath = firstIssue?.path.join('.') ?? 'response';
    return {
      success: false,
      reason: 'SCHEMA_VALIDATION_FAILED',
      details: `${issuePath}: ${firstIssue?.message ?? 'Structured output invalido'}`,
    };
  }

  return {
    success: true,
    data: result.data,
  };
}

function parseJsonIfNeeded(
  rawResponse: unknown,
):
  | { success: true; data: unknown }
  | { success: false; reason: 'INVALID_JSON'; details: string } {
  if (typeof rawResponse !== 'string') {
    return { success: true, data: rawResponse };
  }

  try {
    return { success: true, data: JSON.parse(rawResponse) };
  } catch {
    return {
      success: false,
      reason: 'INVALID_JSON',
      details: 'Model output is not valid JSON',
    };
  }
}

function hasSourceDocument(response: AssistantStructuredOutput): boolean {
  return response.source_document.trim().length > 0;
}

function violatesDangerousCargoReturnGuardrail(answer: string): boolean {
  const normalizedAnswer = normalizeText(answer);
  const mentionsDangerousCargo = containsAny(normalizedAnswer, [
    'carga perigosa',
    'cargas perigosas',
    'classe 1',
    'classe 2',
    'classe 3',
    'classe 4',
    'classe 5',
    'classe 6',
    'antt',
  ]);
  const mentionsReturn = containsAny(normalizedAnswer, [
    'devolu',
    'devolver',
    'devolvida',
    'devolvido',
  ]);

  if (!mentionsDangerousCargo || !mentionsReturn) {
    return false;
  }

  const containsRequiredNegative = containsAny(normalizedAnswer, [
    'nao pode',
    'nao podem',
    'nao e possivel',
    'nao sao elegiveis',
    'nao e elegivel',
    'nao podem ser devolvid',
    'nao pode ser devolvid',
    'gestao de riscos',
    'escalar para o supervisor',
    'escalar para supervisor',
  ]);
  const explicitlyAllowsReturn = matchesAnyPattern(normalizedAnswer, [
    /\bsim,\s*carga perigosa pode ser devolvida\b/u,
    /\bsim,\s*cargas perigosas podem ser devolvidas\b/u,
    /\b(?<!nao )pode devolver\b/u,
    /\b(?<!nao )podem devolver\b/u,
    /\b(?<!nao )pode ser devolvida\b/u,
    /\b(?<!nao )podem ser devolvidas\b/u,
    /\bdevolucao permitida\b/u,
    /\be possivel devolver\b/u,
    /\be possivel a devolucao\b/u,
    /\be elegivel para devolucao\b/u,
    /\bsao elegiveis para devolucao\b/u,
  ]);
  const containsExceptionLanguage = containsAny(normalizedAnswer, [
    'oficialmente nao pode, mas',
    'pode haver excecao',
    'podem haver excecoes',
    'excecao',
    'excecoes',
    'autorizacao',
    'autorizado',
    'autorizada',
    'nao diga que e impossivel',
    'tratamento especial',
  ]);

  return explicitlyAllowsReturn || containsExceptionLanguage || !containsRequiredNegative;
}

function normalizeText(value: string): string {
  return value
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase();
}

function containsAny(value: string, terms: string[]): boolean {
  return terms.some((term) => value.includes(term));
}

function matchesAnyPattern(value: string, patterns: RegExp[]): boolean {
  return patterns.some((pattern) => pattern.test(value));
}