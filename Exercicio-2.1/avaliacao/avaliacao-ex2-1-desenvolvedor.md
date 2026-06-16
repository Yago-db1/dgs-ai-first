# Avaliação — Exercício 2.1 (Desenvolvedor) — Configuração de MCP Servers

> **Programa:** Trilha de Certificação AI First — DGS / DB1 Global Software
> **Cenário:** 2 — Fase de Estruturação do Trabalho
> **Papel:** Desenvolvedor
> **Exercício:** 2.1 — Configuração e uso real de MCP servers no projeto
> **Data da avaliação:** 2026-06-16
> **Skills utilizadas:** `avaliacao-foundation.md` + `avaliacao-desenvolvedor.md`

---

## Entregáveis avaliados

| Artefato | Arquivo |
|----------|---------|
| Mapeamento necessidade → server | `docs/mcp/mcp-mapping.md` |
| Config MCP com least privilege | `.mcp/mcp.json` + `.mcp.json` |
| Evidência de execução (automatizada) | `docs/mcp/evidencia-execucao.md` + `scripts/mcp-probe.py` |
| Evidência de uso com iteração de prompt | `docs/mcp/evidencia-agente.md` |
| Análise de riscos de segurança | `docs/mcp/riscos-seguranca.md` |
| Documentação de tarefa por tarefa | `docs/mcp/tarefa-1-mapeamento.md` a `tarefa-4-riscos.md` |

---

## Resumo

Entregável de alta qualidade que cobre todos os critérios do exercício com rigor técnico acima do esperado. O ponto mais forte é a validação empírica dos riscos de segurança — o participante **provou** que o `server-filesystem` não enforça read-only por diretório ao invés de apenas declarar o risco, e depois provou a mitigação com o atributo read-only do SO. A iteração de prompt documenta uma armadilha real de LLM (FAQ como fonte de regra crítica), com lição diretamente aplicável ao system prompt do NovaTech. O único gap menor é que as permissões `deny` para as tools de escrita do `docs-readonly` ficaram descritas na análise de riscos mas não foram configuradas em nenhum arquivo de settings do agente.

---

## Scores por Dimensão

| Dimensão | Score | Justificativa |
|----------|-------|---------------|
| **D1 — Domínio Conceitual** | **3** | Todas as 5 necessidades mapeadas corretamente para reference servers locais e gratuitos. Distingue corretamente que o `server-filesystem` expõe apenas **Tools** (não Resources ou Prompts), e que não há flag de read-only por diretório — o que motivou a solução de duas instâncias separadas. Conceito de least privilege aplicado de forma concreta e específica ao projeto NovaTech, não genericamente. |
| **D2 — Uso de Ferramentas** | **3** | Execução real via `mcp-probe.py`: os servers subiram de fato (handshake MCP completo), as três evidências foram coletadas (a: `read_text_file` POL-001, b: chunk `POL-001-B` conferido contra gabarito do Anexo B, c: `git_log` retornou commit `bbdd03a`). Iteração de prompt documentada com problema real identificado (agente usou `FAQ-03` distrator antes do refinamento) e melhoria concreta após reformulação. `roteiro-teste-tarefa-3.md` confirma explicitamente que a evidência automatizada é válida. |
| **D3 — Qualidade do Entregável** | **3** | `.mcp/mcp.json` sintaticamente correto, coerente com o mapeamento, partindo do scaffold do Anexo C. `mcp-mapping.md` com tabela completa (necessidade → server → tipo MCP → consumidor → escopo) e justificativa de "mínimo suficiente" por server. Evidência real de execução (não só arquivo de config). `mcp-probe.py` torna a prova reproduzível. Único ponto abaixo do ideal: o bloco `deny` para tools de escrita do `docs-readonly` está descrito em `riscos-seguranca.md` mas não configurado em nenhum arquivo de settings do agente (`.claude/settings.json` ou equivalente). |
| **D4 — Pensamento Crítico** | **3** | Dois riscos comprovados empiricamente (não teóricos): Risco 1 validado por teste negativo (`.env` e `AGENTS.md` negados por least privilege), Risco 2 validado por teste positivo (`write_file` funcionou em `docs/novatech` — o risco é real) e mitigação comprovada com `EPERM` + hash intacto. Identifica risco de supply chain via `npx -y` (insight sutil sobre cadeia de execução). Na iteração de prompt, reconhece que o modelo prioriza texto conversacional (FAQ) sobre normativo — observação diretamente aplicável ao system prompt de produção. |
| **D5 — Aplicabilidade ao Projeto** | **3** | Conecta cada server ao equivalente de produção que substituiria (Confluence → `docs/novatech`, Azure AI Search → `data/retrieval-corpus`, GitHub remoto → `git` local). Utiliza documentos reais do NovaTech (POL-001, SLA-2024, PROC-042v2) e valida o retrieval contra o gabarito do Anexo B. Segue a localização `.mcp/mcp.json` definida no Anexo C. A lição capturada na iteração ("prefira documentos normativos a FAQs para regras críticas") é diretamente aplicável à ADR-0003 (documentos contraditórios) e ao system prompt versionado em `/prompts/system-prompt.md`. |

**Score do exercício: 3,0 — Aprovado com distinção**

---

## Verificação de Artefatos Machine-Readable

**`.mcp/mcp.json`** é plenamente machine-readable: JSON válido, 5 servers com campos `command` e `args` corretos, coerente com o mapeamento documentado. Um agente ou ferramenta de CI consegue consumir este arquivo sem ambiguidade.

**`mcp-mapping.md`** é prescritivo para humanos, mas narrativo para agentes — serve como documentação de decisão, não como instrução para o agente. Isso é o correto para este tipo de artefato.

**`riscos-seguranca.md`** documenta mitigações acionáveis com comandos concretos (PowerShell `Set-ItemProperty`, bloco `permissions.deny`). O bloco de deny, porém, está apenas como exemplo em Markdown — para ser executável precisaria estar em `.claude/settings.json` ou equivalente.

---

## Pontos Fortes

1. **Validação empírica do Risco 2:** provar que `write_file` funcionou em `docs/novatech` (e não apenas afirmar que poderia funcionar) eleva o entregável de análise teórica para engenharia de segurança aplicada. A mitigação por camadas (instância isolada + deny tools + read-only no SO) foi igualmente provada.

2. **Decisão de arquitetura documentada:** a divisão em duas instâncias de `filesystem` com justificativa técnica ("o server oficial não tem flag de read-only por diretório") é uma decisão reutilizável por outros projetos e demonstra compreensão real das limitações da ferramenta.

3. **Iteração de prompt com lição capturada:** identificar que o modelo prioriza o `FAQ-03` (texto informal e conversacional) sobre o `POL-001-B` (documento normativo) antes do refinamento é uma observação de alta utilidade prática — gera regra direta para o system prompt de produção do NovaTech.

---

## Pontos de Melhoria

1. **`deny` de tools de escrita não está na config do agente** ← impacto em D3.
   O `riscos-seguranca.md` descreve o bloco `permissions.deny` para `docs-readonly`, mas ele não existe em nenhum arquivo de configuração do projeto. Para ser uma mitigação real (e não apenas documentada), criar `.claude/settings.json` com:
   ```json
   {
     "permissions": {
       "deny": [
         "mcp__docs-readonly__write_file",
         "mcp__docs-readonly__edit_file",
         "mcp__docs-readonly__move_file",
         "mcp__docs-readonly__create_directory"
       ]
     }
   }
   ```

2. **Tools de escrita do `git` server não têm restrição configurada.**
   `mcp-mapping.md` menciona "evitar `git_commit`, `git_reset`, `git_add`", mas não há deny configurado. Um agente com o server `git` ativo poderia fazer um commit sem gate humano. Adicionar o deny em `.claude/settings.json` ou documentar explicitamente que o controle é processual (validation gate do Tech Lead).

3. **Capturas interativas do Claude Code opcionais mas recomendadas.**
   `evidencia-agente.md` marca como opcional as capturas `claude mcp list` e `/mcp connected ✓`. Para a entrega oficial, executar o roteiro de `roteiro-teste-tarefa-3.md` no Claude Code e colar as saídas reforça a evidência interativa além da prova automatizada.

---

## Classificação

**✅ Aprovado com distinção (3,0 / 3,0)**

---

## Tópicos da Trilha para Reforço

Score ≥ 2,5 — nenhum tópico crítico para revisão.

Para aprofundamento voluntário:
- **MCP Permissions Model:** configuração de `allow`/`deny` por tool em Claude Code (`settings.json`) — relevante para os próximos exercícios onde o agente vai gerar e commitar código.
- **Prompt Injection via RAG:** o Risco 3 (`riscos-seguranca.md`) foi identificado mas não testado. Vale criar um chunk de teste com instrução injetada e verificar o comportamento do agente — antecipa problemas de produção.
