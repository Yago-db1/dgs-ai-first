# Árvore de Skills — NovaTech Assistant

> Gerada para o exercício Dev 2.3 com base nos artefatos repetidos do projeto e na estrutura do Anexo C.  
> Hierarquia: Foundation (convenções globais) → Domain (padrões por camada) → Artifact (receitas de geração).

---

## Hierarquia visual

```
skills/
├── foundation/
│   ├── typescript-conventions.md   ← base de tudo: toda skill lê esta primeiro
│   ├── error-handling.md           ← erros, logging, retry — lida por toda skill de serviço
│   └── project-structure.md        ← organização de pastas e módulos
│
├── domain/
│   ├── azure-functions-endpoint.md ← padrão de HTTP trigger para todos os endpoints
│   ├── azure-ai-search-integration.md
│   ├── react-components.md
│   └── testing-patterns.md
│
└── artifact/
    ├── create-rag-endpoint.md      ← receita completa: validation + search + completion
    ├── create-integration-test.md  ← receita completa: msw + fixtures + assertions
    ├── create-react-card.md        ← receita completa: card + feedback form
    ├── create-adr.md               ← receita completa: ADR em /docs/adr/ com campos obrigatórios
    └── create-spec.md              ← receita completa: requirements.md no formato SDD (PS-owned)
```

---

## Foundation — Convenções globais

### `typescript-conventions`

| Campo | Valor |
|-------|-------|
| **Frase-ativação** | "Vou criar/editar um arquivo TypeScript no projeto NovaTech" |
| **Quem cria** | Tech Lead |
| **Quem consome** | Dev Pleno, Dev Sênior, Tech Lead — toda geração de código TypeScript pelo Copilot |
| **Frequência** | ⬛⬛⬛⬛⬛ Máxima — todo arquivo `.ts` do projeto |
| **Depende de** | nenhuma |
| **Descrição** | Convenções TypeScript strict do projeto: `strict: true` obrigatório, proibição de `any`, padrão de imports com `.js` em ESM, nomeação de interfaces (sem prefixo `I`), nomeação de tipos (PascalCase), exports nomeados (sem default exports). |

---

### `error-handling` ⭐ Foundation mais importante

| Campo | Valor |
|-------|-------|
| **Frase-ativação** | "Vou implementar tratamento de erro" / "Preciso logar algo" / "Vou fazer retry de chamada Azure" |
| **Quem cria** | Tech Lead |
| **Quem consome** | Dev Pleno, Dev Sênior, QA — toda geração de serviços e handlers pelo Copilot |
| **Frequência** | ⬛⬛⬛⬛⬛ Máxima — todo serviço, handler e função que faz I/O |
| **Depende de** | `typescript-conventions` |
| **Descrição** | Hierarquia de erros customizados (`NovaTechError`), logging estruturado com pino (nunca `console.log`), retry com exponential backoff para chamadas Azure, mapeamento de erros para HTTP status, proibição de expor stack trace ao cliente. Esta é a skill mais crítica: sem ela, o Copilot gera `console.log`, `catch(e: any)`, e expõe erros internos na resposta HTTP. |

---

### `project-structure`

| Campo | Valor |
|-------|-------|
| **Frase-ativação** | "Vou criar um novo módulo" / "Onde coloco este arquivo?" |
| **Quem cria** | Tech Lead |
| **Quem consome** | Dev Pleno, Dev Sênior — toda criação de novo arquivo ou módulo |
| **Frequência** | ⬛⬛⬛⬜⬜ Alta — na criação de cada novo módulo |
| **Depende de** | nenhuma |
| **Descrição** | Mapa de diretórios do Anexo C: onde cada tipo de arquivo vive (`src/functions/`, `src/services/`, `src/shared/`), convenção de nomeação de arquivos (kebab-case), regra de single responsibility por arquivo, padrão de exports (todos os símbolos públicos exportados via barrel quando aplicável). |

---

## Domain — Padrões por camada

### `azure-functions-endpoint`

| Campo | Valor |
|-------|-------|
| **Frase-ativação** | "Crie um novo endpoint Azure Function" / "Vou implementar um HTTP trigger" |
| **Quem cria** | Tech Lead + Dev Sênior |
| **Quem consome** | Dev Pleno, Dev Sênior, Copilot — criação de qualquer novo endpoint |
| **Frequência** | ⬛⬛⬛⬛⬜ Alta — query, feedback, health + futuros endpoints |
| **Depende de** | `typescript-conventions`, `error-handling` |
| **Descrição** | Padrão de HTTP trigger v4: registro com `app.http()`, assinatura `(request: HttpRequest, context: InvocationContext) => Promise<HttpResponseInit>`, uso de `context.invocationId` como requestId, parsing de body com try/catch, mapeamento de erros para HTTP status, nunca expor stack trace. |

---

### `azure-ai-search-integration`

| Campo | Valor |
|-------|-------|
| **Frase-ativação** | "Vou implementar busca vetorial" / "Preciso integrar com Azure AI Search" |
| **Quem cria** | Dev Sênior |
| **Quem consome** | Dev Pleno, Dev Sênior, Copilot — serviços de search e pipeline de ingestão |
| **Frequência** | ⬛⬛⬛⬜⬜ Média — search.ts + pipeline de ingestão |
| **Depende de** | `typescript-conventions`, `error-handling` |
| **Descrição** | Padrão de vector search no Azure AI Search: configuração do cliente, query com filtro de `vigency_status`, top-5 por score, detecção de conflito de versão (`vigency_warning`), retry com backoff. Incorpora aprendizados do protótipo ChromaDB (Dev 1.3): threshold de similaridade, dominância de FAQ, reordenação anti-lost-in-the-middle. |

---

### `react-components`

| Campo | Valor |
|-------|-------|
| **Frase-ativação** | "Crie um componente React para o painel web" / "Vou implementar um card de resposta" |
| **Quem cria** | Dev Sênior + Product Specialist (validação visual) |
| **Quem consome** | Dev Pleno, Dev Sênior, Copilot — todos os componentes do painel web |
| **Frequência** | ⬛⬛⬜⬜⬜ Média — painel web tem escopo limitado nesta fase |
| **Depende de** | `typescript-conventions`, `project-structure` |
| **Descrição** | Padrão de componentes React para o painel interno: componentes funcionais com TypeScript, props tipadas (sem `any`), separação de presentational vs. container, exibição obrigatória de `source_document` e `confidence_level` em toda resposta, padrão de feedback card. |

---

### `testing-patterns`

| Campo | Valor |
|-------|-------|
| **Frase-ativação** | "Vou escrever um teste" / "Escreva os testes para este módulo" |
| **Quem cria** | QA + Dev Sênior |
| **Quem consome** | Dev Pleno, Dev Sênior, QA, Copilot — toda geração de testes |
| **Frequência** | ⬛⬛⬛⬛⬛ Máxima — um arquivo de teste por módulo implementado |
| **Depende de** | `typescript-conventions`, `error-handling` |
| **Descrição** | Padrão de testes com Vitest: estrutura `describe/it` com frases descritivas, obrigatoriedade de arrange/act/assert explícitos, proibição de `toBeDefined()` e `toBeTruthy()` isolados, mocks HTTP com msw, factories para dados de teste, fixtures em `/tests/fixtures/` (chunks, queries, expected responses do domínio NovaTech). |

---

## Artifact — Receitas de geração

### `create-rag-endpoint`

| Campo | Valor |
|-------|-------|
| **Frase-ativação** | "Crie um endpoint RAG para [módulo]" / "Gere o código completo do endpoint de query/feedback" |
| **Quem cria** | Dev Sênior |
| **Quem consome** | Dev Pleno, Copilot — geração de qualquer endpoint que siga o padrão RAG |
| **Frequência** | ⬛⬛⬛⬜⬜ Alta — query endpoint + feedback endpoint + futuros |
| **Depende de** | `azure-functions-endpoint`, `azure-ai-search-integration`, `error-handling` |
| **Descrição** | Receita completa: validator.ts (Zod) + handler.ts (Azure Function v4) + response-builder.ts. Inclui os 5 passos do pipeline RAG, estrutura de TODOs para stages não implementados, mapeamento de erros, e `source_document` obrigatório no retorno. |

---

### `create-integration-test`

| Campo | Valor |
|-------|-------|
| **Frase-ativação** | "Escreva um teste de integração para [endpoint]" / "Crie os testes de integração do query endpoint" |
| **Quem cria** | QA + Dev Sênior |
| **Quem consome** | Dev Pleno, QA, Copilot — testes de integração de todos os endpoints |
| **Frequência** | ⬛⬛⬛⬛⬜ Alta — um por endpoint implementado |
| **Depende de** | `testing-patterns`, `error-handling`, `azure-functions-endpoint` |
| **Descrição** | Receita completa: setup msw para mockar Azure AI Search e Azure OpenAI, factory de `SearchChunk[]` com dados reais do domínio NovaTech (não "test string"), assertions específicas em `source_document`, `confidence_level`, e `answer`. Inclui casos de carga perigosa e conflito de versão como cenários obrigatórios. |

---

### `create-react-card`

| Campo | Valor |
|-------|-------|
| **Frase-ativação** | "Crie um card de resposta" / "Gere o componente de feedback para o painel web" |
| **Quem cria** | Dev Sênior |
| **Quem consome** | Dev Pleno, Copilot — componentes do painel web |
| **Frequência** | ⬛⬛⬜⬜⬜ Baixa — conjunto limitado de componentes no painel |
| **Depende de** | `react-components`, `typescript-conventions` |
| **Descrição** | Receita completa para cards do painel: ResponseCard (exibe resposta + fonte + confidence), FeedbackCard (formulário de reportar resposta incorreta). Props tipadas com `QueryResponse`, exibição de aviso quando `confidence_level: LOW` ou `NOT_FOUND`. |

---

### `create-adr`

| Campo | Valor |
|-------|-------|
| **Frase-ativação** | "Registre esta decisão como ADR" / "Vou documentar uma decisão arquitetural" |
| **Quem cria** | Tech Lead |
| **Quem consome** | Todos os papéis + Copilot (referência de contexto em qualquer artefato) |
| **Frequência** | ⬛⬛⬛⬜⬜ Média — uma por decisão técnica relevante ao longo do projeto |
| **Depende de** | `project-structure` |
| **Descrição** | Receita para criar ADRs em `/docs/adr/`: formato `ADR-NNNN-titulo-kebab-case.md`, campos obrigatórios (Status, Contexto, Decisão, Consequências), linkagem entre ADRs relacionadas (ex: ADR-0003 referencia ADR-0001 e ADR-0002). Toda decisão técnica ou de escopo com impacto no pipeline de RAG DEVE ser registrada como ADR. |

---

### `create-spec`

| Campo | Valor |
|-------|-------|
| **Frase-ativação** | "Crie o requirements.md de [módulo]" / "Vou escrever a spec SDD de [funcionalidade]" |
| **Quem cria** | **Product Specialist** |
| **Quem consome** | Tech Lead (gera `plan.md` a partir da spec), Dev Pleno, Dev Sênior, Copilot (verifica aderência ao implementar) |
| **Frequência** | ⬛⬛⬛⬛⬜ Alta — um `requirements.md` por módulo (5 módulos definidos no projeto) |
| **Depende de** | nenhuma (artefato de produto, não de código) |
| **Descrição** | Receita para criar `requirements.md` no formato SDD: outcomes orientados a resultado do usuário (não features técnicas), scope boundaries derivados dos bounded contexts, prior decisions referenciando ADRs da fase anterior, verification criteria testáveis pelo QA. Inclui estrutura de seções obrigatórias e exemplos de critérios verificáveis vs. vagos. |

---

## Mapa de dependências entre skills

```
typescript-conventions ◄──────── (todas as skills leem esta primeiro)
        │
        ▼
error-handling ◄─────────────── azure-functions-endpoint
        │                                │
        ├──► azure-ai-search-integration │
        │                                │
        └──► testing-patterns            ▼
                                  create-rag-endpoint
project-structure ◄────────────── react-components
        │                                │
        └──► create-adr                  ▼
                                  create-react-card

testing-patterns + azure-functions-endpoint ──► create-integration-test

(nenhuma) ──► create-spec  [PS-owned — artefato de produto, sem dependência de código]
```

---

## Regras de manutenção

| Situação | Responsável | Ação |
|----------|-------------|------|
| Mudança arquitetural (ex: novo padrão de error handling) | Tech Lead | Atualizar Foundation → propagar para Domain/Artifact que dependem |
| Nova camada ou serviço no projeto | Dev Sênior | Criar/atualizar skill Domain correspondente |
| Padrão de geração que Copilot erra recorrentemente | Qualquer Dev | Abrir PR adicionando ao anti-padrão da skill relevante |
| Skill desatualizada (> 1 sprint sem uso) | Tech Lead | Marcar como `deprecated` no cabeçalho |
