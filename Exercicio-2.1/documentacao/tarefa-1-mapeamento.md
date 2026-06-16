# Tarefa 1 — Mapeamento de necessidades → MCP servers

## O que o exercício pedia

> "Usando o **Claude**, mapeie cada necessidade do projeto para um *reference
> server* gratuito e local (filesystem, git, memory, everything). Para cada um:
> o que ele expõe (tools/resources/prompts), quem consome, e qual pasta/escopo
> ele recebe."

Necessidades de acesso listadas no enunciado:
- Código, specs e skills do repositório (ler e escrever).
- Documentação de negócio da NovaTech (ler — `docs/novatech/`).
- Corpus de chunks para "recuperação" (ler — `data/retrieval-corpus/`).
- Histórico/branches do repositório.
- Memória persistente de decisões e linguagem ubíqua.

## O que foi feito

Produzi o documento **`docs/mcp/mcp-mapping.md`** com a tabela completa
necessidade → server → tipo MCP exposto → consumidor → escopo:

| Necessidade | Server | Expõe | Escopo |
|---|---|---|---|
| Ler/editar código, specs, skills | `filesystem` | Tools (rw) | `./src ./specs ./skills` |
| Ler docs de negócio | `docs-readonly` | Tools (só leitura) | `./docs/novatech/` |
| Recuperar chunks (RAG) | `docs-readonly` | Tools (só leitura) | `./data/retrieval-corpus/` |
| Histórico/diff/branches | `git` | Tools (`git_log`, `git_diff`, …) | repo local |
| Memória persistente | `memory` | Tools (grafo) | `./.mcp/memory.json` |
| Aprender primitivas MCP | `everything` | Tools + Resources + Prompts | — (sandbox) |

**Decisão de desenho documentada:** dividi o `filesystem` em **duas instâncias**
(`filesystem` rw e `docs-readonly`) porque o server oficial não tem flag de
read-only por diretório — separar a fonte de verdade em outra instância é a
forma concreta de aplicar least privilege.

## Onde está o entregável
- `docs/mcp/mcp-mapping.md`
