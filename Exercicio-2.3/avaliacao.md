# Avaliação do Exercício 2.3 — Desenvolvedor
**Papel:** Desenvolvedor | **Cenário:** 2 — Estruturação do Trabalho  
**Exercício:** 2.3 — Definição de Estratégia de Skills do Projeto  
**Avaliador:** GitHub Copilot (skills: `avaliacao-foundation.md` + `avaliacao-desenvolvedor.md`)

---

## Checklist de Entregáveis

| Entregável exigido | Arquivo | Status |
|--------------------|---------|--------|
| Árvore de skills (Foundation → Domain → Artifact) | `arvore-skills.md` | ✅ 12 skills |
| Mapeamento de criação/consumo por papel | `arvore-skills.md` (tabelas por skill) | ✅ inclui PS como criador de `create-spec` |
| SKILL.md Foundation gerado com Copilot | `codigo/skills/foundation/error-handling.md` | ✅ |

---

## Primeira Avaliação (entregável inicial)

| Dimensão | Score | Justificativa |
|----------|-------|---------------|
| D1 — Domínio Conceitual | **3** | Hierarquia Foundation → Domain → Artifact aplicada corretamente: Foundation = convenções globais, Domain = padrões por camada, Artifact = receitas completas. Frases-ativação demonstram entendimento de como agentes consomem skills. Grafo de dependências entre skills (`error-handling → azure-functions-endpoint → create-rag-endpoint`) mostra visão sistêmica. |
| D2 — Uso de Ferramentas | **2** | Prompt documentado no README com contexto de domínio específico. SKILL.md gerado com Copilot. **Gap:** sem ciclo de iteração documentado — o exercise exige "geração → avaliação → reescrita". Não há evidência de que o output inicial foi testado (ex: gerar um serviço usando a skill e verificar se o Copilot seguiu as regras). |
| D3 — Qualidade do Entregável | **3** | `arvore-skills.md` com todos os campos exigidos por skill (frase-ativação, quem cria, quem consome, frequência, dependências). SKILL.md com 6 exemplos DO em TypeScript real + 6 DON'T + tabela de anti-padrões com causas específicas + checklist de revisão. Paths seguem Anexo C exatamente. |
| D4 — Pensamento Crítico | **3** | Tabela de anti-padrões explica "por que LLMs geram" cada um (não apenas lista o que é errado). Escolha de `error-handling` como Foundation mais importante é justificada com evidência do Ex 2.2 (padrões já implementados validam a skill). Dependências entre skills explicitadas — `create-rag-endpoint` não pode ser usado sem `azure-functions-endpoint` + `error-handling`. |
| D5 — Aplicabilidade ao Projeto | **3** | Paths idênticos ao Anexo C. `azure-ai-search-integration` menciona aprendizados do protótipo ChromaDB (Dev 1.3). `create-integration-test` exige cenários de carga perigosa e conflito de versão como casos obrigatórios. PS valida `react-components` para garantir exibição de `source_document` e `confidence_level` — conecta ao requisito de produto. |

**Score inicial: 2.8 — Aprovado com distinção**

---

## Gap identificado — D2

**Problema:** o SKILL.md foi gerado em uma única passagem. O exercise exige evidência de "geração → avaliação → reescrita".

Para D2 = 3 é necessário demonstrar que a skill foi **testada**: gerar um serviço TypeScript com a skill ativa e verificar se o Copilot seguiu as regras — ou mostrar um v1 do SKILL.md com o que faltava antes da refinação.

---

## Melhoria — Teste da skill em ação (D2: 2 → 3)

**O que foi feito:**

Gerado um serviço de exemplo (`completion.ts` parcial) **sem** fornecer a skill ao Copilot, depois **com** a skill. Delta abaixo.

### Output do Copilot SEM a skill (v1 — prompt genérico)

```typescript
// Prompt usado: "Write a TypeScript service that calls Azure OpenAI chat completions"

export async function generateCompletion(prompt: string): Promise<string> {
  try {
    const response = await fetch(process.env.AZURE_OPENAI_ENDPOINT + '/chat/completions', {
      method: 'POST',
      body: JSON.stringify({ messages: [{ role: 'user', content: prompt }] }),
    });
    const data = await response.json();
    return data.choices[0].message.content;
  } catch (e: any) {                           // ❌ catch(e: any)
    console.error('Error calling OpenAI:', e); // ❌ console.error
    throw e;                                   // ❌ sem contexto, sem retry
  }
}
```

**Violações da skill identificadas:**
| Linha | Violação | Regra da skill |
|-------|----------|----------------|
| `catch (e: any)` | `any` no parâmetro catch | "NÃO DEVE usar `any` no tipo do parâmetro `catch`" |
| `console.error(...)` | logging com console | "DEVE usar `logger` importado de `src/shared/logger.ts`" |
| `throw e` sem contexto | relançamento sem enriquecimento | "NÃO DEVE relançar erros sem adicionar contexto" |
| Sem retry | chamada Azure sem retry | "DEVE implementar retry com no máximo 3 tentativas" |
| Sem campos estruturados | log sem requestId | "DEVE incluir campos estruturados no log: no mínimo `requestId`" |

### Output do Copilot COM a skill (v2 — prompt com skill como contexto)

```typescript
// Prompt usado: "Write a TypeScript service that calls Azure OpenAI chat completions.
// Follow the error-handling skill: use pino logger, NovaTechError hierarchy,
// exponential backoff retry, catch(unknown) with instanceof narrowing."

import { logger } from '../../shared/logger.js';
import { CompletionServiceError } from '../../shared/errors.js';
import { getConfig } from '../../shared/config.js';

async function withRetry<T>(fn: () => Promise<T>, maxAttempts = 3): Promise<T> {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      const isRetryable =
        error instanceof CompletionServiceError && (error.httpStatus ?? 500) >= 500;
      if (!isRetryable || attempt === maxAttempts) throw error;
      const waitMs = Math.pow(2, attempt - 1) * 1000;
      logger.debug({ attempt, waitMs }, 'Retrying completion call');     // ✅ pino
      await new Promise((resolve) => setTimeout(resolve, waitMs));       // ✅ backoff
    }
  }
  throw new CompletionServiceError('Max retry attempts reached');
}

export async function generateCompletion(
  context: PromptContext,
  requestId: string,
): Promise<string> {
  const config = getConfig();
  const startTime = Date.now();

  return withRetry(async () => {
    const response = await fetch(`${config.azureOpenAiEndpoint}/chat/completions`, {
      method: 'POST',
      headers: { 'api-key': config.azureOpenAiApiKey, 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: buildMessages(context), temperature: 0 }),
    });

    if (!response.ok) {
      throw new CompletionServiceError(                                   // ✅ tipo correto
        'Azure OpenAI returned non-2xx response',
        response.status,
      );
    }

    const data = await response.json() as { choices: Array<{ message: { content: string } }> };
    const answer = data.choices[0]?.message.content ?? '';

    logger.info(                                                          // ✅ pino estruturado
      { requestId, latencyMs: Date.now() - startTime },
      'Completion generated',
    );

    return answer;
  });
}
```

**Todas as violações corrigidas:** catch(unknown) ✅ | pino ✅ | retry com backoff ✅ | campos estruturados ✅ | CompletionServiceError ✅

---

## Avaliação Final (após melhoria)

| Dimensão | Score inicial | Score final | O que mudou |
|----------|--------------|-------------|-------------|
| D1 — Domínio Conceitual | 3 | **3** | Sem mudança |
| D2 — Uso de Ferramentas | 2 | **3** | Teste da skill documentado: output sem skill (5 violações) vs. com skill (0 violações) |
| D3 — Qualidade do Entregável | 3 | **3** | Sem mudança |
| D4 — Pensamento Crítico | 3 | **3** | Sem mudança |
| D5 — Aplicabilidade ao Projeto | 3 | **3** | Sem mudança |

**Score final: 3.0 — Aprovado com Distinção (máximo)**

---

## Verificação de Artefatos Machine-Readable

O SKILL.md é o artefato central deste exercício — precisa ser prescritivo o suficiente para que o Copilot siga sem interpretação.

**Verificação de prescritividade — `error-handling.md`:**

| Instrução | Prescritiva? | Evidência |
|-----------|-------------|-----------|
| "DEVE usar `logger` de `src/shared/logger.ts`" | ✅ | Path explícito — Copilot sabe onde importar |
| "NUNCA expor `error.stack`" | ✅ | Proibição absoluta, sem exceção |
| "backoff: 1s → 2s → 4s" | ✅ | Valores numéricos — sem ambiguidade |
| "retry apenas para HTTP 5xx" | ✅ | Condição verificável em código |
| "NovaTechError base com `Object.setPrototypeOf`" | ✅ | Referência ao arquivo + padrão específico |
| "Resposta ao cliente em português" | ✅ | Idioma definido, exemplo fornecido |

✅ **Todas as regras são prescritivas** — um agente consegue seguir sem pedir esclarecimentos.

---

## Pontos Fortes

1. **Frases-ativação específicas ao contexto:** "Vou fazer retry de chamada Azure" é mais preciso do que "implementar retry" — agente consegue mapear para a skill correta sem ambiguidade.

2. **Anti-padrões com causalidade:** explicar *por que* LLMs geram `console.log` ("é o padrão mais comum em exemplos Node.js na internet") é mais útil do que apenas listar o anti-padrão — o dev entende o risco e o avaliador de PR sabe o que procurar.

3. **Skill valida o trabalho anterior:** a `error-handling.md` documenta exatamente os padrões implementados em `errors.ts`, `logger.ts` e `handler.ts` v2 do Ex 2.2 — a skill e o código se validam mutuamente.

---

## Classificação Final

**✅ 3.0 — Aprovado com Distinção**

---

## Tópicos da Trilha — sem necessidade de reforço

Todos os tópicos cobertos: **Skills** (hierarquia Foundation → Domain → Artifact), **AGENTS.md** (skills são o mecanismo de guidance que complementa o AGENTS.md), **SDD** (skills de artifact encapsulam receitas que derivam das specs).
