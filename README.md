# DGS AI First — Cenário 2: Fase de Estruturação

> **Trilha de Certificação AI First — DGS / DB1 Global Software**  
> **Papel:** Desenvolvedor | **Cenário:** 2 — Fase de Estruturação do Trabalho

---

## Contexto

Este repositório contém os entregáveis do **Cenário 2** da trilha de certificação AI First, referente à fase de estruturação do projeto **NovaTech Assistant** — um assistente de IA conversacional para atendentes da NovaTech (empresa de logística), que responde perguntas sobre SLAs, frete e devoluções com base em documentação interna indexada via RAG.

### Stack do projeto
- **Linguagem:** TypeScript (strict mode)
- **Backend:** Azure Functions v4 (HTTP triggers)
- **IA:** Azure OpenAI (GPT-4o) + Azure AI Search (pipeline RAG)
- **Frontend:** React (painel web)
- **Testes:** Vitest + msw
- **Logging:** pino (nunca `console.log`)
- **Validação:** Zod
- **IaC:** Bicep
- **Commits:** Conventional Commits

### Ferramentas AI utilizadas nos exercícios
- **GitHub Copilot** — geração de código, tasks, skills e AGENTS.md
- **Claude** (chat) — análise, arquitetura, documentação e especificações

---

## Exercícios

### Exercício 2.1 — Configuração e uso real de MCP servers

**Objetivo:** Configurar os MCP servers locais que fornecem contexto aos agentes de IA (acesso ao repositório, documentação NovaTech e corpus de chunks).

| Entregável | Arquivo |
|---|---|
| Mapeamento necessidade → server (Tools/Resources, escopo) | `Exercicio-2.1/documentacao/mcp-mapping.md` |
| `.mcp/mcp.json` com least privilege e justificativa | `Exercicio-2.1/config/mcp.json` |
| Evidência real de execução (agente leu docs, recuperou chunk, leu git) | `Exercicio-2.1/evidencias/` |
| Análise de ≥ 2 riscos de segurança com mitigação | `Exercicio-2.1/documentacao/riscos-seguranca.md` |
| Avaliação | `Exercicio-2.1/avaliacao/avaliacao-ex2-1-desenvolvedor.md` |

**Destaques:**
- Servers utilizados: `filesystem`, `git`, `memory`, `everything` (todos locais e gratuitos)
- Least privilege aplicado: `docs/novatech/` e `data/retrieval-corpus/` como read-only
- Validação empírica dos riscos: prova de que `server-filesystem` não enforça read-only por diretório sem configuração explícita

---

### Exercício 2.2 — Implementação de spec com Spec Driven Development

**Objetivo:** Converter o `plan.md` do query endpoint em `tasks.md` atômicas e implementar as primeiras tasks com o Copilot, seguido de revisão crítica.

| Entregável | Arquivo |
|---|---|
| `tasks.md` com 12 tasks atômicas (ID, critérios, deps, estimativa) | `Exercicio-2.2/tasks.md` |
| Código gerado com Copilot (TASK-001 a 005 + handler parcial) | `Exercicio-2.2/codigo/src/` |
| Revisão crítica com 2 problemas reais e ajustes aplicados (v1→v2) | `Exercicio-2.2/revisao-critica.md` |
| Avaliação | `Exercicio-2.2/avaliacao.md` |

**Arquivos de código gerados:**

| Arquivo | Task | Descrição |
|---|---|---|
| `src/shared/types.ts` | TASK-001 | Tipos TypeScript do domínio |
| `src/shared/errors.ts` | TASK-004 | Hierarquia de erros customizados |
| `src/shared/config.ts` | TASK-002 | Leitura e validação de variáveis de ambiente |
| `src/shared/logger.ts` | TASK-003 | Instância pino singleton |
| `src/functions/query/validator.ts` | TASK-005 | Schema Zod + função de validação |
| `src/functions/query/handler.ts` | TASK-012 (parcial) | Azure Function v4 com orquestração e error handling |

**Problemas identificados na revisão crítica:**
1. `request.json().catch(() => null)` — engole erro de parse e retorna mensagem enganosa ao cliente
2. `crypto.randomUUID()` em vez de `context.invocationId` — quebra correlação de logs no Application Insights

---

### Exercício 2.3 — Definição de estratégia de skills do projeto

**Objetivo:** Definir a árvore completa de skills do projeto (Foundation → Domain → Artifact) e criar o SKILL.md da skill Foundation mais importante.

| Entregável | Arquivo |
|---|---|
| Árvore de 12 skills com hierarquia Foundation → Domain → Artifact | `Exercicio-2.3/arvore-skills.md` |
| Mapeamento de criação/consumo por papel | `Exercicio-2.3/arvore-skills.md` |
| SKILL.md Foundation (`error-handling`) gerado com Copilot | `Exercicio-2.3/codigo/skills/foundation/error-handling.md` |
| Avaliação | `Exercicio-2.3/avaliacao.md` |

**Árvore de skills:**

```
Foundation (3)                Domain (4)                       Artifact (5)
──────────────────────────    ────────────────────────────     ──────────────────────────
typescript-conventions        azure-functions-endpoint         create-rag-endpoint
error-handling ⭐             azure-ai-search-integration      create-integration-test
project-structure             react-components                 create-react-card
                              testing-patterns                 create-adr
                                                               create-spec
```

---

## Estrutura do repositório

```
dgs-ai-first-cenario-2/
├── README.md
├── exercicio-2-fase-estruturacao.md   # Enunciado completo dos exercícios
├── cenario-1/                         # Referência — exercícios do cenário anterior
├── Exercicio-2.1/                     # MCP servers
│   ├── README.md
│   ├── avaliacao/
│   ├── config/
│   ├── documentacao/
│   └── evidencias/
├── Exercicio-2.2/                     # Spec Driven Development
│   ├── README.md
│   ├── avaliacao.md
│   ├── revisao-critica.md
│   ├── tasks.md
│   └── codigo/src/
└── Exercicio-2.3/                     # Estratégia de skills
    ├── README.md
    ├── avaliacao.md
    ├── arvore-skills.md
    └── codigo/skills/
```

---

## Tópicos cobertos neste cenário

| Tópico | Exercício |
|---|---|
| MCP (Model Context Protocol) — configuração e uso real de servers locais | 2.1 |
| Least privilege em MCP servers e análise de riscos de segurança | 2.1 |
| Spec Driven Development (SDD) — conversão plan → tasks atômicas | 2.2 |
| Geração de código com GitHub Copilot e revisão crítica | 2.2 |
| Hierarquia de skills (Foundation → Domain → Artifact) | 2.3 |
| SKILL.md prescritivo com exemplos DO/DON'T e anti-padrões | 2.3 |
