# Avaliação do Exercício 2.2 — Desenvolvedor
**Papel:** Desenvolvedor | **Cenário:** 2 — Estruturação do Trabalho  
**Exercício:** 2.2 — Implementação de Spec com Spec Driven Development  
**Avaliador:** GitHub Copilot (skills: `avaliacao-foundation.md` + `avaliacao-desenvolvedor.md`)

---

## Checklist de Entregáveis

| Entregável exigido                    | Arquivo              | Status                                         |
| ------------------------------------- | -------------------- | ---------------------------------------------- |
| `tasks.md` com tasks atômicas         | `tasks.md`           | ✅ 12 tasks com ID, critérios, deps, estimativa |
| Código implementado com Copilot       | `codigo/src/`        | ✅ 6 arquivos — TASK-001 a 005 + handler        |
| Revisão crítica com ajustes propostos | `revisao-critica.md` | ✅ 2 problemas reais + fixes aplicados em v2    |

---

## Primeira Avaliação (entregável inicial)

> Estado do entregável **antes** da incorporação do Cenário 1 e antes da documentação do ciclo v1→v2.

| Dimensão                       | Score | Justificativa                                                                                                                                                                                                                                                   |
| ------------------------------ | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 — Domínio Conceitual        | **3** | SDD aplicado corretamente: plan → tasks atômicas → código. Referencia ADR-0002 no TASK-008 e ADR-0003 no tipo `SearchChunk` via campo `vigency_status`. Tasks são contratos executáveis, não listas de to-do.                                                   |
| D2 — Uso de Ferramentas        | **2** | Copilot usado com evidência (código gerado + revisão crítica). Porém sem documentação de prompts específicos nem de ciclo de refinamento explícito. O processo de iteração com a ferramenta não era visível.                                                    |
| D3 — Qualidade do Entregável   | **3** | `tasks.md` com 12 tasks, critérios de aceite objetivos, dependências e fases de paralelismo. Código TypeScript strict, Zod `safeParse`, Azure Functions v4, pino, hierarquia de erros — todos os padrões do plan respeitados. Paths corretos conforme Anexo C.  |
| D4 — Pensamento Crítico        | **3** | 2 bugs reais: `.catch(() => null)` retorna mensagem enganosa ao cliente; `context.invocationId` ignorado quebra correlação no Application Insights. Ambos com reprodução concreta + ajuste proposto. Seção "O que o Copilot acertou" demonstra análise honesta. |
| D5 — Aplicabilidade ao Projeto | **2** | ADRs e linguagem ubíqua presentes, Anexo C respeitado. **Gap:** não conectava ao protótipo open-source do Cenário 1 (Dev 1.3). O enunciado exige reconhecer que o protótipo validou a abordagem e que agora é código de produção com Azure.                     |

**Score inicial: 2.6 — Aprovado com distinção**

---

## Melhorias Realizadas

### Melhoria 1 — Conexão com o Cenário 1 (D5: 2 → 3)

**Problema identificado:** o entregável não conectava ao protótipo Python com ChromaDB e sentence-transformers construído no Dev 1.3. Nenhuma task referenciava descobertas concretas do protótipo como justificativa.

**O que foi feito:**
- Leitura dos artefatos do Cenário 1: `dev-exercicio-1-3-busca.py`, `dev-exercicio-1-3-pipeline-rag.md`, resultados dos 5 testes.
- Identificação das 6 descobertas do protótipo com impacto direto nas tasks de produção.
- Atualização de **TASK-007**, **TASK-008** e **TASK-011** com bloco `> Aprendizado do protótipo` referenciando função, teste e resultado concreto.
- Adição da seção **"Conexão com Cenário 1 — Protótipo → Produção"** no README com tabela de decisões validadas vs. mudanças para produção.

**Descobertas do protótipo incorporadas:**

| Descoberta                                                                          | Arquivo do protótipo   | Task atualizada |
| ----------------------------------------------------------------------------------- | ---------------------- | --------------- |
| `_check_version_conflict()`: PROC-042 v1/v2 coexistiram em 3/5 testes               | `busca.py`             | TASK-007        |
| `filter_faq_if_formal_covers`: FAQ dominava rank 1 (sim=0.5672) para carga perigosa | `busca.py`             | TASK-011        |
| `_reorder_for_attention()`: lost-in-the-middle mitigado nos Testes 3 e 5            | `prompt_builder.py`    | TASK-008        |
| `VERSION_CONFLICT_TEMPLATE`: LLM misturava v1/v2 sem instrução explícita            | `prompt_builder.py`    | TASK-008        |
| Token ratio 0.70 para PT-BR (não 0.75)                                              | análise 1.1 / pipeline | TASK-008        |
| Threshold 0.35 (estimativa 0.75 era inviável) — precisa recalibrar para Azure       | execução real          | TASK-007        |

---

### Melhoria 2 — Ciclo v1 → v2 documentado (D2: 2 → 3)

**Problema identificado:** os prompts usados com o Copilot não estavam documentados e o ciclo de refinamento não era visível — o entregável mostrava apenas o resultado final, não o processo.

**O que foi feito:**
- `handler.v1.ts` salvo como arquivo separado — preserva exatamente o output original do Copilot antes de qualquer edição.
- Dois ajustes da revisão crítica aplicados no `handler.ts` (v2):
  - **Fix 1:** `.catch(() => null)` → `try/catch` com `ValidationError('body inválido', 'body')`
  - **Fix 2:** `crypto.randomUUID()` → `context.invocationId` + `context.traceContext?.traceParent`
- Seção **"Processo de Geração com GitHub Copilot"** adicionada ao README com:
  - 3 prompts usados na geração (com contexto de domínio específico)
  - Código diff v1 vs v2 para cada correção com explicação de impacto em produção

**Delta v1 → v2 do `handler.ts`:**

```typescript
// FIX 1 — v1 (Copilot)           →   v2 (revisado)
request.json().catch(() => null)   →   try { body = await request.json() }
validateQueryInput(body)               catch { throw new ValidationError('body inválido', 'body') }

// FIX 2 — v1 (Copilot)           →   v2 (revisado)
crypto.randomUUID()                →   context.invocationId
// (context ignorado)              →   context.traceContext?.traceParent (W3C trace)
```

---

## Avaliação Final (após melhorias)

| Dimensão                       | Score inicial | Score final | O que mudou                                                                         |
| ------------------------------ | ------------- | ----------- | ----------------------------------------------------------------------------------- |
| D1 — Domínio Conceitual        | 3             | **3**       | Sem mudança — já estava completo                                                    |
| D2 — Uso de Ferramentas        | 2             | **3**       | Prompts documentados + `handler.v1.ts` preservado + ciclo v1→v2 explícito no README |
| D3 — Qualidade do Entregável   | 3             | **3**       | Sem mudança — já estava completo                                                    |
| D4 — Pensamento Crítico        | 3             | **3**       | Sem mudança — já estava completo                                                    |
| D5 — Aplicabilidade ao Projeto | 2             | **3**       | Conexão com Cenário 1 incorporada nas tasks e no README                             |

**Score final: 3.0 — Aprovado com Distinção (máximo)**

---

## Verificação de Artefatos Machine-Readable

O `tasks.md` é o artefato verificável deste exercício.

✅ **Prescritivo** — critérios de aceite são afirmações testáveis:
- *"`QueryResponse` contém `source_document` não-opcional"* → verificável pelo compilador
- *"Pergunta sobre carga perigosa + devolução SEMPRE retorna negativa, independente do LLM"* → verificável por teste unitário
- *"Lança `ValidationError` com campo `field`"* → verificável por `instanceof`

Nenhum critério usa linguagem vaga como "funcionar corretamente".

---

## Pontos Fortes

1. **Tasks genuinamente atômicas:** cada uma tem 1 arquivo-alvo, critérios objetivos, e pode ser implementada e testada de forma independente. O mapa de fases de paralelismo torna o `tasks.md` diretamente utilizável como board de sprint.

2. **Conexão protótipo → produção rastreável:** cada decisão técnica das tasks de serviço (TASK-007, 008, 011) cita o arquivo do protótipo, a função e o número do teste que a motivou. Zero decisões "do nada".

3. **Revisão crítica com sinal real:** o Problema 2 (`context.invocationId`) é uma falha que a maioria dos devs não percebe sem experiência com Azure Monitor — identificar e explicar o impacto em produção demonstra conhecimento além do básico.

---

## Classificação Final

**✅ 3.0 — Aprovado com Distinção**

---

