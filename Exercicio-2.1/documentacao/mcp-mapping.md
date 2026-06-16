# MCP — Mapeamento de Necessidades → Servers (Exercício Dev 2.1, Tarefa 1)

> Todos os servers são *reference servers* oficiais do Model Context Protocol,
> rodam **localmente** via `npx`/`uvx` e **não dependem de nenhum serviço pago
> ou externo** (sem Azure, Confluence ou GitHub). Substituem, em ambiente local,
> as fontes que na operação real seriam Confluence (docs), Azure AI Search
> (retrieval) e GitHub (repo).

## Tabela de mapeamento

| # | Necessidade do projeto | Server | Tipo MCP exposto | Quem consome | Escopo / aponta para |
|---|------------------------|--------|------------------|--------------|----------------------|
| 1 | Ler **e editar** código, specs e skills | `filesystem` | **Tools** (read/write/edit/list/search) | Dev + Tech Lead (Claude Code, Copilot) | `./src` `./specs` `./skills` (read-write) |
| 2 | Ler documentação de negócio da NovaTech (era Confluence) | `docs-readonly` | **Tools** (uso restrito a leitura) | Todos os agentes | `./docs/novatech/` (Anexo A) |
| 3 | "Recuperar" chunks para RAG (era Azure AI Search) | `docs-readonly` | **Tools** (uso restrito a leitura) | Todos os agentes | `./data/retrieval-corpus/` (Anexo B) |
| 4 | Histórico, diff e branches do repo (era GitHub) | `git` | **Tools** (`git_log`, `git_diff`, `git_show`, `git_branch`, …) | Dev + Tech Lead | repositório local (`.`) |
| 5 | Memória persistente de decisões e linguagem ubíqua | `memory` | **Tools** (grafo: create/read entities & relations) | Todos os agentes | grafo local em `./.mcp/memory.json` |
| 6 | Explorar/aprender as primitivas de MCP | `everything` | **Tools + Resources + Prompts** (demo) | Dev (aprendizado) | — (sandbox didático) |

## Decisão de desenho: por que **duas** instâncias de `filesystem`?

O `@modelcontextprotocol/server-filesystem` **não tem flag de "read-only" por
diretório**: qualquer pasta passada nos `args` recebe acesso completo, incluindo
as tools `write_file`, `edit_file`, `move_file` e `create_directory`
(comprovado empiricamente — ver `evidencia-execucao.md`, seção "Risco 2").

Para aplicar least privilege de forma concreta, separamos em dois servers:

- **`filesystem`** — recebe só `./src ./specs ./skills` (as pastas que o time
  realmente edita). É o único com intenção de escrita.
- **`docs-readonly`** — recebe `./docs/novatech` e `./data/retrieval-corpus`
  (as fontes de negócio/RAG). São **fontes de verdade que o agente nunca deve
  alterar**. O caráter read-only é garantido por **defesa em camadas** (não pelo
  server): (1) escopo isolado nesta instância, (2) negar as tools de escrita
  deste server no agente, e (3) atributo read-only no SO. Ver
  `riscos-seguranca.md`, Risco 2.

Nenhuma instância recebe a **raiz do repo**, `./infra`, `./.git`, `./.github`
nem arquivos de segredo (`.env*`) — esses ficam **fora de todo escopo MCP**.

## Justificativa de "mínimo suficiente" por server

- **`filesystem` (`./src ./specs ./skills`)** — são exatamente os artefatos que
  o Dev cria/edita nesta fase. Não inclui `docs`/`data` (são leitura), nem
  `infra` (IaC sensível, fora do fluxo de codificação), nem a raiz (evita expor
  `package.json` de build, configs e, sobretudo, qualquer `.env`).
- **`docs-readonly` (`./docs/novatech ./data/retrieval-corpus`)** — só as duas
  fontes que o assistente precisa "ler" e "recuperar". Mínimo suficiente para as
  evidências (a) e (b) do exercício.
- **`git` (`--repository .`)** — precisa enxergar o repo inteiro para dar
  histórico/diff, mas as tools são de VCS (não um FS aberto); o risco é mitigado
  evitando as tools de escrita (`git_commit`, `git_reset`, `git_add`).
- **`memory` (`./.mcp/memory.json`)** — grafo isolado num único arquivo
  versionável; não toca o resto do FS.
- **`everything`** — sem escopo de FS; é sandbox didático das primitivas MCP.

## Como o agente carrega esta config

- **Claude Code**: lê `.mcp.json` na raiz do projeto (ou via `claude mcp add`).
  Para esta estrutura, aponte/importe o `.mcp/mcp.json` ao iniciar o `claude`
  de dentro de `novatech-assistant/`.
- **Reprodução headless / CI**: `python scripts/mcp-probe.py` sobe cada server,
  faz o handshake e executa o roteiro de prova (ver evidência).
