# dev-exercicio-1-3-prompt-builder.py
# NovaTech RAG Pipeline — Módulo de Montagem de Prompt
#
# Desenvolvido com GitHub Copilot.
# Prompts usados:
#   1. "Write a prompt assembly function that combines a static system prompt,
#       dynamic document chunks with source labels, and a user query"
#   2. "Add a conditional version conflict warning section that appears only when
#       chunks from conflicting document versions are present"
#   3. "Add a token budget estimator that breaks down the prompt by section"
#
# Copilot gerou build_prompt() e o template de formatação de chunks.
# O desenvolvedor ajustou: (a) a hierarquia de fontes (FAQ depois de documentos
# formais), (b) o aviso condicional de conflito de versão com instrução explícita
# ao LLM, (c) a estimativa de tokens por seção.

from typing import List, Dict, Optional

# ── System prompt (estático) ──────────────────────────────────────────────────
# Este bloco é fixo em toda query. Tokens estimados: ~480.
# Para atualizar as regras, editar aqui e recriar o índice de testes.
# Não usar para informação dinâmica (tier do cliente, histórico) — isso vai
# nas seções dinâmicas abaixo.

SYSTEM_PROMPT = """\
Você é o Assistente de Atendimento da NovaTech. Você responde perguntas \
de atendentes usando EXCLUSIVAMENTE o texto dos trechos de documentação fornecidos.

# REGRA FUNDAMENTAL
Você é um leitor de documentos, não um especialista em logística.
Não use conhecimento de domínio para completar, enriquecer ou expandir respostas.
Se a informação não estiver nos trechos abaixo, ela não existe para você.

# HIERARQUIA DE FONTES
Os trechos podem vir de tipos de documento diferentes. Siga esta ordem:
  1. Documentos formais (POL-XXX, PROC-XXX, SLA-XXXX) → fonte de verdade oficial.
  2. FAQ-Atendimento → use apenas para orientação operacional (ex: como abrir chamado).
     NUNCA use o FAQ como fonte de regras, prazos, valores ou exceções.
Se um trecho do FAQ contradisser um documento formal: siga o documento formal. Ignore o FAQ.

# GUARDRAILS — PROIBIÇÕES
❌ NUNCA invente números, ramais, prazos, versões ou procedimentos.
❌ NUNCA suavize proibições explícitas. "NÃO são elegíveis" = não pode, ponto final.
❌ NUNCA cite seções que não apareçam literalmente nos trechos fornecidos.
❌ Se dois trechos formais conflitam: apresente AMBOS com versão. Não escolha silenciosamente.

# GUARDRAILS — OBRIGAÇÕES
✅ Cite a fonte exatamente como aparece no trecho (ex: POL-001, seção 3.2).
✅ RESPOSTA PARCIAL: forneça o que há nos trechos + ❓ DADO AUSENTE para o que falta.
✅ RECUSA TOTAL (nenhum trecho cobre a pergunta): responda apenas
   "Não encontrei essa informação na documentação disponível. Recomendo escalar."

# FORMATO DE RESPOSTA
1. Resposta direta (baseada apenas nos trechos)
2. Detalhamento, se o trecho tiver mais informação relevante
3. Fonte: [exatamente como no trecho]
4. ⚠️ EXCEÇÃO: [somente se o trecho contiver exceção explícita]
5. ❓ DADO AUSENTE: [somente em resposta parcial — o que falta, sem inventar]
"""

# Template de aviso de conflito de versão (injetado condicionalmente)
VERSION_CONFLICT_TEMPLATE = """\

⚠️ ATENÇÃO — CONFLITO DE VERSÕES DETECTADO ({doc_base}):
Os trechos abaixo incluem chunks de versões diferentes do mesmo documento.
Apresente AMBAS as versões na sua resposta com os respectivos identificadores.
Instrua o atendente a verificar qual versão se aplica ao chamado antes de usar o valor.
"""


# ── Montagem do prompt ────────────────────────────────────────────────────────

def build_prompt(
    query: str,
    chunks: List[Dict],
    version_conflict: Optional[str] = None,
    client_tier: Optional[str] = None,
) -> str:
    """
    Monta o prompt completo para inferência do LLM.

    Anatomia do contexto (estático → dinâmico):
    ┌─────────────────────────────────────────────────────┐
    │ [ESTÁTICO]   System prompt + guardrails       ~480 tok│
    │ [DINÂMICO]   Metadados do cliente (opcional)   ~50 tok│
    │ [DINÂMICO]   Chunks recuperados (≤5 × ~400)  ~2000 tok│
    │ [CONDICIONAL] Aviso de conflito de versão       ~80 tok│
    │ [DINÂMICO]   Pergunta do atendente              ~30 tok│
    │                                         Total ~2640 tok│
    │ Margem disponível (janela 128K):        ~125.360 tok   │
    └─────────────────────────────────────────────────────┘

    Ordenação de chunks no prompt (mitigação de lost-in-the-middle):
    - Chunk mais relevante (rank 1) → posição 1 (alta atenção)
    - Segundo mais relevante → posição final antes da pergunta (alta atenção)
    - Demais → posições intermediárias
    - FAQ chunks são sempre colocados por último dentro do bloco de contexto

    NOTA: a reordenação requer implementação customizada — LangChain e
    LlamaIndex não expõem essa lógica nativamente (cf. análise 1.1, seção 3).
    """
    parts = []

    # 1. System prompt (estático)
    parts.append(SYSTEM_PROMPT)

    # 2. Metadados do cliente (dinâmico por sessão, opcional)
    if client_tier:
        parts.append(f"\n# CONTEXTO DO ATENDIMENTO\nTier do cliente: {client_tier}\n")

    # 3. Chunks recuperados (dinâmico por query)
    parts.append("\n# DOCUMENTOS DISPONÍVEIS PARA ESTA CONSULTA\n")

    # Separar FAQ dos documentos formais para colocar FAQ por último
    formal_chunks = [c for c in chunks if 'FAQ' not in c['doc_id'].upper()]
    faq_chunks = [c for c in chunks if 'FAQ' in c['doc_id'].upper()]

    # Reordenação lost-in-the-middle: rank1 primeiro, rank2 último
    ordered = _reorder_for_attention(formal_chunks) + faq_chunks

    for i, chunk in enumerate(ordered, 1):
        source_label = (
            f"[{chunk['doc_id']} — {chunk['secao']} | "
            f"versão {chunk['versao']} | emissão {chunk['data_emissao']}]"
        )
        parts.append(f"### Trecho {i} {source_label}\n{chunk['text']}\n")

    # 4. Aviso de conflito de versão (condicional)
    if version_conflict:
        parts.append(VERSION_CONFLICT_TEMPLATE.format(doc_base=version_conflict))

    # 5. Pergunta do atendente (dinâmico por query)
    parts.append(f"\n# PERGUNTA DO ATENDENTE\n{query}")

    full_prompt = '\n'.join(parts)

    # Aviso de orçamento (salvaguarda para sessões muito longas)
    est_tokens = int(len(full_prompt.split()) / 0.70)
    if est_tokens > 10_000:
        print(
            f"  ⚠️  Prompt size warning: ~{est_tokens} tokens estimados. "
            "Considere reduzir o número de chunks (MAX_CHUNK_TOKENS)."
        )

    return full_prompt


def _reorder_for_attention(chunks: List[Dict]) -> List[Dict]:
    """
    Reordena chunks para mitigar lost-in-the-middle:
    [rank1] [rank3] [rank4] [rank5] [rank2]
    → rank1 (posição 1, alta atenção) e rank2 (posição final, alta atenção).
    Chunks intermediários ficam no meio onde atenção é menor.
    """
    if len(chunks) <= 2:
        return chunks

    first = chunks[0]
    last = chunks[1]
    middle = chunks[2:]
    return [first] + middle + [last]


# ── Análise de tokens por seção ───────────────────────────────────────────────

def token_budget_breakdown(prompt: str) -> Dict:
    """
    Estima distribuição de tokens por seção do prompt.
    Útil para monitorar crescimento do contexto em sessões longas.
    """
    section_tokens = {}
    current_section = 'system'
    section_text = {
        'system': [],
        'client_context': [],
        'chunks': [],
        'conflict_warning': [],
        'question': [],
    }

    for line in prompt.split('\n'):
        if line.startswith('# CONTEXTO DO ATENDIMENTO'):
            current_section = 'client_context'
        elif line.startswith('# DOCUMENTOS DISPONÍVEIS'):
            current_section = 'chunks'
        elif line.startswith('⚠️ ATENÇÃO — CONFLITO'):
            current_section = 'conflict_warning'
        elif line.startswith('# PERGUNTA DO ATENDENTE'):
            current_section = 'question'
        section_text[current_section].append(line)

    for section, lines in section_text.items():
        text = '\n'.join(lines)
        words = len(text.split())
        section_tokens[section] = {
            'words': words,
            'est_tokens': int(words / 0.70),
        }

    section_tokens['TOTAL'] = {
        'words': sum(v['words'] for v in section_tokens.values()),
        'est_tokens': sum(v['est_tokens'] for v in section_tokens.values()),
    }

    return section_tokens


# ── Demo ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample_chunks = [
        {
            'doc_id': 'POL-001-POLITICA-DEVOLUCAO',
            'versao': '3.1',
            'data_emissao': '15/01/2024',
            'secao': '3.2 Exceções ao prazo geral',
            'text': (
                'As seguintes categorias de carga NÃO são elegíveis para devolução '
                'pelo processo padrão: Cargas perigosas classificadas nas classes 1 a 6 '
                'da ANTT, conforme Resolução ANTT nº 5.947/2021. Para essas categorias, '
                'o cliente deve entrar em contato com o setor de Gestão de Riscos '
                '(ramal 4500) para tratamento individual.'
            ),
        },
    ]

    prompt = build_prompt(
        query="Posso devolver carga perigosa?",
        chunks=sample_chunks,
        version_conflict=None,
        client_tier='Gold',
    )

    breakdown = token_budget_breakdown(prompt)

    print("=== Token Budget Breakdown ===")
    for section, data in breakdown.items():
        print(f"  {section:<20} {data['est_tokens']:>6} tokens est.")

    print(f"\n=== Prompt preview (primeiros 400 chars) ===\n{prompt[:400]}...")
