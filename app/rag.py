# =============================================================================
# NICE HTA PLATFORM
# Retrieval Augmented Generation (RAG)
# =============================================================================

import time
import logging
import shutil

from datetime import datetime
from collections import defaultdict

import pdfplumber
import chromadb

from langchain.docstore.document import Document

from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_community.embeddings import HuggingFaceBgeEmbeddings

from langchain_community.chat_models import ChatOllama

from langchain.prompts import PromptTemplate

from langchain.retrievers import ContextualCompressionRetriever

from langchain.retrievers.document_compressors import CrossEncoderReranker

from langchain_community.cross_encoders import HuggingFaceCrossEncoder

import repository
from langchain_chroma import Chroma

from paths import VECTORSTORE_FOLDER

# =============================================================================
# Repository
# =============================================================================

# Single shared vector database location (paths.py already creates this
# folder on import, so no extra mkdir() call is needed here).
VECTOR_FOLDER = VECTORSTORE_FOLDER

# =============================================================================
# Embedding Configuration
# =============================================================================

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

EMBEDDING_KWARGS = {"device": "cpu"}

ENCODE_KWARGS = {"normalize_embeddings": True}

RERANK_MODEL = "BAAI/bge-reranker-base"

LLM_MODEL = "llama3:latest"

# =============================================================================
# Chunk Configuration
# =============================================================================

CHUNK_SIZE = 1000

CHUNK_OVERLAP = 200

MINIMUM_CHUNK_LENGTH = 100

TOP_K = 10

RERANK_TOP_K = 8

# =============================================================================
# Logging
# =============================================================================

logging.basicConfig(level=logging.INFO, format="%(levelname)s : %(message)s")

logger = logging.getLogger(__name__)

# =============================================================================
# Module 2
# Load Selected PDF
# =============================================================================


def load_selected_pdf(document_row):
    """
    Load the user-selected PDF from the repository.

    Parameters
    ----------
    document_row : pandas.Series

    Returns
    -------
    tuple

        pdf_path

        metadata
    """

    pdf_path = repository.get_pdf_path(document_row)

    metadata = {
        "Document ID": document_row["Document ID"],
        "Document Name": document_row["Document Name"],
        "TA Number": document_row["TA Number"],
        "File Type": document_row["File Type"],
        "Local File": document_row["Local File"],
        "Loaded At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    logger.info(f"Selected document : {metadata['Document Name']}")

    return pdf_path, metadata


# =============================================================================
# Module 3
# Extract PDF Text
# =============================================================================


def extract_pdf_text(pdf_path, metadata, page_from=None, page_to=None):
    """
    Extract page-wise text from a PDF.

    Parameters
    ----------
    pdf_path : pathlib.Path

    metadata : dict

    Returns
    -------
    list

        One dictionary per page.
    """

    logger.info(f"Reading PDF : {pdf_path.name}")

    pages = []

    with pdfplumber.open(pdf_path) as pdf:

        total_pages = len(pdf.pages)

        logger.info(f"Total Pages : {total_pages}")

        if page_from is None:

            page_from = 1

        if page_to is None:

            page_to = len(pdf.pages)

        page_from = max(1, page_from)

        page_to = min(len(pdf.pages), page_to)

        logger.info(f"Processing Pages : {page_from}-{page_to}")

        for page_number in range(page_from, page_to + 1):

            page = pdf.pages[page_number - 1]

            text = page.extract_text()

            if text is None:

                text = ""

            text = text.strip()

            pages.append(
                {
                    "Document ID": metadata["Document ID"],
                    "Document Name": metadata["Document Name"],
                    "TA Number": metadata["TA Number"],
                    "Page": page_number,
                    "Text": text,
                }
            )

    logger.info(f"{len(pages)} page(s) extracted.")

    return pages


# =============================================================================
# Module 4
# Smart Recursive Chunking
# =============================================================================


def build_chunks(pages, metadata):
    """
    Convert extracted PDF text into LangChain Documents.

    Parameters
    ----------
    pages : list

    metadata : dict

    Returns
    -------
    list
    """

    logger.info("Creating document chunks...")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    documents = []

    chunk_counter = 1

    for page in pages:

        text = page["Text"].strip()

        if len(text) < MINIMUM_CHUNK_LENGTH:

            continue

        raw_chunks = splitter.split_text(text)

        total_chunks = len(raw_chunks)

        for chunk_number, chunk in enumerate(raw_chunks, start=1):

            chunk = chunk.strip()

            if len(chunk) < MINIMUM_CHUNK_LENGTH:

                continue

            documents.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "document_id": metadata["Document ID"],
                        "document_name": metadata["Document Name"],
                        "ta_number": metadata["TA Number"],
                        "page": page["Page"],
                        "chunk_id": chunk_counter,
                        "page_chunk": chunk_number,
                        "total_page_chunks": total_chunks,
                        "chunk_length": len(chunk),
                        "created_at": datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    },
                )
            )

            chunk_counter += 1

    logger.info(f"{len(documents)} chunk(s) created.")

    return documents


# =============================================================================
# Module 5
# Load BGE Embedding Model
# =============================================================================

_embedding_model = None


def load_embedding_model():
    """
    Load the BGE embedding model.

    Returns
    -------
    HuggingFaceBgeEmbeddings
    """

    global _embedding_model

    if _embedding_model is not None:

        return _embedding_model

    logger.info("Loading embedding model...")

    _embedding_model = HuggingFaceBgeEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs=EMBEDDING_KWARGS,
        encode_kwargs=ENCODE_KWARGS,
        query_instruction=(
            "Represent this question for retrieving relevant " "passages:"
        ),
        embed_instruction="Represent this document for retrieval:",
    )

    logger.info("Embedding model loaded.")

    return _embedding_model


# =============================================================================
# Module 6
# Build Chroma Vector Store
# =============================================================================

_vector_store = None


def build_vector_store(documents, metadata):
    """
    Build an in-memory Chroma vector store.
    """

    global _vector_store

    logger.info("Building Chroma vector store...")

    embedding_model = load_embedding_model()

    # ------------------------------------------------------------
    # Chroma Database
    #
    # Each document gets its own subfolder under the shared
    # VECTOR_FOLDER (vectorstore/) so different documents' indexes
    # never collide, and nothing is left behind in the OS temp
    # directory.
    #
    # Any existing collection for this document is cleared first,
    # so re-processing (e.g. with a different page range) fully
    # rebuilds the index instead of appending on top of the old
    # chunks and duplicating/stale-ing the retrieved context.
    # ------------------------------------------------------------

    collection_name = (
        metadata["Document ID"].replace(" ", "_").replace("/", "_")
    )

    document_directory = VECTOR_FOLDER / collection_name

    if document_directory.exists():

        logger.info(
            f"Clearing existing vector store for {collection_name}..."
        )

        shutil.rmtree(document_directory)

    document_directory.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(document_directory))

    start = time.time()

    _vector_store = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embedding_model,
    )

    _vector_store.add_documents(documents)

    elapsed = time.time() - start

    logger.info(f"{len(documents)} chunks indexed.")

    logger.info(f"Vector store created in {elapsed:.2f} seconds.")

    return _vector_store


# =============================================================================
# Module 7
# Build MMR Retriever
# =============================================================================

_retriever = None


def build_retriever(vector_store):
    """
    Build the Maximum Marginal Relevance (MMR) retriever.

    Parameters
    ----------
    vector_store : Chroma

    Returns
    -------
    Retriever
    """

    global _retriever

    logger.info("Building MMR retriever...")

    _retriever = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": TOP_K, "fetch_k": 30, "lambda_mult": 0.5},
    )

    logger.info("MMR retriever ready.")

    return _retriever


# =============================================================================
# Module 8
# BGE Cross Encoder Reranker
# =============================================================================


_reranker = None


def build_reranker(retriever):
    """
    Build the BGE Cross Encoder reranker.

    Parameters
    ----------
    retriever

        MMR Retriever.

    Returns
    -------
    ContextualCompressionRetriever
    """

    global _reranker

    logger.info("Loading BGE reranker...")

    cross_encoder = HuggingFaceCrossEncoder(model_name=RERANK_MODEL)

    compressor = CrossEncoderReranker(model=cross_encoder, top_n=RERANK_TOP_K)

    _reranker = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=retriever
    )

    logger.info("BGE reranker ready.")

    return _reranker


# =============================================================================
# Module 9
# NICE HTA Prompt Template
# =============================================================================

_prompt = None


def build_prompt():
    """
    Create the prompt template used by the RAG system.

    Returns
    -------
    PromptTemplate
    """

    global _prompt

    # -------------------------------------------------------------------------
    # Return cached prompt
    # -------------------------------------------------------------------------

    if _prompt is not None:

        return _prompt

    logger.info("Building prompt template...")

    template = """
You are an expert Health Technology Assessment (HTA) assistant
specialising in NICE Technology Appraisals.

Answer the user's question ONLY using the supplied context.

Rules
-----
1. Do not use outside knowledge.
2. If the answer is not available in the context, say:
   "The selected document does not contain sufficient information
   to answer this question."
3. Be concise but complete.
4. Preserve medical terminology exactly as written.
5. Use bullet points where appropriate.
6. Do not invent numbers, dates or recommendations.
7. If multiple pieces of evidence exist, combine them into one answer.

Context
-------
{context}

Question
--------
{question}

Answer
------
"""

    _prompt = PromptTemplate(
        input_variables=["context", "question"], template=template
    )

    return _prompt


# =============================================================================
# Module 10
# Load Ollama LLM
# =============================================================================

_llm = None


def load_llm():
    """
    Load the Ollama language model.

    Returns
    -------
    ChatOllama
    """

    global _llm

    if _llm is not None:

        return _llm

    logger.info("Loading Ollama model...")

    _llm = ChatOllama(
        model=LLM_MODEL,
        temperature=0,
        num_predict=6144,
        num_ctx=32768,
        repeat_penalty=1.1,
        top_p=0.9,
        seed=42,
    )

    logger.info("LLM ready.")

    return _llm


# =============================================================================
# Module 11
# Question Answering
# =============================================================================


def ask_question(question):
    """
    Execute the complete RAG pipeline.

    Parameters
    ----------
    question : str

    Returns
    -------
    dict
    """

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    if _reranker is None:

        raise RuntimeError("Please build the RAG pipeline first.")

    if _llm is None:

        load_llm()

    logger.info(f"Question : {question}")

    total_start = time.time()

    # -------------------------------------------------------------------------
    # Retrieve Context
    # -------------------------------------------------------------------------

    retrieval_start = time.time()

    documents = _reranker.invoke(question)

    retrieval_time = round(time.time() - retrieval_start, 2)

    if not documents:

        return {
            "question": question,
            "answer": "The selected document does not contain sufficient "
            "information to answer this question.",
            "document": {},
            "sources": [],
            "performance": {
                "retrieved_chunks": 0,
                "response_time": retrieval_time,
            },
        }

    # -------------------------------------------------------------------------
    # Build Context
    # -------------------------------------------------------------------------

    context = "\n\n------------------------------\n\n".join(
        doc.page_content for doc in documents
    )

    # -------------------------------------------------------------------------
    # Build Prompt
    # -------------------------------------------------------------------------

    prompt = build_prompt()

    final_prompt = prompt.format(context=context, question=question)

    # -------------------------------------------------------------------------
    # LLM
    # -------------------------------------------------------------------------

    llm_start = time.time()

    response = _llm.invoke(final_prompt)

    llm_time = round(time.time() - llm_start, 2)

    total_time = round(time.time() - total_start, 2)

    # -------------------------------------------------------------------------
    # Document Metadata
    # -------------------------------------------------------------------------

    first = documents[0].metadata

    document = {
        "document_id": first.get("document_id"),
        "document_name": first.get("document_name"),
        "ta_number": first.get("ta_number"),
    }

    # -------------------------------------------------------------------------
    # Source Summary
    # -------------------------------------------------------------------------

    page_chunks = defaultdict(list)

    for doc in documents:

        page = doc.metadata.get("page")

        chunk = doc.metadata.get("chunk_id")

        if chunk not in page_chunks[page]:

            page_chunks[page].append(chunk)

    sources = []

    for page in sorted(page_chunks):

        sources.append({"page": page, "chunks": sorted(page_chunks[page])})

    logger.info(f"Retrieved {len(documents)} chunks.")

    logger.info(f"Retrieval : {retrieval_time:.2f} sec")

    logger.info(f"LLM : {llm_time:.2f} sec")

    logger.info(f"Completed in {total_time:.2f} sec")

    # -------------------------------------------------------------------------
    # Final Output
    # -------------------------------------------------------------------------

    return {
        "question": question,
        "answer": response.content,
        "document": document,
        "sources": sources,
        "performance": {
            "retrieved_chunks": len(documents),
            "retrieval_time": retrieval_time,
            "llm_time": llm_time,
            "response_time": total_time,
        },
    }


# =============================================================================
# Module 12
# Build Complete RAG Pipeline
# =============================================================================


def build_rag(document_row, page_from=None, page_to=None):
    """
    Build the complete RAG pipeline for one selected document.

    Parameters
    ----------
    document_row : pandas.Series

        One row from the repository index.

    Returns
    -------
    dict

        Pipeline objects.
    """

    logger.info("Initialising RAG pipeline...")

    # -------------------------------------------------------------------------
    # Load Selected PDF
    # -------------------------------------------------------------------------

    pdf_path, metadata = load_selected_pdf(document_row)

    # -------------------------------------------------------------------------
    # Extract PDF Text
    # -------------------------------------------------------------------------

    pages = extract_pdf_text(pdf_path, metadata, page_from, page_to)

    # -------------------------------------------------------------------------
    # Create Chunks
    # -------------------------------------------------------------------------

    documents = build_chunks(pages, metadata)

    # -------------------------------------------------------------------------
    # Create Vector Store
    # -------------------------------------------------------------------------

    vector_store = build_vector_store(documents, metadata)

    # -------------------------------------------------------------------------
    # Create Retriever
    # -------------------------------------------------------------------------

    retriever = build_retriever(vector_store)

    # -------------------------------------------------------------------------
    # Create BGE Reranker
    # -------------------------------------------------------------------------

    build_reranker(retriever)

    # -------------------------------------------------------------------------
    # Load LLM
    # -------------------------------------------------------------------------

    load_llm()

    logger.info("RAG pipeline ready.")

    return {
        "metadata": metadata,
        "documents": documents,
        "vector_store": vector_store,
        "retriever": retriever,
        "reranker": _reranker,
        "llm": _llm,
    }
