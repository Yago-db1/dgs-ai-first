# Revisão Crítica — Código Gerado pelo GitHub Copilot

> **Exercício 2.2 — Tarefa 3:** Identificar ao menos 2 pontos que precisariam de ajuste antes de um code review real.

---

## Contexto

O código foi gerado pelo **GitHub Copilot** com base no `plan.md` do query endpoint e nas tasks atômicas do `tasks.md`. A primeira task implementada cobre o setup do endpoint: tipos de domínio, erros customizados, configuração, logger, validação de input (Zod) e o handler Azure Functions v4.

---

## Problema 1 — `request.json()` engole erro de parse silenciosamente

### Código gerado

```typescript
const body = await request.json().catch(() => null);
const input = validateQueryInput(body);
```

### Por que é um problema

Quando o cliente envia um body que **não é JSON válido** (ex.: `question=foo` em form-encoding, ou body truncado), o `.catch(() => null)` retorna `null` silenciosamente. O `validateQueryInput(null)` então lança:

```
ValidationError: "O campo question é obrigatório" (field: "question")
```

A mensagem está **tecnicamente correta mas semanticamente errada**: o cliente recebe HTTP 400 dizendo que `question` está ausente, quando o problema real é que o body inteiro não é JSON. Isso dificulta o debug do lado do cliente.

Além disso, a informação de que o parse falhou **não é logada** — o `catch` descarta o erro original.

### Ajuste proposto

```typescript
let body: unknown;
try {
  body = await request.json();
} catch {
  throw new ValidationError(
    'O body da requisição deve ser um JSON válido',
    'body',
  );
}
const input = validateQueryInput(body);
```

**Impacto:** mensagem de erro correta ao cliente + erro de parse logado via `ValidationError` pelo `handleError`.

---

## Problema 2 — `context.invocationId` ignorado: logs não correlacionados no Azure Monitor

### Código gerado

```typescript
async function queryHandler(
  request: HttpRequest,
  context: InvocationContext, // ← nunca usado
): Promise<HttpResponseInit> {
  const requestId = crypto.randomUUID(); // ID gerado localmente
  ...
  logger.info({ requestId }, 'Query request received');
```

### Por que é um problema

O Azure Functions v4 injeta `context.invocationId` — um ID único por invocação que o Azure Monitor usa para correlacionar logs, métricas e traces no Application Insights. Ao ignorar esse ID e gerar um `crypto.randomUUID()` próprio, os logs do `pino` ficam **desconectados** dos traces do Azure.

Em produção, isso significa: quando um incidente ocorre e o time consulta o Application Insights, os logs do pino aparecem com um `requestId` diferente do `invocationId` registrado pelo runtime — impossível correlacionar sem busca manual.

### Ajuste proposto

```typescript
async function queryHandler(
  request: HttpRequest,
  context: InvocationContext,
): Promise<HttpResponseInit> {
  const requestId = context.invocationId; // usa o ID do Azure, não UUID local
  const startTime = Date.now();

  logger.info(
    {
      requestId,
      traceParent: context.traceContext?.traceParent, // W3C trace context para distributed tracing
    },
    'Query request received',
  );
```

**Impacto:** logs do pino ficam correlacionados com invocações no Application Insights, habilitando rastreamento completo de requests em produção.

---

## Resumo dos ajustes

| # | Arquivo | Problema | Severidade | Tipo |
|---|---------|----------|------------|------|
| 1 | `handler.ts` | Parse de JSON silencia erro real, retorna mensagem enganosa ao cliente | **Alta** | Bug de UX + observabilidade |
| 2 | `handler.ts` | `context.invocationId` ignorado, logs não correlacionados no Azure Monitor | **Alta** | Observabilidade em produção |

---

## O que o Copilot acertou (não inventado)

- Hierarquia de erros com `instanceof` e `Object.setPrototypeOf` para correção do prototype chain em ES2022
- Zod `safeParse` em vez de `parse` (evita exception não tipada)
- Campos `code` e `field` nos erros HTTP (facilita handling no cliente)
- `authLevel: 'function'` no registro da Azure Function (segurança por padrão)
- `crypto.randomUUID()` disponível nativamente no Node.js 18+ sem import (correto para o target ES2022)
