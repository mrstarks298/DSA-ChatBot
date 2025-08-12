import json, re, requests
from flask import current_app
import logging
logger = logging.getLogger("dsa-mentor")

DSA_TOPICS = {
    'array': ['array', 'arrays', 'list', 'arraylist'],
    'linked_list': ['linked list', 'linkedlist', 'node', 'pointer'],
    'stack': ['stack', 'lifo', 'push', 'pop'],
    'queue': ['queue', 'fifo', 'enqueue', 'dequeue'],  # This should match "queue"!
    'tree': ['tree', 'binary tree', 'bst', 'binary search tree', 'avl', 'heap'],
    'graph': ['graph', 'vertex', 'edge', 'adjacency', 'dijkstra', 'bfs', 'dfs'],
    'sorting': ['sort', 'sorting', 'bubble sort', 'merge sort', 'quick sort', 'heap sort'],
    'searching': ['search', 'searching', 'binary search', 'linear search'],
    'dynamic_programming': ['dp', 'dynamic programming', 'memoization', 'tabulation'],
    'recursion': ['recursion', 'recursive', 'backtracking']
}

class QueryProcessor:
    @staticmethod
    def clean_and_normalize_query(query: str) -> str:
        if not query:
            return ""
        query = re.sub(r'\s+', ' ', query.strip())
        # FIXED: Escape the dash or put it at the end of the character class
        normalized = re.sub(r'[^\w\s?!.+\-]', '', query.lower())
        # Alternative fix: put dash at the end
        # normalized = re.sub(r'[^\w\s?!.+-]', '', query.lower())
        
        typo = {
            r'\balgorithem\b': 'algorithm',
            r'\balgoritm\b': 'algorithm',
            r'\blinklist\b': 'linked list',
            r'\bbst\b': 'binary search tree',
            r'\bgrapth\b': 'graph',
            r'\bsearch\b': 'searching',
            r'\bsort\b': 'sorting',
            r'\brecursiv\b': 'recursion'
        }
        for p, c in typo.items():
            normalized = re.sub(p, c, normalized)
        return normalized

    @staticmethod
    def extract_dsa_context(query: str) -> dict:
        normalized = query.lower()
        ctx = {
            'topics': [],
            'complexity_asked': False,
            'implementation_asked': False,
            'example_asked': False,
            'comparison_asked': False
        }
        for topic, kws in DSA_TOPICS.items():
            if any(k in normalized for k in kws):
                ctx['topics'].append(topic)
        if any(w in normalized for w in ['time complexity', 'space complexity', 'big o', 'complexity']):
            ctx['complexity_asked'] = True
        if any(w in normalized for w in ['implement', 'code', 'program', 'write', 'coding']):
            ctx['implementation_asked'] = True
        if any(w in normalized for w in ['example', 'sample', 'demo', 'show me']):
            ctx['example_asked'] = True
        if any(w in normalized for w in ['vs', 'versus', 'compare', 'difference', 'better']):
            ctx['comparison_asked'] = True
        return ctx





def classify_query_fallback(query: str) -> dict:
    """Enhanced fallback with better DSA detection"""
    q = query.lower().strip()
    
    # Greeting patterns
    if any(x in q for x in ['hi', 'hello', 'hey', 'greetings', 'good morning', 'good afternoon']):
        return {"type": "greeting", "confidence": 0.8, "is_dsa": False, "reasoning": "fallback pattern"}
    
    # Casual chat patterns
    if any(x in q for x in ['how are you', 'how r u', 'whats up', "what's up", "how's it going"]):
        return {"type": "casual_chat", "confidence": 0.8, "is_dsa": False, "reasoning": "fallback pattern"}
    
    # FIXED: Better DSA detection using our DSA_TOPICS
    processor = QueryProcessor()
    ctx = processor.extract_dsa_context(q)
    
    if ctx['topics']:  # If any DSA topics detected
        return {"type": "dsa_specific", "confidence": 0.9, "is_dsa": True, "reasoning": f"fallback detected: {ctx['topics']}"}
    
    # Specific DSA keywords that might not be in topics
    dsa_keywords = [
        'algorithm', 'complexity', 'binary search', 'merge sort', 'linked list', 
        'binary tree', 'graph traversal', 'data structure', 'big o', 'recursion',
        'dynamic programming', 'dp', 'leetcode', 'coding interview'
    ]
    if any(x in q for x in dsa_keywords):
        return {"type": "dsa_specific", "confidence": 0.8, "is_dsa": True, "reasoning": "fallback keyword match"}
    
    return {"type": "vague_question", "confidence": 0.5, "is_dsa": False, "reasoning": "fallback default"}

def classify_query_with_groq(user_query: str) -> dict:
    """Fixed Groq API call with proper response parsing"""
    api_key = current_app.config.get("GROQ_API_KEY")
    if not api_key or not user_query:
        logger.warning("No Groq API key or empty query, using fallback")
        return classify_query_fallback(user_query)
    
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {
                "role": "system", 
                "content": """You are an intent classifier for a DSA (Data Structures & Algorithms) chatbot. 

Classify user queries into these categories:
- "greeting": Hi, hello, good morning
- "casual_chat": How are you, what's up  
- "fun_chat": General friendly conversation
- "dsa_specific": Questions about algorithms, data structures, coding, complexity
- "vague_question": Unclear or very general questions

For DSA topics like "queue", "stack", "tree", "sorting", "binary search" etc., always use "dsa_specific".

Respond with ONLY valid JSON in this format:
{"type": "category", "confidence": 0.8, "is_dsa": true/false, "reasoning": "explanation"}"""
            },
            {"role": "user", "content": f"Classify this user query: '{user_query}'"}
        ],
        "temperature": 0.1,
        "max_tokens": 150
    }
    
    try:
        res = requests.post(current_app.config["GROQ_CHAT_API_URL"], headers=headers, json=payload, timeout=10)
        res.raise_for_status()
        
        response_json = res.json()
        logger.debug(f"Groq API response structure: {type(response_json.get('choices'))}")
        
        # FIXED: Handle both list and dict response formats
        choices = response_json.get("choices")
        if isinstance(choices, list) and len(choices) > 0:
            # Standard format: choices is a list
            content = choices[0].get("message", {}).get("content", "").strip()
        elif isinstance(choices, dict):
            # Alternative format: choices is a dict
            content = choices.get("message", {}).get("content", "").strip()
        else:
            raise ValueError(f"Unexpected choices format: {type(choices)}")
        
        # Clean up response
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        if content.startswith("json"):
            content = content[4:]
        
        content = content.strip()
        
        # Parse JSON response
        parsed = json.loads(content)
        
        # Validate required fields
        if not isinstance(parsed.get("type"), str):
            raise ValueError("Missing or invalid 'type' field")
        
        # Ensure is_dsa is boolean
        if "is_dsa" not in parsed:
            parsed["is_dsa"] = parsed.get("type") == "dsa_specific"
        
        logger.info(f"Groq classification successful: {parsed}")
        return parsed
        
    except json.JSONDecodeError as e:
        logger.error(f"Groq JSON parse error: {e}, content: {content}")
        return classify_query_fallback(user_query)
    except requests.RequestException as e:
        logger.error(f"Groq API request error: {e}")
        return classify_query_fallback(user_query)
    except Exception as e:
        logger.error(f"Groq classification error: {e}")
        return classify_query_fallback(user_query)

def generate_response_by_intent(classification: dict, original_query: str) -> dict | None:
    base = {"top_dsa": [], "video_suggestions": []}
    t = classification.get("type", "general")
    
    if t == "greeting":
        return {
            **base,
            "best_book": {
                "title": "Hello! 👋",
                "content": "Hi there! I'm DSA Mentor, your AI assistant for learning Data Structures and Algorithms.\n\nWhat topic would you like to explore today?"
            },
            "summary": "Ready to help with any DSA topic!"
        }
    
    if t == "casual_chat":
        return {
            **base,
            "best_book": {
                "title": "I'm doing great! 😊",
                "content": "Thanks for asking! I'm here and ready to help you learn DSA concepts.\n\nWhat would you like to work on?"
            },
            "summary": "I'm doing well and ready to help you learn!"
        }
    
    if t == "fun_chat":
        return {
            **base,
            "best_book": {
                "title": "That's nice! 🎉",
                "content": "I appreciate the friendly chat! While I love conversation, I'm most helpful with DSA topics.\n\nAsk me about any concept!"
            },
            "summary": "I'm here for both fun and learning!"
        }
    
    if t == "vague_question":
        if "dsa" in original_query.lower():
            return {
                **base,
                "best_book": {
                    "title": "What is DSA? 🎯",
                    "content": "DSA stands for Data Structures and Algorithms.\n\n- Data Structures organize data (arrays, trees, graphs)\n- Algorithms solve problems (sorting, searching)\n\nIt's essential for interviews and scalable systems."
                },
                "summary": "DSA = Data Structures + Algorithms."
            }
        return {
            **base,
            "best_book": {
                "title": "I'm here to help! 🤝",
                "content": "Please specify a topic: algorithms (sorting/searching), data structures (trees/graphs), problem solving, or complexity."
            },
            "summary": "Specify a DSA topic to continue."
        }
    
    # IMPORTANT: Return None for dsa_specific so it goes to the main DSA processing
    return None

def enhanced_summarize_with_context(text: str, ctx: dict, original_query: str) -> str | None:
    api_key = current_app.config.get("GROQ_API_KEY")
    if not api_key or not text:
        return None
    
    prompt = "You are a helpful DSA tutor. "
    if ctx.get('complexity_asked'):
        prompt += "Focus on time and space complexity analysis. "
    if ctx.get('implementation_asked'):
        prompt += "Include implementation details and code examples. "
    if ctx.get('example_asked'):
        prompt += "Provide clear examples and step-by-step explanations. "
    if ctx.get('comparison_asked'):
        prompt += "Compare different approaches and their trade-offs. "
    
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": prompt + "Summarize technical DSA content clearly in 3-4 sentences."},
            {"role": "user", "content": f"User asked: '{original_query}'\n\nContent to summarize:\n{text}\n\nProvide a focused summary."}
        ],
        "temperature": 0.3,
        "max_tokens": 200
    }
    
    try:
        res = requests.post(current_app.config["GROQ_CHAT_API_URL"], headers=headers, json=payload, timeout=15)
        res.raise_for_status()
        
        # FIXED: Same response parsing fix here
        response_json = res.json()
        choices = response_json.get("choices")
        if isinstance(choices, list) and len(choices) > 0:
            content = choices[0].get("message", {}).get("content", "")
        elif isinstance(choices, dict):
            content = choices.get("message", {}).get("content", "")
        else:
            raise ValueError(f"Unexpected choices format: {type(choices)}")
            
        return content
    except Exception as e:
        logger.error(f"Summarization error: {e}")
        return None