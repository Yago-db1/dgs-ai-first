import { z } from 'zod';
import { ValidationError } from '../../shared/errors.js';
import type { FeedbackRequest } from '../../shared/types.js';

export const FeedbackRequestSchema = z
  .object({
    queryId: z
      .string({ required_error: 'O campo queryId é obrigatório' })
      .trim()
      .min(1, 'O campo queryId não pode ser vazio'),
    rating: z
      .number({
        required_error: 'O campo rating é obrigatório',
        invalid_type_error: 'O campo rating deve ser um número inteiro entre 1 e 5',
      })
      .int('O campo rating deve ser um número inteiro entre 1 e 5')
      .min(1, 'O campo rating deve ser um número inteiro entre 1 e 5')
      .max(5, 'O campo rating deve ser um número inteiro entre 1 e 5'),
    comment: z
      .string({ invalid_type_error: 'O campo comment deve ser texto' })
      .trim()
      .min(1, 'O campo comment não pode ser vazio')
      .max(2000, 'O campo comment não pode ultrapassar 2000 caracteres')
      .optional(),
    attendantEmail: z
      .string({ required_error: 'O campo attendantEmail é obrigatório' })
      .trim()
      .email('O campo attendantEmail deve ser um e-mail válido'),
  })
  .strict();

export function validateFeedbackInput(body: unknown): FeedbackRequest {
  const result = FeedbackRequestSchema.safeParse(body);

  if (!result.success) {
    const firstError = result.error.errors[0];
    const field = firstError?.path.join('.') ?? 'unknown';
    const message = firstError?.message ?? 'Requisição inválida';
    throw new ValidationError(message, field);
  }

  return result.data;
}
