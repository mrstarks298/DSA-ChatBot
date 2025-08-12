import json
import ast
import numpy as np
import pandas as pd
import requests
import os
from ..extensions import supabase, logger

HF_API_URL = "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction"
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

headers = {"Authorization": f"Bearer {HF_API_TOKEN}"} if HF_API_TOKEN else {}

def get_embedding_from_api(text: str):
    """Get embedding vector from Hugging Face Inference API."""
    if not HF_API_TOKEN:
        logger.error("HF_API_TOKEN not set in environment.")
        return None
    payload = {"inputs": text}
    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        embedding = response.json()
        return np.array(embedding)
    except Exception as e:
        logger.error(f"Error getting embedding from API: {e}")
        return None

def _to_array(embedding_data):
    """Parse embeddings stored in different formats into numpy arrays with debug."""
    if embedding_data is None:
        logger.debug("embedding_data is None")
        return None
    
    try:
        if isinstance(embedding_data, np.ndarray):
            logger.debug(f"Already numpy array, shape: {embedding_data.shape}")
            return embedding_data
        
        if isinstance(embedding_data, list):
            arr = np.array(embedding_data)
            logger.debug(f"Converted from list, shape: {arr.shape}")
            return arr
        
        if isinstance(embedding_data, str):
            s = embedding_data.strip()
            logger.debug(f"Processing string of length {len(s)}")
            
            if s.startswith('{') and s.endswith('}'):
                try:
                    nums_str = s[1:-1]
                    nums = [float(x.strip()) for x in nums_str.split(',') if x.strip()]
                    arr = np.array(nums)
                    logger.debug(f"Parsed PostgreSQL array format, shape: {arr.shape}")
                    return arr
                except Exception as e:
                    logger.debug(f"Failed to parse PostgreSQL format: {e}")
            
            if s.startswith('[') and s.endswith(']'):
                try:
                    nums = [float(x.strip()) for x in s[1:-1].split(',') if x.strip()]
                    arr = np.array(nums)
                    logger.debug(f"Parsed JSON array format, shape: {arr.shape}")
                    return arr
                except Exception as e:
                    logger.debug(f"Failed to parse JSON format manually: {e}")
            
            try:
                parsed = json.loads(s)
                arr = np.array(parsed)
                logger.debug(f"JSON parsed successfully, shape: {arr.shape}")
                return arr
            except Exception as e:
                logger.debug(f"JSON parse failed: {e}")
            
            try:
                parsed = ast.literal_eval(s)
                arr = np.array(parsed)
                logger.debug(f"ast.literal_eval parsed successfully, shape: {arr.shape}")
                return arr
            except Exception as e:
                logger.debug(f"ast.literal_eval failed: {e}")
        
        arr = np.array(embedding_data)
        logger.debug(f"Direct conversion, shape: {arr.shape}")
        return arr
    
    except Exception as e:
        logger.error(f"All parsing methods failed: {e}")
        return None

def fetch_text_df():
    """Fetch text embeddings table from Supabase, parse embeddings, and validate."""
    try:
        if supabase is None:
            logger.error("Supabase client not initialized")
            return pd.DataFrame()
        
        res = supabase.table("text_embeddings").select("id, content, embedding::text").execute()
        df = pd.DataFrame(res.data or [])
        logger.info(f"Raw text_embeddings rows: {len(df)}")
        
        if df.empty:
            return df
        
        df["embedding"] = df["embedding"].apply(_to_array)
        
        df = df.dropna(subset=["embedding"])
        
        df = df[df["embedding"].apply(lambda x: hasattr(x, "__len__") and len(x) == 384)]
        
        logger.info(f"Loaded {len(df)} text records with valid embeddings")
        return df
    except Exception as e:
        logger.error(f"text fetch error: {e}")
        return pd.DataFrame()

def fetch_qa_df():
    """Fetch QA resources from Supabase, parse embeddings, and validate."""
    try:
        if supabase is None:
            logger.error("Supabase client not initialized")
            return pd.DataFrame()
        
        res = supabase.table("qa1_resources").select("id, section, question, article_link, practice_link, embedding::text").execute()
        df = pd.DataFrame(res.data or [])
        logger.info(f"Raw qa1_resources rows: {len(df)}")
        
        if df.empty:
            logger.warning("qa1_resources table is empty!")
            return df
        
        df["embedding"] = df["embedding"].apply(_to_array)
        
        df = df.dropna(subset=["embedding"])
        
        df = df[df["embedding"].apply(lambda x: hasattr(x, "__len__") and len(x) == 384)]
        
        logger.info(f"Final QA records with valid embeddings: {len(df)}")
        return df
    except Exception as e:
        logger.error(f"qa fetch error: {e}")
        return pd.DataFrame()
