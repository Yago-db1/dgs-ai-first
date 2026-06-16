import { z } from 'zod';
import { ValidationError } from '../../shared/errors.js';
import type { QueryRequest } from '../../shared/types.js';

export const QueryRequestSchema = z.object({
  question: z
    .string({ required_error: 'O campo question é obrigatório' })
    .trim()
    .min(1, 'O campo question não pode ser vazio')
    .max(1000, 'O campo question não pode ultrapassar 1000 caracteres'),
  session_id: z
    .string()
    .uuid('O campo session_id deve ser um UUID v4 válido')
    .optional(),
  attendant_id: z.string().optional(),
});

/**
 * Validates raw HTTP request body against the query endpoint schema.
 * Throws ValidationError (HTTP 400) on the first schema violation found.
 */
export function validateQueryInput(body: unknown): QueryRequest {
  const result = QueryRequestSchema.safeParse(body);

  if (!result.success) {
    const firstError = result.error.errors[0];
    const field = firstError?.path.join('.') ?? 'unknown';
    const message = firstError?.message ?? 'Requisição inválida';
    throw new ValidationError(message, field);
  }

  return result.data;
}
