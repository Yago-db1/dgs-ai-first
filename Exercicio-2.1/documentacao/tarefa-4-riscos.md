# Tarefa 4 — Riscos de segurança no uso de MCP (setup local)

## O que o exercício pedia

> "Identifique ao menos **2 riscos de segurança** no uso de MCP servers **neste
> contexto local** e proponha mitigações (ex.: um `filesystem` server com escopo
> amplo demais expõe `.env`/segredos; um server com escrita habilitada permite
> que o agente altere arquivos sem revisão)."

Critério de avaliação: *"Os riscos são específicos ao setup local (exposição de
segredos por escopo amplo, escrita sem gate), com mitigação acionável."*

## O que foi feito

Documentei **4 riscos** específicos do setup local em
**`docs/mcp/riscos-seguranca.md`**, dois deles **comprovados empiricamente**
durante a coleta de evidência (não apenas teóricos):

| # | Risco | Comprovado? | Mitigação principal |
|---|-------|-------------|---------------------|
| 1 | Escopo amplo expõe `.env`/IaC | ✅ teste negativo: leitura fora do escopo é negada | Least privilege: só `src/specs/skills` |
| 2 | "Read-only" não é enforced → escrita sem gate | ✅ `write_file` funcionou em `docs/novatech` | Instância isolada + deny tools + read-only no SO (provado: `EPERM`, hash intacto) |
| 3 | Prompt injection via conteúdo recuperado (docs/chunks) | — | Conteúdo = dado, nunca instrução; `docs-readonly` sem tools de escrita |
| 4 | Supply chain: `npx -y`/`uvx` baixam e executam pacotes | — | Fixar versões; `.mcp.json` versionado e revisado |

Destaques:
- **Risco 1** foi validado pelo teste negativo (a leitura de `.env`,
  `infra/main.bicep` e `AGENTS.md` retornou `Access denied`).
- **Risco 2** foi o achado mais relevante: provei que a instância "read-only"
  **conseguiu escrever** em `docs/novatech` (o server não tem read-only por dir).
  A mitigação também foi provada — com read-only no SO, o `write_file` falha com
  `EPERM` e o conteúdo permanece intacto (hash igual).

Cada risco tem mitigação acionável e está ligado a artefatos concretos da config
(`.mcp/mcp.json`) e do fluxo do projeto (validation gates, política de aprovação
de servers do Ex. 2.2).

## Onde está o entregável
- `docs/mcp/riscos-seguranca.md` (análise completa)
