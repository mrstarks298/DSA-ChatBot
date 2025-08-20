import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from .embeddings import get_embedding_from_api  # import the API embedding function
from ..extensions import logger

def best_text_for_query(query: str, text_df):
    if not query or not query.strip():
        return {"error": "Empty query provided"}
        
    if text_df.empty:
        return {"error": "No text content available"}
    try:
        qemb = get_embedding_from_api(query)
        if qemb is None:
            return {"error": "Query embedding generation failed or dimension mismatch"}
        # Flatten possible nested shapes from HF router
        if hasattr(qemb, 'ndim') and qemb.ndim > 1:
            try:
                qemb = qemb.flatten()
            except Exception:
                return {"error": "Query embedding format invalid"}
        if len(qemb) != 384:
            return {"error": "Query embedding generation failed or dimension mismatch"}

        embs = np.vstack(text_df["embedding"].tolist())
        sims = cosine_similarity([qemb], embs)
        idx = sims.argmax()
        best_row = text_df.iloc[idx].to_dict()
        best_row["similarity"] = float(sims[0][idx])
        if hasattr(best_row.get("embedding"), "tolist"):
            best_row["embedding"] = best_row["embedding"].tolist()
        return best_row
    except Exception as e:
        logger.error(f"best_text_for_query error: {e}")
        return {"error": str(e)}

def top_qa_for_query(query: str, qa_df, k: int = 5):
    if not query or not query.strip():
        return []
        
    if qa_df.empty:
        return []
    try:
        qemb = get_embedding_from_api(query)
        if qemb is None:
            return []
        if hasattr(qemb, 'ndim') and qemb.ndim > 1:
            try:
                qemb = qemb.flatten()
            except Exception:
                return []
        if len(qemb) != 384:
            return []
        embs = np.vstack(qa_df["embedding"].tolist())
        sims = cosine_similarity([qemb], embs)[0]
        qa_df = qa_df.copy()
        qa_df["similarity"] = sims
        topk = qa_df.sort_values(by="similarity", ascending=False).head(k)
        recs = topk.to_dict(orient="records")
        for r in recs:
            if hasattr(r.get("embedding"), "tolist"):
                r["embedding"] = r["embedding"].tolist()
            if isinstance(r.get("similarity"), (float,)):
                r["similarity"] = float(r["similarity"])
        return recs
    except Exception as e:
        logger.error(f"top_qa_for_query error: {e}")
        return []
