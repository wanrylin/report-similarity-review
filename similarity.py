"""TF-IDF and optional semantic scores for pairs in one batch of reports."""
from itertools import combinations

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def compute_tfidf_similarity(texts):
    """Compare English word unigrams and bigrams by TF-IDF cosine similarity."""
    vectorizer = TfidfVectorizer(
        stop_words="english", ngram_range=(1, 2), strip_accents="unicode",
    )
    vectors = vectorizer.fit_transform(texts)
    return np.clip(cosine_similarity(vectors), 0, 1)


def compute_semantic_similarity(texts):
    """Compare leading excerpts with the optional local sentence model."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Install requirements-semantic.txt to use semantic comparison."
        ) from exc

    try:
        model = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception as exc:
        raise RuntimeError(
            "Could not load all-MiniLM-L6-v2. Download the model on first use "
            "or run with --method tfidf."
        ) from exc
    embeddings = model.encode(
        [text[:4000] for text in texts],
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.clip(embeddings @ embeddings.T, -1, 1)


def compute_similarity_matrix(documents, method="tfidf"):
    """Return the selected score matrices and every unordered pair, ranked."""
    texts = [document["text"] for document in documents]
    filenames = [document["filename"] for document in documents]
    matrices = {}
    if method in ("tfidf", "both"):
        matrices["tfidf"] = compute_tfidf_similarity(texts)
    if method in ("semantic", "both"):
        matrices["semantic"] = compute_semantic_similarity(texts)
    if not matrices:
        raise ValueError(f"Unknown comparison method: {method}")

    combined = np.mean(list(matrices.values()), axis=0)
    pairs = []
    for i, j in combinations(range(len(documents)), 2):
        pairs.append({
            "i": i,
            "j": j,
            "file_a": filenames[i],
            "file_b": filenames[j],
            "combined": float(combined[i, j]),
            **{name: float(scores[i, j]) for name, scores in matrices.items()},
        })
    pairs.sort(key=lambda pair: pair["combined"], reverse=True)
    return {
        **matrices, "combined": combined, "filenames": filenames,
        "n": len(documents), "pairs": pairs,
    }
