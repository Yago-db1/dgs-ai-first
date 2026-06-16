import pino from 'pino';

// Singleton logger — import this throughout the codebase.
// NEVER use console.log, console.error, or console.warn anywhere in the project.
export const logger = pino({
  level: process.env['LOG_LEVEL'] ?? 'info',
  base: { service: 'novatech-assistant' },
});
