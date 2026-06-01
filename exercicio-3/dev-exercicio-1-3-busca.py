# dev-exercicio-1-3-busca.py
# NovaTech RAG Pipeline — Módulo de Busca
#
# Desenvolvido com GitHub Copilot.
# Prompts usados:
#   1. "Write a search function that queries ChromaDB with a sentence-transformer
#       embedding and returns results with cosine similarity scores above a threshold"
#   2. "Add version conflict detection: warn when chunks from different versions
#       of the same base document (PROC-042 v1 and v2) appear in the same result set"
#
# Copilot gerou a estrutura de search() e a conversão distance→similarity.
# O desenvolvedor adicionou: _check_version_conflict(), a lógica de normalização
# de doc_id para detecção de conflito, e os comentários de decisão de arquitetura.

import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional

# ── Configuração ──────────────────────────────────────────────────────────────
CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "novatech_docs"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Threshold de similaridade mínima (cosine).
# Chunks abaixo desse valor não são passados ao LLM — aciona fallback.
# Valor calibrado empiricamente: 0.75 captura chunks relevantes e rejeita
# off-topic. Ajustar com base no benchmark (cf. análise 1.1, seção 6).
SIMILARITY_THRESHOLD = 0.35    # recalibrado após execução real (estimativa original 0.75 foi alta demais)

TOP_K_CANDIDATES = 20   # pool inicial para "reranking" (sem cross-encoder no PoC)
TOP_K_FINAL = 5         # chunks enviados ao LLM (lost-in-the-middle: ≤ 6 é seguro)

# Mapeamento de base de documento para detecção de conflito de versão.
# Documentos com o mesmo BASE_ID mas versões diferentes são conflitantes.
# Expandir conforme novos documentos versionados forem incorporados.
VERSION_CONFLICT_BASES = {
    'PROC-042-FRETE-ESPECIAL-V1': 'PROC-042',
    'PROC-042-V2-FRETE-ESPECIAL-REVISADO': 'PROC-042',
}


# ── Detecção de conflito de versão ────────────────────────────────────────────

def _normalize_doc_id(doc_id: str) -> str:
    """
    Normaliza doc_id para base canônica.
    Ex: PROC-042-FRETE-ESPECIAL-V1 e PROC-042-V2-FRETE-ESPECIAL-REVISADO
        → 'PROC-042' (mesmo base, versões diferentes).
    """
    return VERSION_CONFLICT_BASES.get(doc_id.upper(), doc_id.upper())


def filter_faq_if_formal_covers(chunks: List[Dict], formal_threshold: float = 0.40) -> List[Dict]:
    """
    Remove chunks do FAQ quando pelo menos um documento formal tem
    similaridade acima do threshold. Deve ser aplicada ANTES do slice
    para top_k — caso contrário, FAQ ocupa os ranks 1-N e chunks
    formais relevantes (fora do top-N original) nunca surfaceiam.

    Threshold 0.40 (vs. 0.45 anterior): formal docs sobre SLA/devolução
    atingem ~0.44 para queries conversacionais — 0.45 era alto demais.
    Para queries sem cobertura formal, docs formais ficam abaixo de 0.35,
    então o FAQ é mantido como fallback.
    """
    max_formal_sim = max(
        (c['similarity'] for c in chunks if 'FAQ' not in c['doc_id'].upper()),
        default=0.0,
    )
    if max_formal_sim >= formal_threshold:
        return [c for c in chunks if 'FAQ' not in c['doc_id'].upper()]
    return chunks


def _check_version_conflict(chunks: List[Dict]) -> Optional[str]:
    """
    Detecta quando chunks de versões conflitantes do mesmo documento
    aparecem juntos no resultado de busca.

    Retorna o base_id do documento conflitante, ou None se não há conflito.

    Esse é o principal modo de falha para o corpus da NovaTech:
    PROC-042 v1 (Norte=1.6) e v2 (Norte=1.8) no mesmo contexto → LLM
    pode silenciosamente combinar multiplicadores de versões diferentes.
    """
    seen_bases: Dict[str, List[str]] = {}

    for chunk in chunks:
        base = _normalize_doc_id(chunk['doc_id'])
        if base not in seen_bases:
            seen_bases[base] = []
        if chunk['doc_id'] not in seen_bases[base]:
            seen_bases[base].append(chunk['doc_id'])

    for base, versions in seen_bases.items():
        if len(versions) > 1:
            return base     # conflito detectado

    return None             # sem conflito


# ── Função de busca ───────────────────────────────────────────────────────────

def search(query: str, top_k: int = TOP_K_FINAL) -> Dict:
    """
    Recupera os top-K chunks mais relevantes para uma query.

    Fluxo:
      1. Codifica a query com o mesmo modelo usado na ingestão
      2. ANN search no ChromaDB (top TOP_K_CANDIDATES candidatos)
      3. Converte distance → similarity (cosine: sim = 1 - dist)
      4. Filtra pelo SIMILARITY_THRESHOLD
      5. Retorna top_k chunks com texto, metadados e score
      6. Sinaliza conflito de versão se detectado

    NOTA sobre reranking: a ausência de cross-encoder (ms-marco-MiniLM ou
    similar) é um gap conhecido. O ANN por similaridade de embedding retorna
    chunks semanticamente próximos, mas não necessariamente os mais úteis para
    a pergunta específica. Exemplo: "frete para Manaus" pode recuperar chunks
    de prazo de entrega (mesma seção do documento) antes do chunk de multiplicador.
    Reranker resolveria isso, mas adiciona ~200-500ms de latência (cf. análise 1.1,
    seção 5). Excluído do PoC — flagrado como melhoria prioritária.

    Retorna dict com:
      'chunks': lista de resultados
      'fallback': True se nenhum chunk passou o threshold
      'version_conflict': base_id do doc conflitante, ou None
    """
    model = SentenceTransformer(EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_collection(COLLECTION_NAME)

    query_embedding = model.encode([query])[0].tolist()

    raw = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(TOP_K_CANDIDATES, collection.count()),
        include=['documents', 'metadatas', 'distances'],
    )

    results = []
    for i, (doc, meta, dist) in enumerate(zip(
        raw['documents'][0],
        raw['metadatas'][0],
        raw['distances'][0],
    )):
        similarity = round(1.0 - dist, 4)
        if similarity >= SIMILARITY_THRESHOLD:
            results.append({
                'rank': i + 1,
                'text': doc,
                'doc_id': meta['doc_id'],
                'versao': meta['versao'],
                'data_emissao': meta['data_emissao'],
                'secao': meta['secao'],
                'tipo': meta['tipo'],
                'similarity': similarity,
            })

    # FAQ filter aplicado ANTES do slice: garante que chunks formais em ranks
    # 6-20 do pool de candidatos surfaceiem após remoção dos FAQ que dominavam
    # os ranks 1-5 com linguagem conversacional.
    results = filter_faq_if_formal_covers(results)
    results = results[:top_k]

    fallback = len(results) == 0
    version_conflict = _check_version_conflict(results) if results else None

    return {
        'chunks': results,
        'fallback': fallback,
        'version_conflict': version_conflict,
    }


# ── Saída formatada para testes ───────────────────────────────────────────────

def search_and_display(query: str) -> Dict:
    """
    Executa busca e imprime resultados formatados no stdout.
    Usado nos testes documentados no arquivo principal do exercício.
    """
    SEP = '─' * 65
    print(f"\n{SEP}")
    print(f"QUERY: {query}")
    print(SEP)

    result = search(query)

    if result['fallback']:
        print("  [FALLBACK] Nenhum chunk acima do threshold.")
        print("  → Resposta ao atendente: 'Não encontrei informação suficiente")
        print("    na base de conhecimento. Recomendo escalar para o supervisor.'")
        return result

    if result['version_conflict']:
        print(f"  ⚠️  CONFLITO DE VERSÃO: {result['version_conflict']}")
        print("     Ambas as versões foram recuperadas. "
              "O prompt_builder vai sinalizar isso ao LLM.")

    for r in result['chunks']:
        print(
            f"\n  Rank {r['rank']} | sim={r['similarity']:.4f} | "
            f"[{r['doc_id']} — {r['secao'][:45]}]"
        )
        print(f"  {r['text'][:180].strip()}...")

    return result


if __name__ == "__main__":
    TEST_QUERIES = [
        "Qual o prazo de devolução?",
        "Posso devolver carga perigosa?",
        "Qual o SLA do cliente Gold?",
        "Frete para 600kg para Manaus?",
        "Qual o multiplicador de frete para o Sudeste?",
    ]

    for q in TEST_QUERIES:
        search_and_display(q)
