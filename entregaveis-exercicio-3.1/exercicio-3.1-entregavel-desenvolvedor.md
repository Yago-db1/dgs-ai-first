# Exercício 3.1 — Desenvolvedor

## Entregável

O exercício foi implementado com:

- schema Zod do structured output
- código do `response-validator`
- code review com correções reais

---

## 1. Schema Zod do structured output

Arquivo: `src\services\response-validator.ts`

```ts
export const AssistantStructuredOutputSchema = z
  .object({
    answer: z
      .string({ required_error: 'O campo answer é obrigatório' })
      .trim()
      .min(1, 'O campo answer não pode ser vazio'),
    source_document: z
      .string({ required_error: 'O campo source_document é obrigatório' })
      .trim()
      .min(1, 'O campo source_document não pode ser vazio'),
    confidence_score: z
      .number({ required_error: 'O campo confidence_score é obrigatório' })
      .min(0, 'O campo confidence_score deve ser maior ou igual a 0')
      .max(1, 'O campo confidence_score deve ser menor ou igual a 1'),
  })
  .strict();

export type AssistantStructuredOutput = z.infer<typeof AssistantStructuredOutputSchema>;
```

### O que o schema garante

- `answer`: string obrigatória e não vazia
- `source_document`: string obrigatória e não vazia
- `confidence_score`: número obrigatório entre `0` e `1`
- `.strict()`: rejeita campos extras

---

## 2. Código do `response-validator`

Arquivo: `src\services\response-validator.ts`

### Comportamento implementado

1. recebe a resposta bruta do modelo
2. aceita tanto objeto quanto JSON em string
3. valida contra o schema Zod
4. aplica os 2 guardrails determinísticos
5. em qualquer falha:
   - registra o motivo em log
   - retorna uma resposta padrão segura

### Guardrails implementados

#### Guardrail 1 — `source_document` obrigatório

Toda resposta deve conter `source_document`.

Se faltar ou vier inválido, a resposta é rejeitada.

#### Guardrail 2 — carga perigosa + devolução

Se a resposta tratar de **carga perigosa** junto com **devolução**, ela:

- é bloqueada se disser que a devolução é permitida
- é bloqueada se usar linguagem ambígua de exceção, autorização ou tratamento especial
- só passa se trouxer negativa clara compatível com a `POL-001`

### Fallback seguro

Quando a resposta é bloqueada, o validator retorna:

- `answer`: mensagem neutra de segurança
- `source_document`: `SYSTEM_FALLBACK`
- `confidence_score`: `0`

Isso evita fingir que existe uma fonte oficial válida quando a resposta falhou.

---

## 3. Code review com correções

### Problema 1 — fallback fingia fonte oficial

**Problema real:** o fallback usava `source_document: 'POL-001'` mesmo quando a resposta era rejeitada.

**Risco:** isso simulava uma citação documental legítima sem validação real.

**Correção aplicada:** o fallback passou a usar `source_document: 'SYSTEM_FALLBACK'`.

### Problema 2 — guardrail frágil para linguagem ambígua

**Problema real:** a versão anterior podia deixar passar respostas como:

- "oficialmente não pode, mas..."
- "pode haver exceção"
- "precisa de autorização"
- "tratamento especial"

Esse risco é real porque o `FAQ-Atendimento` do Anexo A é informal e traz esse tipo de formulação.

**Correção aplicada:** o guardrail foi reforçado para bloquear esse tipo de ambiguidade.

### Problema 3 — risco de falso positivo em frases corretas

**Problema real:** buscas genéricas demais podiam bloquear respostas corretas com negativa explícita.

**Correção aplicada:** a detecção de permissão indevida passou a usar padrões mais específicos.

---

## 4. Evidência de bloqueio real

Os guardrails não apenas registram logs: eles **substituem** respostas inválidas por fallback seguro.

Testes adicionados em `tests\response-validator.test.ts` cobrem:

- resposta válida
- JSON string válido
- schema inválido
- devolução de carga perigosa permitida
- devolução de carga perigosa sem negativa
- resposta correta com negativa
- resposta ambígua inspirada no FAQ informal

---

## 5. Evidência de uso do GitHub Copilot

### Uso da ferramenta

O GitHub Copilot foi usado como apoio para propor:

- o schema inicial do structured output
- a primeira estrutura do `response-validator.ts`
- a base da lógica de parse e validação

### Exemplos curtos de prompts/comandos usados com o Copilot

Exemplos representativos do tipo de instrução dado ao Copilot durante a implementação:

```text
Defina um schema Zod para structured output com os campos answer, source_document e confidence_score.
```

```text
Implemente um response-validator.ts que valide a resposta contra o schema, registre falhas em log e retorne uma resposta padrão segura.
```

```text
Adicione um guardrail determinístico para bloquear respostas sobre carga perigosa + devolução quando a resposta disser que a devolução é possível ou não trouxer negativa.
```

### Versão inicial sugerida pela ferramenta

Na versão inicial, a proposta do código já cobria:

- parse de resposta bruta
- validação contra schema
- bloqueio básico com fallback

Mas ainda deixava pontos de governança frágeis, especialmente no fallback e na detecção de linguagem ambígua.

### Revisão crítica posterior

Após a geração inicial, foi feita revisão manual/analítica do código produzido para verificar se o output do Copilot realmente atendia ao enunciado e aos guardrails do projeto.

Os principais problemas encontrados na revisão foram:

- fallback fingindo uma fonte oficial válida
- guardrail frágil para respostas ambíguas sobre devolução de carga perigosa
- risco de falso positivo em respostas corretas com negativa explícita

### Correções aplicadas após a revisão

Depois da revisão, o código foi ajustado para:

- trocar `POL-001` por `SYSTEM_FALLBACK` no fallback técnico
- bloquear linguagem de exceção, autorização e tratamento especial
- usar padrões mais específicos para detectar permissão indevida
- ampliar a suíte de testes para cobrir os casos corrigidos

### Resumo do fluxo Copilot + revisão

| Etapa | Papel do Copilot | Análise e ajuste humano |
|---|---|---|
| Schema inicial | Propôs a estrutura com `answer`, `source_document` e `confidence_score` | Validação da obrigatoriedade dos campos e endurecimento com `.strict()` |
| Validator inicial | Estruturou parse, validação e bloqueio básico | Revisão crítica para detectar problemas reais no fallback e no guardrail |
| Versão final | Base reaproveitada | Correções aplicadas e testes adicionados para evidenciar bloqueio real |

### Separação entre versão inicial e versão após review

| Aspecto | Versão inicial | Versão após review |
|---|---|---|
| Fallback | Retornava fonte oficial no bloqueio | Passou a usar `SYSTEM_FALLBACK` |
| Guardrail de carga perigosa | Detectava casos diretos | Passou a bloquear também exceção, autorização e tratamento especial |
| Matching de permissão | Mais genérico | Refinado com padrões mais específicos |
| Testes | Cobertura básica dos casos principais | Cobertura ampliada com caso ambíguo inspirado no FAQ |

---

## 6. Conexão com artefatos dos cenários 1 e 2

### Anexo A / documentação da NovaTech

O guardrail de **carga perigosa + devolução** foi implementado com base na `POL-001`, que define que cargas perigosas classes 1 a 6 não são elegíveis para devolução pelo processo padrão.

O entregável também considera o risco do `FAQ-Atendimento`, que é um documento informal e pode induzir respostas ambíguas ou permissivas demais.

### Guardrails formalizados no cenário 2

Os 2 guardrails implementados no código representam a tradução determinística de regras de produto que, no cenário 2, foram formalizadas como guardrails do assistente.

Trechos literais usados como referência:

> "Toda resposta DEVE conter o campo `source_document` — se não tiver, a resposta é rejeitada e substituída por mensagem padrão."

> "Respostas que mencionam 'carga perigosa' junto com 'devolução' DEVEM conter a negativa — se afirmarem que a devolução é possível, a resposta é bloqueada."

Ou seja:

- o prompt tenta induzir o modelo a responder corretamente
- o código garante que o sistema bloqueie a resposta caso a regra seja violada

### AGENTS.md e convenções do projeto

Mesmo com o `AGENTS.md` ainda marcado com `TODO` no starter repo, a implementação seguiu as convenções já presentes no projeto:

- uso do logger compartilhado (`shared/logger.ts`) com `pino`
- ausência de `console.log`
- separação entre validação de input/output e lógica de pipeline

### Arquitetura do cenário 3

O `response-validator.ts` foi implementado como parte da camada de **verification loop / guardrails** do harness.

Ele complementa o comportamento probabilístico do prompt com validação determinística de output, reforçando a governança antes que a resposta siga para a etapa final do pipeline.

### Relação com a ADR-0002 / context budget

Esta tarefa não implementa gerenciamento de contexto nem context budget diretamente.

Mesmo assim, o entregável respeita a separação arquitetural do projeto:

- montagem de contexto e orçamento de tokens ficam em outras etapas do pipeline
- `response-validator.ts` atua apenas na validação determinística da resposta gerada

Isso mantém aderência à arquitetura maior do assistente, em vez de misturar responsabilidade de contexto com responsabilidade de governança do output.

---

## 7. Critérios de avaliação

### O schema de structured output é válido e usa Zod corretamente

Sim. O schema usa `z.object(...)`, valida os 3 campos exigidos e usa `.strict()`.

### Os 2 guardrails realmente bloqueiam respostas inválidas

Sim. Quando há violação, a resposta não segue adiante: ela é substituída por fallback seguro.

### O code review identifica problemas reais

Sim. Os problemas corrigidos são concretos:

- fallback com fonte inventada
- fragilidade para linguagem ambígua
- risco de falso positivo

### A distinção entre prompt e código fica clara

- **Prompt (probabilístico):** tenta induzir o modelo a responder no formato certo e seguir as regras
- **Código (determinístico):** valida schema, aplica guardrails e bloqueia respostas inválidas

---

## Conclusão

O exercício atende ao objetivo de harness de governança: o modelo pode tentar responder corretamente, mas a decisão final de aceitar ou bloquear a resposta fica com o código determinístico.

---

## Avaliação do Exercício 3.1

### Resumo

O entregável cobre bem o objetivo de Harness Engineering e demonstra entendimento claro da diferença entre indução por prompt e bloqueio determinístico por código. O schema, os guardrails e o code review estão coerentes com o enunciado e conectados ao contexto da NovaTech.

### Scores por Dimensão

| Dimensão | Score | Justificativa |
|----------|-------|---------------|
| D1 — Domínio Conceitual | 3 | Explica corretamente structured output, validação com Zod e a complementaridade entre prompt probabilístico e verificação determinística. |
| D2 — Uso de Ferramentas | 2 | Há evidência concreta de uso do Copilot e revisão crítica do resultado, mas a evidência do uso do Claude no code review ficou mais descritiva do que demonstrada. |
| D3 — Qualidade do Entregável | 3 | O artefato está completo para o escopo pedido, com schema válido, fallback seguro e guardrails que efetivamente bloqueiam a resposta inválida. |
| D4 — Pensamento Crítico | 3 | O review identifica problemas reais e relevantes, como fonte inventada no fallback, fragilidade para ambiguidade e risco de falso positivo. |
| D5 — Aplicabilidade ao Projeto | 3 | O texto conecta o código à POL-001, ao FAQ informal, aos guardrails do cenário 2, ao AGENTS.md e à arquitetura do assistente. |

**Score do exercício: 2.8**

### Verificação de Armadilhas

Nenhuma armadilha obrigatória formal foi listada para este exercício. Ainda assim, o entregável identificou problemas reais esperados no review: fallback com fonte oficial indevida, detecção frágil de ambiguidade e risco de falso positivo.

### Pontos Fortes

- Explica com clareza a diferença entre o que o prompt tenta induzir e o que o código realmente garante.
- Implementa os 2 guardrails pedidos de forma alinhada ao enunciado e ao contexto da POL-001.
- Faz um code review útil, com problemas concretos e correções compatíveis com governança de output.

### Pontos de Melhoria

- Incluir evidência mais explícita do uso do Claude no review, por exemplo com prompts ou resumo do feedback retornado.
- Anexar o arquivo de testes citado no texto para reforçar a evidência prática de bloqueio real.
- Tornar a evidência do comportamento do fallback ainda mais verificável com exemplos de entrada e saída.

### Classificação

Aprovado com distinção

### Tópicos da Trilha para Reforço

Nenhum reforço prioritário.
