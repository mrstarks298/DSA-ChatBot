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
            'comparison_asked': False,
            'question_generation_asked': False  # NEW: Added question generation detection
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
        # NEW: Detect question generation requests
        if any(w in normalized for w in ['generate question', 'create question', 'ask question', 'practice question', 'quiz', 'test me', 'give me question']):
            ctx['question_generation_asked'] = True
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
    
    # NEW: Question generation patterns
    if any(x in q for x in ['generate question', 'create question', 'practice question', 'quiz me', 'test me', 'give me question']):
        return {"type": "question_generation", "confidence": 0.9, "is_dsa": True, "reasoning": "question generation request"}
    
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
- "question_generation": Requests to generate/create practice questions or quizzes
- "vague_question": Unclear or very general questions

For DSA topics like "queue", "stack", "tree", "sorting", "binary search" etc., always use "dsa_specific".
For requests like "generate questions", "create quiz", "practice problems", use "question_generation".

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
            parsed["is_dsa"] = parsed.get("type") in ["dsa_specific", "question_generation"]
        
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

# NEW: Question generation function using Groq API
def generate_dsa_questions_with_groq(topic: str, difficulty: str = 'medium', count: int = 3) -> dict:
    """Generate DSA questions with answers using Groq API instead of embeddings"""
    api_key = current_app.config.get("GROQ_API_KEY")
    if not api_key:
        logger.warning("No Groq API key for question generation")
        return {"questions": [], "error": "API key not available"}
    
    # Map common topics to more specific ones
    topic_mapping = {
        'array': 'Arrays and Array Manipulation',
        'linked_list': 'Linked Lists',
        'stack': 'Stack Data Structure', 
        'queue': 'Queue Data Structure',
        'tree': 'Binary Trees and Tree Traversal',
        'graph': 'Graph Algorithms and Traversal',
        'sorting': 'Sorting Algorithms',
        'searching': 'Searching Algorithms',
        'dynamic_programming': 'Dynamic Programming',
        'recursion': 'Recursion and Backtracking'
    }
    
    formatted_topic = topic_mapping.get(topic.lower(), topic)
    
    system_prompt = f"""You are an expert DSA instructor creating practice questions. 
Generate {count} {difficulty} level questions about {formatted_topic}.

For each question, provide:
1. Clear problem statement
2. Input/output examples
3. Detailed solution explanation
4. Code implementation (Python preferred)
5. Time/space complexity analysis

Format as JSON:
{{
  "questions": [
    {{
      "id": 1,
      "question": "Problem statement here",
      "examples": ["Example 1: Input -> Output", "Example 2: Input -> Output"],
      "solution_explanation": "Step by step explanation",
      "code": "def solution():\\n    # Python implementation here",
      "time_complexity": "O(n)",
      "space_complexity": "O(1)",
      "difficulty": "{difficulty}",
      "topic": "{formatted_topic}"
    }}
  ]
}}"""

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate {count} {difficulty} questions about {formatted_topic} with complete solutions"}
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        res = requests.post(current_app.config["GROQ_CHAT_API_URL"], headers=headers, json=payload, timeout=20)
        res.raise_for_status()
        
        response_json = res.json()
        choices = response_json.get("choices")
        if isinstance(choices, list) and len(choices) > 0:
            content = choices[0].get("message", {}).get("content", "")
        elif isinstance(choices, dict):
            content = choices.get("message", {}).get("content", "")
        else:
            raise ValueError(f"Unexpected choices format: {type(choices)}")
        
        # Clean up JSON response
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
        
        try:
            questions_data = json.loads(content)
            logger.info(f"Generated {len(questions_data.get('questions', []))} questions for {topic}")
            return questions_data
        except json.JSONDecodeError:
            # Fallback: create structured response from text
            return _create_fallback_questions(content, topic, difficulty)
            
    except Exception as e:
        logger.error(f"Question generation error: {e}")
        return _generate_fallback_questions(topic, difficulty, count)

# NEW: Helper function for fallback questions
def _create_fallback_questions(content: str, topic: str, difficulty: str) -> dict:
    """Create structured questions from unstructured content"""
    return {
        "questions": [{
            "id": 1,
            "question": f"Practice {topic} problem ({difficulty} level)",
            "examples": ["Check the detailed explanation below"],
            "solution_explanation": content,
            "code": "# Implementation details provided in explanation above",
            "time_complexity": "Varies",
            "space_complexity": "Varies", 
            "difficulty": difficulty,
            "topic": topic
        }]
    }

# NEW: Helper function for basic fallback questions
def _generate_fallback_questions(topic: str, difficulty: str, count: int) -> dict:
    """Generate basic questions when API fails"""
    basic_questions = {
        'array': {
            'question': 'Find the maximum element in an array',
            'solution': 'Iterate through array keeping track of maximum value',
            'complexity': 'O(n) time, O(1) space'
        },
        'linked_list': {
            'question': 'Reverse a linked list',
            'solution': 'Use iterative approach with prev, curr, next pointers',
            'complexity': 'O(n) time, O(1) space'
        },
        'tree': {
            'question': 'Find height of binary tree',
            'solution': 'Use recursive approach: max(left_height, right_height) + 1',
            'complexity': 'O(n) time, O(h) space where h is height'
        },
        'sorting': {
            'question': 'Implement merge sort algorithm',
            'solution': 'Divide array into halves, recursively sort, then merge',
            'complexity': 'O(n log n) time, O(n) space'
        },
        'graph': {
            'question': 'Implement breadth-first search (BFS)',
            'solution': 'Use queue to visit nodes level by level',
            'complexity': 'O(V + E) time, O(V) space'
        }
    }
    
    default = basic_questions.get(topic, {
        'question': f'Solve a {difficulty} {topic} problem',
        'solution': 'Think about the problem step by step',
        'complexity': 'Analyze time and space requirements'
    })
    
    return {
        "questions": [{
            "id": 1,
            "question": default['question'],
            "examples": ["Example will be provided with solution"],
            "solution_explanation": default['solution'],
            "code": "# Code implementation here",
            "time_complexity": default['complexity'].split(',')[0] if ',' in default['complexity'] else 'O(n)',
            "space_complexity": default['complexity'].split(',')[1].strip() if ',' in default['complexity'] else 'O(1)',
            "difficulty": difficulty,
            "topic": topic
        }]
    }

# NEW: Direct DSA question answering using Groq
def answer_dsa_question_with_groq(question: str, context: str = "") -> dict:
    """Answer DSA questions directly using Groq API"""
    api_key = current_app.config.get("GROQ_API_KEY")
    if not api_key:
        logger.warning("No Groq API key for question answering")
        return {"answer": "API key not available", "error": True}
    
    system_prompt = """You are an expert DSA tutor. Provide comprehensive answers to DSA questions.

Your response should include:
1. Clear explanation of the concept/algorithm
2. Step-by-step approach
3. Code implementation (Python preferred)
4. Time and space complexity analysis
5. Real-world applications or interview tips

Be detailed but concise. Focus on helping the student understand the concept thoroughly."""

    user_prompt = f"Question: {question}"
    if context:
        user_prompt += f"\n\nAdditional Context: {context}"

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 1500
    }
    
    try:
        res = requests.post(current_app.config["GROQ_CHAT_API_URL"], headers=headers, json=payload, timeout=15)
        res.raise_for_status()
        
        response_json = res.json()
        choices = response_json.get("choices")
        if isinstance(choices, list) and len(choices) > 0:
            content = choices[0].get("message", {}).get("content", "")
        elif isinstance(choices, dict):
            content = choices.get("message", {}).get("content", "")
        else:
            raise ValueError(f"Unexpected choices format: {type(choices)}")
        
        return {
            "answer": content,
            "source": "groq_api",
            "confidence": 0.9,
            "error": False
        }
        
    except Exception as e:
        logger.error(f"Question answering error: {e}")
        return {
            "answer": "I apologize, but I'm having trouble processing your question right now. Please try rephrasing or ask about a specific DSA concept.",
            "source": "fallback",
            "confidence": 0.3,
            "error": True
        }

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
    
    # NEW: Handle question generation requests
    if t == "question_generation":
        # Extract topic and difficulty from query
        processor = QueryProcessor()
        ctx = processor.extract_dsa_context(original_query)
        
        # Determine topic
        topic = ctx['topics'][0] if ctx['topics'] else 'general'
        
        # Determine difficulty from query
        difficulty = 'medium'  # default
        query_lower = original_query.lower()
        if any(word in query_lower for word in ['easy', 'beginner', 'simple', 'basic']):
            difficulty = 'easy'
        elif any(word in query_lower for word in ['hard', 'difficult', 'advanced', 'expert', 'challenging']):
            difficulty = 'hard'
        
        # Generate questions using Groq API
        questions_data = generate_dsa_questions_with_groq(topic, difficulty, 2)
        
        if questions_data.get("error"):
            return {
                **base,
                "best_book": {
                    "title": "Question Generation 🤔",
                    "content": "I'm having trouble generating questions right now. Please specify a topic (arrays, trees, graphs, etc.) and I'll help you practice!\n\nExample: 'Generate easy array questions'"
                },
                "summary": "Specify a DSA topic for practice questions."
            }
        
        # Format the response with generated questions
        questions = questions_data.get("questions", [])
        if questions:
            content = f"Here are some {difficulty} practice questions about {topic}:\n\n"
            for i, q in enumerate(questions[:2], 1):
                content += f"**Question {i}:** {q.get('question', 'N/A')}\n\n"
                if q.get('examples'):
                    content += f"**Examples:** {', '.join(q['examples'])}\n\n"
                content += f"**Solution:** {q.get('solution_explanation', 'See code below')}\n\n"
                if q.get('code'):
                    content += f"**Code:**\n```python\n{q['code']}\n```\n\n"
                content += f"**Complexity:** {q.get('time_complexity', 'N/A')} time, {q.get('space_complexity', 'N/A')} space\n\n"
                content += "---\n\n"
        else:
            content = f"I can help you practice {topic} problems. What specific aspect would you like to focus on?"
        
        return {
            **base,
            "best_book": {
                "title": f"{difficulty.title()} {topic.title()} Practice Questions 📝",
                "content": content
            },
            "summary": f"Generated {len(questions)} practice questions for {topic}"
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
                "content": "Please specify a topic: algorithms (sorting/searching), data structures (trees/graphs), problem solving, or complexity.\n\nYou can also ask me to generate practice questions!"
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
    if ctx.get('question_generation_asked'):  # NEW: Handle question generation context
        prompt += "Focus on practice questions and learning exercises. "
    
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
