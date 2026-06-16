// Custom error hierarchy for NovaTech Assistant.
// All errors extend NovaTechError to allow typed instanceof checks throughout the codebase.

export type ErrorCode =
  | 'CONFIGURATION_ERROR'
  | 'VALIDATION_ERROR'
  | 'SEARCH_SERVICE_ERROR'
  | 'COMPLETION_SERVICE_ERROR'
  | 'NOT_FOUND';

export class NovaTechError extends Error {
  constructor(
    message: string,
    public readonly code: ErrorCode,
    public readonly context?: Record<string, unknown>,
  ) {
    super(message);
    this.name = this.constructor.name;
    // Restore prototype chain for instanceof checks in compiled JS
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class ConfigurationError extends NovaTechError {
  constructor(
    message: string,
    public readonly variable: string,
  ) {
    super(message, 'CONFIGURATION_ERROR', { variable });
  }
}

export class ValidationError extends NovaTechError {
  constructor(
    message: string,
    public readonly field: string,
  ) {
    super(message, 'VALIDATION_ERROR', { field });
  }
}

export class SearchServiceError extends NovaTechError {
  constructor(
    message: string,
    public readonly httpStatus?: number,
  ) {
    super(message, 'SEARCH_SERVICE_ERROR', { httpStatus });
  }
}

export class CompletionServiceError extends NovaTechError {
  constructor(
    message: string,
    public readonly httpStatus?: number,
  ) {
    super(message, 'COMPLETION_SERVICE_ERROR', { httpStatus });
  }
}

export class NotFoundError extends NovaTechError {
  constructor(message: string) {
    super(message, 'NOT_FOUND');
  }
}
