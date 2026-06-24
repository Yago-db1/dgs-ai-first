# Exercício 3.2 — Desenvolvedor

## Entregável

O exercício foi entregue com:

- revisão humana inicial do código gerado por IA
- segunda revisão crítica
- comparação honesta entre as duas revisões
- reescrita do módulo de feedback seguindo o AGENTS.md

---

## 1. Minha revisão inicial

Na primeira leitura do código gerado pelo Copilot, identifiquei imediatamente:

1. **Uso de `as any` sem validação com Zod**  
   - **Classificação:** violação do AGENTS.md / bug potencial  
   - **Motivo:** o projeto exige TypeScript strict e validação de input com Zod.

2. **Uso de `console.log` em vez de pino**  
   - **Classificação:** violação do AGENTS.md  
   - **Motivo:** o padrão do projeto exige o logger central com pino.

---

## 2. Segunda revisão crítica

Na revisão posterior, ampliei a análise e identifiquei:

1. **`require('@azure/cosmos')` dentro da função**  
   - **Classificação:** violação do AGENTS.md  
   - **Motivo:** o projeto exige imports estáticos no topo.

2. **Log de dado pessoal (`attendantEmail`)**  
   - **Classificação:** problema de segurança / privacidade  
   - **Motivo:** o e-mail do atendente era serializado no log.

3. **Ausência de validação dos campos de entrada**  
   - **Classificação:** bug potencial  
   - **Motivo:** `queryId`, `rating`, `comment` e `attendantEmail` eram persistidos sem validação.

4. **Falta de tratamento explícito para JSON inválido**  
   - **Classificação:** bug potencial  
   - **Motivo:** uma falha em `request.json()` quebraria o fluxo sem resposta controlada.

5. **Falta de tratamento explícito para erro de persistência**  
   - **Classificação:** bug potencial  
   - **Motivo:** a criação no Cosmos DB era assumida como sempre bem-sucedida.

6. **Uso de configuração sem validação prévia**  
   - **Classificação:** bug potencial  
   - **Motivo:** `COSMOS_CONNECTION_STRING` podia estar ausente e falhar só em runtime.

---

## 3. Comparação entre revisão humana e revisão posterior

Minha revisão inicial encontrou duas violações importantes do padrão do projeto:

- `as any` sem Zod
- `console.log` em vez de pino

A revisão posterior foi mais completa porque também capturou:

- `require` dinâmico
- log de PII (`attendantEmail`)
- falta de validação de input
- falta de tratamento explícito de erro
- falta de validação de configuração

Essa comparação mostra que a análise inicial foi útil, mas incompleta. A segunda revisão agregou principalmente em **segurança, privacidade e robustez operacional**.

---

## 4. Código reescrito

Arquivos entregues nesta pasta:

- `src\functions\feedback\handler.ts`
- `src\functions\feedback\validator.ts`
- `src\shared\types.ts`

### Correções aplicadas

1. **Validação com Zod**  
   O payload do feedback agora é validado com schema estrito antes de qualquer persistência.

2. **Logging com pino**  
   O handler usa `logger` compartilhado e remove `console.log`.

3. **Sem log de PII**  
   O log registra `queryId`, `rating` e presença de comentário, sem expor `attendantEmail`.

4. **Import estático**  
   `CosmosClient` foi movido para import no topo do arquivo.

5. **Tratamento explícito de erros**  
   O fluxo diferencia erro de validação, erro de configuração e erro interno.

6. **Cliente Cosmos reutilizável**  
   O container é resolvido por helper dedicado, evitando recriação desnecessária a cada request.

---

## 5. Evidência de aderência ao AGENTS.md

O código final atende os pontos exigidos no exercício:

- **TypeScript strict mode**: sem `as any`
- **Zod para validação de input**
- **pino para logging**
- **sem logar dados pessoais**
- **imports estáticos no topo**

---

## 6. Comparação humano vs. revisão posterior

| Item | Minha análise inicial | Revisão posterior |
|---|---|---|
| `as any` sem Zod | Identifiquei | Confirmado |
| `console.log` em vez de pino | Identifiquei | Confirmado |
| `require` dinâmico | Não identifiquei na primeira passada | Identificado depois |
| `attendantEmail` logado | Não identifiquei na primeira passada | Identificado depois |
| Falta de validação de campos | Parcial | Identificado claramente |
| Falta de tratamento de erro | Parcial | Identificado claramente |

---

## 7. Uso das ferramentas

### GitHub Copilot

O Copilot foi usado como apoio para:

- reestruturar o handler seguindo o padrão do projeto
- extrair a validação para um arquivo dedicado
- ajustar imports, tipos e fluxo de erro

### Revisão crítica posterior

A revisão posterior foi usada para confrontar a análise humana inicial e ampliar a lista de problemas antes da reescrita.

---

## 8. Conexão com o projeto NovaTech

O entregável foi conectado diretamente ao contexto do projeto:

- respeita o **AGENTS.md** do cenário 2
- segue o padrão já existente do starter repo (`shared/logger.ts`, `shared/errors.ts`)
- mantém aderência à estrutura pedida no enunciado (`src/functions/feedback/handler.ts`)

---

## 9. Conclusão

O código original gerado por IA tinha violações claras de padrão, riscos de privacidade e fragilidade operacional. A versão final reescrita corrige esses pontos com validação determinística, logging adequado, imports estáticos e tratamento explícito de erro, ficando aderente ao projeto NovaTech.

---

## Avaliação do Exercício 3.2

### Resumo

O entregável é forte na reescrita do módulo e na comparação honesta entre as revisões, mas perde nota no requisito central de análise humana inicial. As duas armadilhas mais sutis e importantes do exercício (`require` dinâmico e log de PII) só apareceram na segunda revisão.

### Scores por Dimensão

| Dimensão | Score | Justificativa |
|----------|-------|---------------|
| D1 — Domínio Conceitual | 3 | O entregável demonstra boa compreensão do que caracteriza revisão crítica de output de IA, diferenciando padrão de projeto, risco de segurança e bug potencial. |
| D2 — Uso de Ferramentas | 2 | Há evidência de uso combinado de revisão humana, Claude e Copilot, mas faltam exemplos mais concretos dos prompts ou do retorno da segunda revisão. |
| D3 — Qualidade do Entregável | 3 | A reescrita proposta atende ao AGENTS.md: valida input com Zod, remove `console.log`, usa import estático e evita logar dado pessoal. |
| D4 — Pensamento Crítico | 1 | O exercício era humano primeiro, e a análise própria inicial não identificou todas as armadilhas obrigatórias; especialmente, o log de `attendantEmail` só foi detectado depois, o que aciona a regra de corte. |
| D5 — Aplicabilidade ao Projeto | 3 | O resultado está bem conectado ao contexto do projeto, ao AGENTS.md e aos padrões esperados do repositório NovaTech. |

**Score do exercício: 2.4**

### Verificação de Armadilhas

- `as any` sem validação Zod — **identificada na análise própria**
- `console.log` em vez de pino — **identificada na análise própria**
- `require` dinâmico — **identificada apenas na segunda revisão**
- `attendantEmail` logado — **identificada apenas na segunda revisão**

### Pontos Fortes

- A comparação entre revisão inicial e revisão posterior é honesta e não tenta esconder o que passou despercebido.
- O código reescrito corrige os problemas centrais pedidos no exercício.
- A classificação dos achados por tipo de problema mostra maturidade na análise.

### Pontos de Melhoria

- Fortalecer a análise própria inicial para capturar todas as armadilhas obrigatórias antes de recorrer à IA.
- Incluir evidência mais direta do uso do Claude e do Copilot, com prompts ou síntese objetiva do que cada ferramenta agregou.
- Acrescentar exemplos de cenários inválidos esperados para deixar mais auditável a robustez do módulo reescrito.

### Classificação

Aprovado

### Tópicos da Trilha para Reforço

Revisão Crítica de Outputs de IA
