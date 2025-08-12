import json, ast, numpy as np, pandas as pd
from ..extensions import supabase, logger

def _to_array(embedding_data):
    """Enhanced embedding parser with better debugging"""
    if embedding_data is None:
        print("DEBUG: embedding_data is None")
        return None
    
    try:
        # If it's already a numpy array
        if isinstance(embedding_data, np.ndarray):
            print(f"DEBUG: Already numpy array, shape: {embedding_data.shape}")
            return embedding_data
        
        # If it's a list
        if isinstance(embedding_data, list):
            arr = np.array(embedding_data)
            print(f"DEBUG: Converted from list, shape: {arr.shape}")
            return arr
        
        # If it's a string (most common case from Postgres)
        if isinstance(embedding_data, str):
            s = embedding_data.strip()
            print(f"DEBUG: Processing string of length {len(s)}, starts with: {s[:50]}")
            
            # Handle PostgreSQL array format: {1.0,2.0,3.0}
            if s.startswith('{') and s.endswith('}'):
                try:
                    # Remove braces and split by comma
                    nums_str = s[1:-1]
                    nums = [float(x.strip()) for x in nums_str.split(',') if x.strip()]
                    arr = np.array(nums)
                    print(f"DEBUG: Parsed PostgreSQL array format, shape: {arr.shape}")
                    return arr
                except Exception as e:
                    print(f"DEBUG: Failed to parse PostgreSQL format: {e}")
            
            # Handle JSON array format: [1.0,2.0,3.0]
            if s.startswith('[') and s.endswith(']'):
                try:
                    nums = [float(x.strip()) for x in s[1:-1].split(',') if x.strip()]
                    arr = np.array(nums)
                    print(f"DEBUG: Parsed JSON array format, shape: {arr.shape}")
                    return arr
                except Exception as e:
                    print(f"DEBUG: Failed to parse JSON format manually: {e}")
            
            # Try JSON parsing
            try:
                parsed = json.loads(s)
                arr = np.array(parsed)
                print(f"DEBUG: JSON parsed successfully, shape: {arr.shape}")
                return arr
            except Exception as e:
                print(f"DEBUG: JSON parse failed: {e}")
            
            # Try ast.literal_eval
            try:
                parsed = ast.literal_eval(s)
                arr = np.array(parsed)
                print(f"DEBUG: ast.literal_eval parsed successfully, shape: {arr.shape}")
                return arr
            except Exception as e:
                print(f"DEBUG: ast.literal_eval failed: {e}")
        
        # Try to convert directly
        arr = np.array(embedding_data)
        print(f"DEBUG: Direct conversion, shape: {arr.shape}")
        return arr
        
    except Exception as e:
        print(f"DEBUG: All parsing methods failed: {e}")
        return None

def fetch_text_df():
    try:
        if supabase is None:
            logger.error("Supabase client not initialized")
            return pd.DataFrame()
            
        res = supabase.table("text_embeddings").select("id, content, embedding::text").execute()
        df = pd.DataFrame(res.data or [])
        
        logger.info(f"Raw text_embeddings rows: {len(df)}")
        
        if df.empty:
            return df
            
        # Debug: Check embeddings before processing
        logger.info(f"Sample embedding type before processing: {type(df.iloc[0]['embedding']) if len(df) > 0 else 'No data'}")
        
        df["embedding"] = df["embedding"].apply(_to_array)
        
        # Count valid embeddings
        valid_before_shape_check = df["embedding"].notna().sum()
        logger.info(f"Valid embeddings after _to_array: {valid_before_shape_check}")
        
        df = df.dropna(subset=["embedding"])
        
        # Check embedding dimensions
        invalid_dims = []
        for idx, emb in enumerate(df["embedding"]):
            if hasattr(emb, "__len__") and len(emb) != 384:
                invalid_dims.append((idx, len(emb)))
        
        if invalid_dims:
            logger.warning(f"Found {len(invalid_dims)} embeddings with wrong dimensions: {invalid_dims}")
        
        df = df[df["embedding"].apply(lambda x: hasattr(x, "__len__") and len(x) == 384)]
        
        logger.info(f"Loaded {len(df)} text records with valid embeddings")
        return df
    except Exception as e:
        logger.error(f"text fetch error: {e}")
        return pd.DataFrame()

def fetch_qa_df():
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
        
        # Debug: Check a few sample rows
        if len(df) > 0:
            sample_row = df.iloc[0]
            logger.info(f"Sample QA row - ID: {sample_row.get('id')}, has embedding: {sample_row.get('embedding') is not None}")
            logger.info(f"Sample embedding type: {type(sample_row.get('embedding'))}")
            if sample_row.get('embedding'):
                emb_str = str(sample_row.get('embedding'))[:100]
                logger.info(f"Sample embedding start: {emb_str}")
        
        # Apply embedding conversion
        logger.info("Converting QA embeddings...")
        df["embedding"] = df["embedding"].apply(_to_array)
        
        # Count valid embeddings after conversion
        valid_embeddings = df["embedding"].notna().sum()
        logger.info(f"QA embeddings after conversion - Valid: {valid_embeddings}, Invalid: {len(df) - valid_embeddings}")
        
        # Check for None embeddings
        none_count = df["embedding"].isna().sum()
        if none_count > 0:
            logger.warning(f"Found {none_count} None embeddings in QA data")
            
        df = df.dropna(subset=["embedding"])
        
        # Check dimensions
        if len(df) > 0:
            sample_emb = df.iloc[0]["embedding"]
            logger.info(f"Sample QA embedding shape after conversion: {sample_emb.shape if hasattr(sample_emb, 'shape') else 'No shape'}")
        
        # Filter by dimension
        valid_dim_count = df["embedding"].apply(lambda x: hasattr(x, "__len__") and len(x) == 384).sum()
        logger.info(f"QA embeddings with correct dimensions (384): {valid_dim_count}")
        
        df = df[df["embedding"].apply(lambda x: hasattr(x, "__len__") and len(x) == 384)]
        
        logger.info(f"Final QA records with valid embeddings: {len(df)}")
        
        # Log some sample questions for verification
        if len(df) > 0:
            sample_questions = df["question"].head(3).tolist()
            logger.info(f"Sample questions: {sample_questions}")
            
        return df
    except Exception as e:
        logger.error(f"qa fetch error: {e}")
        logger.exception("Full QA fetch error traceback:")
        return pd.DataFrame()
