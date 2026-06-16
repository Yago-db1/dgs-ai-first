# Tarefa 2 — Escrever o `.mcp/mcp.json` com least privilege

## O que o exercício pedia

> "Escreva o `.mcp/mcp.json` do projeto (preenchendo o scaffold vazio do starter
> repo). Aplique **least privilege** de forma concreta: o `filesystem` server
> deve receber só as pastas necessárias, e as fontes de leitura
> (`docs/novatech/`, `data/retrieval-corpus/`) devem ser tratadas como
> **read-only**; justifique por que cada escopo é o mínimo suficiente."

## O que foi feito

Preenchi o scaffold vazio (`{"mcpServers":{}}`) com a configuração final em
**`.mcp/mcp.json`**, aplicando least privilege concreto:

```json
{
  "mcpServers": {
    "filesystem":    { "args": ["...server-filesystem", "./src", "./specs", "./skills"] },
    "docs-readonly": { "args": ["...server-filesystem", "./docs/novatech", "./data/retrieval-corpus"] },
    "git":           { "args": ["mcp-server-git", "--repository", "."] },
    "memory":        { "env": { "MEMORY_FILE_PATH": "./.mcp/memory.json" } },
    "everything":    { }
  }
}
```

Decisões de least privilege aplicadas:
- **`filesystem` (rw)** recebe **só** `./src ./specs ./skills` — as pastas que o
  Dev realmente edita. **Não** recebe a raiz, `infra/`, `.git/` nem `.env`.
- **`docs-readonly`** isola as fontes de verdade (`docs/novatech`,
  `data/retrieval-corpus`) numa instância separada, para serem tratadas como
  somente-leitura.
- **`git`** aponta para o repo, mas expõe tools de VCS (não um FS aberto).
- **`memory`** grava num único arquivo versionável (`./.mcp/memory.json`).
- Nenhuma instância recebe segredos, IaC ou a raiz do repo.

**Observação técnica importante (também documentada em `riscos-seguranca.md`):**
o `server-filesystem` não enforça read-only por diretório — ele expõe
`write_file`/`edit_file` em qualquer pasta do escopo. Por isso o "read-only" da
`docs-readonly` é garantido por defesa em camadas (instância isolada + negar
tools de escrita no agente + atributo read-only no SO), não pelo server.

A justificativa de "mínimo suficiente" por server está detalhada em
`docs/mcp/mcp-mapping.md`.

## Onde está o entregável
- `.mcp/mcp.json` (preenchido)
- Justificativas: `docs/mcp/mcp-mapping.md`
