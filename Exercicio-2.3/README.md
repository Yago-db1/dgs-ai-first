# Exercício 2.3 — Definição de Estratégia de Skills do Projeto

**Papel:** Desenvolvedor  
**Ferramentas usadas:** Claude (árvore de skills + mapeamento) + GitHub Copilot (geração do SKILL.md Foundation)

---

## Checklist de Entregáveis

| Entregável exigido | Arquivo | Status |
|--------------------|---------|--------|
| Árvore de skills com hierarquia Foundation → Domain → Artifact | `arvore-skills.md` | ✅ |
| Mapeamento criação/consumo por papel para cada skill | `arvore-skills.md` (tabelas por skill) | ✅ |
| SKILL.md da Foundation mais importante gerado com Copilot | `codigo/skills/foundation/error-handling.md` | ✅ |

---

## Tarefa 1 — Árvore de skills

**Output:** [`arvore-skills.md`](./arvore-skills.md)

### Estrutura definida (12 skills)

```
Foundation (3)              Domain (4)                    Artifact (5)
─────────────────────────   ───────────────────────────   ─────────────────────────
typescript-conventions      azure-functions-endpoint      create-rag-endpoint
error-handling ⭐           azure-ai-search-integration   create-integration-test
project-structure           react-components              create-react-card
                            testing-patterns              create-adr
                                                          create-spec
```

**Por que estas 12 e não mais:** cada skill corresponde a um tipo de artefato produzido repetidamente no projeto (lista do enunciado). Não há skills teóricas — toda skill tem ao menos um arquivo-alvo no Anexo C que a consome diretamente. `create-adr` e `create-spec` foram adicionadas porque "documentação técnica de endpoints (ADRs)" e "specs de produto (SDD)" estavam na lista de artefatos do enunciado sem skill correspondente.

### Prompt e iteração com o Claude

**Prompt enviado ao Claude:**

```
Preciso definir a árvore de skills do projeto NovaTech Assistant.
Stack: TypeScript + Azure Functions v4 + Azure AI Search + Azure OpenAI (GPT-4o) + React + Vitest + pino.

Artefatos produzidos repetidamente:
- Endpoints Azure Functions com padrão RAG (query, feedback, health)
- Testes de integração para endpoints (mesmo padrão para todos)
- Componentes React para o painel web (cards de resposta, formulário de feedback)
- Documentação técnica de endpoints (ADRs, README de módulos)
- Specs de produto (requirements.md no formato SDD)

Hierarquia: Foundation (convenções globais) → Domain (padrões por camada) → Artifact (receitas de geração).
Skills ficam em /skills/foundation/, /skills/domain/, /skills/artifact/ (Anexo C).

Para cada skill: nome, frase-ativação, quem cria (papel específico), quem consome (papel + Copilot), frequência.
Importante: incluir papéis não-dev como criadores quando fizer sentido (QA para testes, PS para specs, TL para ADRs).
```

**Iterações v1 → v2:**

| O que o Claude propôs | O que foi corrigido | Por quê |
|---|---|---|
| 8 skills sem distinguir Domain de Artifact | 3 camadas distintas com 12 skills | Domain = padrão reutilizável; Artifact = receita completa de geração |
| `testing-patterns` e `create-integration-test` como um único item | Separados em Domain e Artifact | A receita (Artifact) consome os padrões (Domain) — são níveis diferentes |
| PS ausente como criador | Adicionado PS como criador de `create-spec` | PS é o dono dos requirements.md — incoerente deixá-lo só como consumidor |
| `create-adr` ausente | Adicionado como Artifact do TL | "Documentação técnica (ADRs)" estava na lista de artefatos do enunciado |

---

## Tarefa 2 — Mapeamento de criação e consumo

| Skill | Cria | Consome | Frequência |
|-------|------|---------|------------|
| `typescript-conventions` | Tech Lead | Todos os devs + Copilot (todo `.ts`) | ⬛⬛⬛⬛⬛ Máxima |
| `error-handling` ⭐ | Tech Lead | Dev Pleno, Dev Sênior, QA, Copilot | ⬛⬛⬛⬛⬛ Máxima |
| `project-structure` | Tech Lead | Dev Pleno, Dev Sênior, Copilot | ⬛⬛⬛⬜⬜ Alta |
| `azure-functions-endpoint` | TL + Dev Sênior | Dev Pleno, Dev Sênior, Copilot | ⬛⬛⬛⬛⬜ Alta |
| `azure-ai-search-integration` | Dev Sênior | Dev Pleno, Dev Sênior, Copilot | ⬛⬛⬛⬜⬜ Média |
| `react-components` | Dev Sênior + PS (validação) | Dev Pleno, Dev Sênior, Copilot | ⬛⬛⬜⬜⬜ Média |
| `testing-patterns` | QA + Dev Sênior | Todos os devs + QA + Copilot | ⬛⬛⬛⬛⬛ Máxima |
| `create-rag-endpoint` | Dev Sênior | Dev Pleno, Copilot | ⬛⬛⬛⬜⬜ Alta |
| `create-integration-test` | QA + Dev Sênior | Dev Pleno, QA, Copilot | ⬛⬛⬛⬛⬜ Alta |
| `create-react-card` | Dev Sênior | Dev Pleno, Copilot | ⬛⬛⬜⬜⬜ Baixa |
| `create-adr` | Tech Lead | Todos os papéis + Copilot | ⬛⬛⬛⬜⬜ Média |
| `create-spec` | **Product Specialist** | Tech Lead, Dev Pleno, Dev Sênior, Copilot | ⬛⬛⬛⬛⬜ Alta |

**Visão de time (não é só para devs):**
- **QA cria** `testing-patterns` e `create-integration-test` — são os maiores consumidores desses artefatos
- **Product Specialist cria** `create-spec` — é o dono dos `requirements.md` e define o formato SDD que o TL e os devs consomem
- **Product Specialist valida** `react-components` — a skill define como `QueryResponse` é exibida no painel; PS garante que `confidence_level` e `source_document` apareçam como exigem os guardrails
- **Tech Lead cria** todas as Foundation e `create-adr` — são convenções e artefatos de decisão que impactam o time inteiro

---

## Tarefa 3 — SKILL.md Foundation: `error-handling`

**Ferramenta:** GitHub Copilot  
**Output:** [`codigo/skills/foundation/error-handling.md`](./codigo/skills/foundation/error-handling.md)

### Por que `error-handling` é a Foundation mais importante

É a skill que todas as outras de serviço leem primeiro, e é onde o Copilot mais erra sem guidance:

| Sem a skill | Com a skill |
|---|---|
| `console.log(error)` | `logger.error({ requestId, code }, message)` |
| `catch (e: any)` | `catch (error: unknown)` + `instanceof` |
| `throw new Error('msg')` | `throw new SearchServiceError('msg', httpStatus)` |
| Retry em `for` loop | `withRetry()` com backoff 1s → 2s → 4s |
| `body: JSON.stringify({ error: e.message, stack: e.stack })` | Mensagem genérica em PT-BR ao cliente |
| Custom error sem `Object.setPrototypeOf` | `instanceof` correto em ES2022 |

### Conexão com Exercício 2.2

A skill documenta exatamente os padrões implementados no Ex 2.2:
- `errors.ts` (TASK-004) — hierarquia `NovaTechError` com `Object.setPrototypeOf`
- `logger.ts` (TASK-003) — pino singleton com campo `service`
- `handler.ts` v2 — `context.invocationId`, catch com `unknown`, mapeamento HTTP

A skill garante que o próximo dev que implementar TASK-006 a TASK-012 **não precise redescobrir** esses padrões.

### Prompt usado com o Copilot

```
Create a SKILL.md for the error-handling Foundation skill of the NovaTech Assistant project.
This skill is read by Copilot before generating any TypeScript file that does I/O.

The project uses:
- pino for structured logging (never console.log)
- Custom error hierarchy in src/shared/errors.ts (NovaTechError base class)
- Azure Functions v4 — errors map to HTTP status: ValidationError→400, service errors→502
- TypeScript strict mode — catch parameter must be unknown, not any
- Object.setPrototypeOf required in all custom error constructors (ES2022 instanceof fix)
- Exponential backoff retry for Azure calls: 1s → 2s → 4s, max 3 attempts, only for 5xx

Include:
1. Context (when to read this skill — activation phrases)
2. Prescriptive rules (MUST/MUST NOT)
3. DO examples with real TypeScript code
4. DON'T examples showing what Copilot generates WITHOUT this guidance
5. Anti-patterns table with "why LLMs generate this" and "impact"
6. Review checklist (7 items max)
```

---

## Autoavaliação dos critérios

| Critério | Atendido? | Evidência |
|----------|-----------|-----------|
| Árvore coerente com o projeto | ✅ | Cada skill mapeia a um artefato real da lista do enunciado (12 skills, incluindo `create-adr` e `create-spec`) |
| Criação/consumo multi-papel | ✅ | QA cria `testing-patterns` e `create-integration-test`; **PS cria `create-spec`**; TL cria Foundation e `create-adr`; PS valida `react-components` |
| SKILL.md Foundation concreto e prescritivo | ✅ | 6 exemplos DO com código TypeScript real; 6 exemplos DON'T com o que o Copilot gera sem guidance |
| Anti-padrões úteis | ✅ | Tabela com 6 anti-padrões, causa ("por que LLMs geram") e impacto em produção |
| Uso do Claude documentado | ✅ | Prompt e iterações v1 → v2 registrados na Tarefa 1 |
