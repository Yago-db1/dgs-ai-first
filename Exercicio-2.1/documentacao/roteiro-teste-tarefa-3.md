# Roteiro de Teste — Tarefa 3 (uso real com o agente)

> Como subir os MCP servers no **Claude Code** e produzir a evidência exigida
> pela Tarefa 3: o agente **(a)** lê um documento de `docs/novatech/`,
> **(b)** recupera um chunk de `data/retrieval-corpus/` (conferido contra o
> gabarito do Anexo B) e **(c)** lê o histórico do repositório via `git`.
>
> Existem duas formas de evidência, e ambas valem:
> - **Automatizada/reproduzível:** `python scripts/mcp-probe.py` (ver `evidencia-execucao.md`).
> - **Interativa com o agente:** este roteiro.

---

## Pré-requisitos (já atendidos no starter repo)

- `node`/`npx`, `uvx` (Python) e `git` instalados.
- `.mcp/mcp.json` — config do exercício (Anexo C).
- `.mcp.json` na raiz — cópia que o **Claude Code carrega automaticamente**
  (o Claude Code lê `.mcp.json` da raiz, não `.mcp/mcp.json`).

---

## Passo 0 — Confirmar que o Claude Code enxerga os servers

```powershell
cd "...\Anexo-D-starter-repo-novatech-assistant\novatech-assistant"
claude mcp list
```

Esperado (linhas do projeto):
```
filesystem:    npx ... server-filesystem ./src ./specs ./skills
docs-readonly: npx ... server-filesystem ./docs/novatech ./data/retrieval-corpus
git:           uvx mcp-server-git --repository .
memory:        npx ... server-memory
everything:    npx ... server-everything
```
Na primeira vez aparecem como `⏸ Pending approval` — é a trava de segurança do
Claude Code (servers de `.mcp.json` de projeto só rodam após aprovação;
mitigação do Risco 4 / supply chain).

📸 **Captura 1** — saída do `claude mcp list`.

---

## Passo 1 — Abrir o agente e aprovar

```powershell
claude
```
- Aprove os MCP servers do projeto quando perguntado (Yes / "use this and all future").
- Digite `/mcp` → os 5 servers devem aparecer como **connected ✓**.

📸 **Captura 2** — `/mcp` mostrando os servers conectados.

---

## Passo 2 — As três evidências

### (a) Listar e ler um documento de `docs/novatech/`
Prompt no chat:
```
Usando o MCP server docs-readonly, liste os arquivos em docs/novatech e depois
leia o documento POL-001 (política de devolução). Mostre o início do conteúdo.
```
Esperado: o agente chama `docs-readonly - list_directory` e
`docs-readonly - read_text_file`; retorna o cabeçalho do POL-001
("# POL-001 — Política de Devolução de Mercadorias", Versão 3.1, ...).

📸 **Captura 3** — a chamada da tool MCP + o conteúdo lido.

### (b) Recuperar um chunk relevante de `data/retrieval-corpus/`
Prompt no chat:
```
Usando o MCP server docs-readonly, abra data/retrieval-corpus/chunks-novatech.md
e me diga qual chunk responde à pergunta de um atendente:
"Posso devolver carga perigosa?". Cite o ID do chunk.
```
Esperado: o agente lê o corpus via MCP e cita o chunk **POL-001-B**.

📸 **Captura 4** — o ID do chunk citado.

**Conferência contra o gabarito (Anexo B — mapa de cobertura):**

| Pergunta | Chunk que DEVE ser recuperado |
|----------|-------------------------------|
| "Posso devolver carga perigosa?" | **POL-001-B** |
| "Qual o SLA do cliente Gold?" | **SLA-2024-B** |
| "Qual o multiplicador para o Sudeste?" | **PROC-042v2-B** |

Se o ID citado bater com a coluna da direita, a recuperação está correta.

### (c) Ler o histórico do repositório via `git`
Prompt no chat:
```
Usando o MCP server git, me mostre o histórico de commits deste repositório (git_log).
```
Esperado: o agente chama `git - git_log` e retorna o commit
`bbdd03a … chore: starter repo (Anexo D) — estrutura + dados semeados...`.

📸 **Captura 5** — a chamada `git_log` + o commit.

---

## Passo 3 — Salvar a evidência

Qualquer uma das opções:
- **Screenshots** das capturas 1–5.
- Dentro do `claude`, rode `/export` para salvar a conversa inteira.
- Copie o texto do terminal para um `docs/mcp/evidencia-agente.md`.

---

## Checklist de "passou"

- [ ] `/mcp` mostra os 5 servers **connected ✓**.
- [ ] (a) o agente **chamou a tool MCP** (não leu por conta própria) e devolveu o POL-001.
- [ ] (b) o ID do chunk citado **bate com o gabarito do Anexo B**.
- [ ] (c) `git_log` retornou o commit do starter repo.

## Observações
- O Claude Code pede aprovação a cada tool MCP na primeira vez — é normal;
  aprove (ou "don't ask again for this tool").
- Se `/mcp` não mostrar os servers, confirme que abriu o `claude` **de dentro**
  de `novatech-assistant/` (onde está o `.mcp.json`).
