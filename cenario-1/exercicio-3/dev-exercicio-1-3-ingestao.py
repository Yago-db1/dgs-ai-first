# dev-exercicio-1-3-ingestao.py
# NovaTech RAG Pipeline — Módulo de Ingestão
#
# Desenvolvido com GitHub Copilot.
# Prompts usados:
#   1. "Write a Python function that splits a markdown document into semantic chunks
#       based on headings, keeping tables as atomic units"
#   2. "Add a function to detect markdown sections that contain critical negations
#       (NÃO são elegíveis, exceto, salvo) and prevent them from being split"
#   3. "Generate ChromaDB upsert code for a list of text chunks with metadata"
#
# Copilot gerou o esqueleto das funções chunk_by_section(), is_table() e
# has_critical_negation(). O desenvolvedor ajustou: (a) o regex de split para
# preservar o heading no corpo do chunk, (b) o ratio de tokens para PT-BR (0.70),
# (c) a lógica de overlap de 80 tokens nas seções fragmentadas.

import os
import re
import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict

# ── Configuração ──────────────────────────────────────────────────────────────
DOCS_DIR = "./docs"
CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "novatech_docs"

# paraphrase-multilingual-MiniLM-L12-v2: modelo multilingual que suporta PT-BR.
# Não usar all-MiniLM-L6-v2 (treinado apenas em inglês) — queda de qualidade
# em português estimada em 10-15% no Recall@5 (decisão de arquitetura pendente:
# validar com benchmark do exercício 1.1, seção 6).
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

MAX_CHUNK_TOKENS = 600   # teto por chunk (seções menores = chunk único)
TOKEN_RATIO = 0.70       # palavras → tokens para PT-BR (BPE; cf. análise 1.1)


# ── Funções auxiliares ────────────────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """Estimativa de tokens para texto em português (ratio BPE ~0.70)."""
    return int(len(text.split()) / TOKEN_RATIO)


def is_table(text: str) -> bool:
    """Detecta blocos de tabela markdown (mínimo: cabeçalho + separador + 1 linha)."""
    lines = [l for l in text.strip().split('\n') if '|' in l]
    return len(lines) >= 3


def table_to_anchored_text(section: str, heading_text: str) -> str:
    """
    Converte chunk de tabela markdown para texto com prefixo em linguagem natural.

    Gera uma linha NL por linha de dados da tabela (ex: "Gold: Até 2h úteis.
    Silver: Até 4h úteis."), seguida da tabela original. Resolve o problema de
    embeddings pobres para pipe syntax: o modelo foi treinado em linguagem natural
    e trata pipes como ruído, diluindo a similaridade com queries conversacionais.
    """
    table_lines = [l for l in section.strip().split('\n') if '|' in l]

    if len(table_lines) < 3:
        prefix = f"[Tabela: {heading_text}]\n\n" if heading_text else ""
        return prefix + section

    # Parse: cabeçalho (índice 0) + separador (índice 1) + dados (índice 2+)
    headers = [h.strip() for h in table_lines[0].split('|') if h.strip()]
    nl_rows = []
    for row_line in table_lines[2:]:
        cells = [c.strip() for c in row_line.split('|') if c.strip()]
        if not cells:
            continue
        parts = []
        for i, cell in enumerate(cells):
            label = headers[i] if i < len(headers) else f"col{i + 1}"
            parts.append(f"{label}: {cell}")
        nl_rows.append(". ".join(parts) + ".")

    nl_summary = f"[Tabela: {heading_text}]\n" + "\n".join(nl_rows)
    return nl_summary + "\n\n" + section


def has_critical_negation(text: str) -> bool:
    """
    Detecta seções com negações semânticas críticas.

    Risco: se "NÃO são elegíveis" for separado dos itens da lista abaixo dele,
    o LLM pode interpretar cada item como elegível (inversão de regra).
    Essas seções são tratadas como unidades atômicas — nunca fragmentadas.
    """
    patterns = [
        r'NÃO\s+(são|é|estão)\s+elegíveis',
        r'não\s+(se\s+aplica|é\s+permitido|podem\s+ser)',
        r'\bexceto\b',
        r'\bsalvo\b',
        r'\bvedado\b',
    ]
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def extract_doc_metadata(content: str, filename: str) -> Dict:
    """Extrai doc_id, versão e data a partir do cabeçalho do documento."""
    doc_id = filename.replace('.md', '').upper()

    version_match = re.search(r'\*\*Versão:\*\*\s*(.+)', content)
    date_match = re.search(
        r'\*\*(Data de emissão|Última atualização):\*\*\s*(.+)', content
    )

    return {
        'doc_id': doc_id,
        'versao': version_match.group(1).strip() if version_match else 'unknown',
        'data_emissao': date_match.group(2).strip() if date_match else 'unknown',
        'filename': filename,
    }


# ── Chunking semântico ────────────────────────────────────────────────────────

def chunk_by_section(content: str, doc_metadata: Dict) -> List[Dict]:
    """
    Estratégia de chunking semântico por seção (heading-based).

    Regras de decisão (em ordem de prioridade):
      1. Tabela markdown → chunk atômico independente (nunca dividir)
      2. Seção com negação crítica → chunk atômico (preserva integridade semântica)
      3. Seção ≤ MAX_CHUNK_TOKENS → chunk único
      4. Seção > MAX_CHUNK_TOKENS → dividir por parágrafo com overlap de ~80 tokens

    Justificativa pelo tipo de pergunta (cf. análise 1.1, seção 4):
    - Perguntas dos atendentes mapeiam para seções específicas (ex: "prazo de
      devolução" → POL-001 §3.1; "carga perigosa" → POL-001 §3.2).
    - Chunking por seção maximiza a probabilidade de que a resposta completa
      esteja em um único chunk, reduzindo dependência de múltiplos chunks e
      mitigando o efeito lost-in-the-middle.
    - Chunking fixo de 512 tokens cortaria a tabela de multiplicadores da
      PROC-042 ao meio, separando cabeçalhos dos valores.
    """
    chunks = []
    doc_id = doc_metadata['doc_id']

    # Split no início de cada heading, mantendo o heading com seu conteúdo
    raw_sections = re.split(r'(?=\n#{1,4} )', '\n' + content)
    sections = [s.strip() for s in raw_sections if s.strip()]

    for section in sections:
        lines = section.split('\n')
        heading_text = ''

        # Extrai o texto do heading para o campo 'secao'
        for line in lines:
            if re.match(r'^#{1,4} ', line):
                heading_text = re.sub(r'^#{1,4} ', '', line).strip()
                break

        est_tokens = estimate_tokens(section)

        base_meta = {
            'doc_id': doc_id,
            'versao': doc_metadata['versao'],
            'data_emissao': doc_metadata['data_emissao'],
            'secao': heading_text,
        }

        # Regra 1: tabela → atômico com prefixo em linguagem natural
        if is_table(section):
            chunks.append({**base_meta, 'text': table_to_anchored_text(section, heading_text),
                           'tipo': 'tabela',
                           'chunk_id': f"{doc_id}_{len(chunks):03d}"})
            continue

        # Regra 2: negação crítica → atômico
        if has_critical_negation(section):
            chunks.append({**base_meta, 'text': section,
                           'tipo': 'negacao_critica',
                           'chunk_id': f"{doc_id}_{len(chunks):03d}"})
            continue

        # Regra 3: pequeno o suficiente → chunk único
        if est_tokens <= MAX_CHUNK_TOKENS:
            chunks.append({**base_meta, 'text': section,
                           'tipo': 'secao',
                           'chunk_id': f"{doc_id}_{len(chunks):03d}"})
            continue

        # Regra 4: fragmentar por parágrafo com overlap de ~80 tokens
        paragraphs = re.split(r'\n\n+', section)
        current = heading_text + '\n\n' if heading_text else ''
        overlap = ''

        for para in paragraphs:
            candidate = current + para
            if estimate_tokens(candidate) > MAX_CHUNK_TOKENS and current.strip():
                chunks.append({**base_meta, 'text': current.strip(),
                               'tipo': 'secao_fragmentada',
                               'chunk_id': f"{doc_id}_{len(chunks):03d}"})
                overlap = para          # último parágrafo como overlap
                current = overlap + '\n\n'
            else:
                current = candidate + '\n\n'

        if current.strip():
            chunks.append({**base_meta, 'text': current.strip(),
                           'tipo': 'secao' if not overlap else 'secao_fragmentada',
                           'chunk_id': f"{doc_id}_{len(chunks):03d}"})

    return chunks


# ── Pipeline principal ────────────────────────────────────────────────────────

def ingest_documents(docs_dir: str = DOCS_DIR) -> int:
    """
    Pipeline de ingestão completo:
      1. Lê arquivos .md de docs_dir
      2. Chunking semântico por seção com metadados
      3. Geração de embeddings em batch (multilingual sentence-transformer)
      4. Armazenamento no ChromaDB (persistente, cosine similarity)

    Retorna: total de chunks indexados.
    """
    print(f"[ingestão] Carregando modelo: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)

    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # Recria a coleção para ingestão limpa (idempotente)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    total_chunks = 0
    md_files = sorted(f for f in os.listdir(docs_dir) if f.endswith('.md'))

    for filename in md_files:
        filepath = os.path.join(docs_dir, filename)
        print(f"\n[ingestão] Processando: {filename}")

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        doc_meta = extract_doc_metadata(content, filename)
        chunks = chunk_by_section(content, doc_meta)

        print(f"  → {len(chunks)} chunks gerados")
        for c in chunks:
            est = estimate_tokens(c['text'])
            print(f"     [{c['tipo']:20s}] {c['secao'][:55]:<55} ({est:>4} tok est.)")

        # Batch embedding (eficiente: uma chamada por documento)
        texts = [c['text'] for c in chunks]
        embeddings = model.encode(texts, show_progress_bar=False).tolist()

        collection.add(
            ids=[c['chunk_id'] for c in chunks],
            embeddings=embeddings,
            documents=texts,
            metadatas=[
                {
                    'doc_id': c['doc_id'],
                    'versao': c['versao'],
                    'data_emissao': c['data_emissao'],
                    'secao': c['secao'],
                    'tipo': c['tipo'],
                }
                for c in chunks
            ],
        )

        total_chunks += len(chunks)

    print(f"\n[ingestão] Concluído. Total de chunks indexados: {total_chunks}")
    return total_chunks


if __name__ == "__main__":
    ingest_documents()
