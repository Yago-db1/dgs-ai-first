import { ConfigurationError } from './errors.js';

export interface AppConfig {
  azureOpenAiEndpoint: string;
  azureOpenAiApiKey: string;
  azureOpenAiDeploymentName: string;
  azureOpenAiEmbeddingDeployment: string;
  azureSearchEndpoint: string;
  azureSearchApiKey: string;
  azureSearchIndexName: string;
  logLevel: string;
}

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new ConfigurationError(
      `Missing required environment variable: ${name}`,
      name,
    );
  }
  return value;
}

export function getConfig(): AppConfig {
  return {
    azureOpenAiEndpoint: requireEnv('AZURE_OPENAI_ENDPOINT'),
    azureOpenAiApiKey: requireEnv('AZURE_OPENAI_API_KEY'),
    azureOpenAiDeploymentName: requireEnv('AZURE_OPENAI_DEPLOYMENT_NAME'),
    azureOpenAiEmbeddingDeployment: requireEnv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT'),
    azureSearchEndpoint: requireEnv('AZURE_SEARCH_ENDPOINT'),
    azureSearchApiKey: requireEnv('AZURE_SEARCH_API_KEY'),
    azureSearchIndexName: requireEnv('AZURE_SEARCH_INDEX_NAME'),
    // LOG_LEVEL is optional — safe default does not expose security data
    logLevel: process.env['LOG_LEVEL'] ?? 'info',
  };
}
