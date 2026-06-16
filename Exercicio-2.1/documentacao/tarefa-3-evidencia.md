# Tarefa 3 — Subir os servers e comprovar o uso

## O que o exercício pedia

> "**Suba os servers e comprove o uso:** abra o agente (Claude/Copilot) com os
> servers ativos e demonstre, com evidência, que ele consegue **(a)** listar e
> ler um documento de `docs/novatech/`, **(b)** recuperar um chunk relevante de
> `data/retrieval-corpus/` para uma pergunta do domínio (use o mapa de cobertura
> do Anexo B como gabarito), e **(c)** ler o histórico do repositório via `git`."

Critério de avaliação: *"Há **evidência real de uso** (não só o arquivo de
config): o agente leu documentação e recuperou chunk via MCP."*

## O que foi feito

Como os servers são locais, subi cada um **de fato** via stdio e executei o
roteiro de prova, capturando a saída real em **`docs/mcp/evidencia-execucao.md`**.
Para tornar a prova **reproduzível**, escrevi **`scripts/mcp-probe.py`** (cliente
MCP mínimo que faz `initialize` → `notifications/initialized` → `tools/call`).

Evidências coletadas (saída real, ambiente Windows · node v24 · uvx · git):

- **Handshake**: `secure-filesystem-server v0.2.0` e `mcp-git v1.27.2` subiram e
  listaram suas tools.
- **(a)** `read_text_file` no server `docs-readonly` retornou o cabeçalho de
  `docs/novatech/POL-001-politica-devolucao.md`.
- **(b)** Para a pergunta *"Posso devolver carga perigosa?"*, recuperei o chunk
  **`POL-001-B`** — exatamente o gabarito do mapa de cobertura do Anexo B — com a
  resposta correta (carga perigosa NÃO é devolvível pelo processo padrão).
- **(c)** `git_log` no server `git` retornou o histórico do repo (commit
  `bbdd03a`).
- **(d) bônus** — teste negativo de least privilege: leitura de `.env`,
  `infra/main.bicep` e `AGENTS.md` foi **NEGADA** (`Access denied - path outside
  allowed directories`), provando que o escopo mínimo é real.

> Nota sobre o agente: a prova foi feita exercitando os mesmos servers que o
> Claude Code/Copilot carregam de `.mcp/mcp.json`, via um driver MCP idêntico ao
> handshake que o agente faz. O script pode ser reexecutado a qualquer momento
> com `python scripts/mcp-probe.py` (ou `--json` para respostas cruas).

## Onde está o entregável
- `docs/mcp/evidencia-execucao.md` (prova automatizada/reproduzível — saída real do `mcp-probe.py`)
- `scripts/mcp-probe.py` (reproduz a prova)
- `docs/mcp/evidencia-agente.md` (prova pelo **agente real** Claude Code/Copilot + iteração de prompt documentada)
