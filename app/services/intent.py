import json, re, requests
from flask import current_app
import logging
logger = logging.getLogger("dsa-mentor")

DSA_TOPICS = {
    'array': ['array', 'arrays', 'list', 'arraylist'],
    'linked_list': ['linked list', 'linkedlist', 'node', 'pointer'],
    'stack': ['stack', 'lifo', 'push', 'pop'],
    'queue': ['queue', 'fifo', 'enqueue', 'dequeue'],
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
        if not query or not isinstance(query, str):
            return ""
        query = re.sub(r'\s+', ' ', query.strip())
        normalized = re.sub(r'[^\w\s?!.+\-]', '', query.lower())
        
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
        if not query or not isinstance(query, str):
            return {
                'topics': [],
                'complexity_asked': False,
                'implementation_asked': False,
                'example_asked': False,
                'comparison_asked': False,
                'question_generation_asked': False
            }
            
        normalized = query.lower()
        ctx = {
            'topics': [],
            'complexity_asked': False,
            'implementation_asked': False,
            'example_asked': False,
            'comparison_asked': False,
            'question_generation_asked': False
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
        if any(w in normalized for w in ['generate question', 'create question', 'ask question', 'practice question', 'quiz', 'test me', 'give me question', 'generate problem', 'practice problem']):
            ctx['question_generation_asked'] = True
        return ctx

def classify_query_fallback(query: str) -> dict:
    """Enhanced fallback with better DSA detection"""
    if not query or not isinstance(query, str):
        return {"type": "vague_question", "confidence": 0.5, "is_dsa": False, "reasoning": "fallback empty query"}
        
    q = query.lower().strip()
    
    # Greeting patterns
    if any(x in q for x in ['hi', 'hello', 'hey', 'greetings', 'good morning', 'good afternoon']):
        return {"type": "greeting", "confidence": 0.8, "is_dsa": False, "reasoning": "fallback pattern"}
    
    # Casual chat patterns
    if any(x in q for x in ['how are you', 'how r u', 'whats up', "what's up", "how's it going"]):
        return {"type": "casual_chat", "confidence": 0.8, "is_dsa": False, "reasoning": "fallback pattern"}
    
    # Question generation patterns (ENHANCED)
    if any(x in q for x in ['generate question', 'create question', 'practice question', 'quiz me', 'test me', 'give me question', 'generate problem', 'practice problem', 'give me practice']):
        return {"type": "question_generation", "confidence": 0.9, "is_dsa": True, "reasoning": "question generation request"}
    
    # Better DSA detection using our DSA_TOPICS
    processor = QueryProcessor()
    ctx = processor.extract_dsa_context(q)
    
    if ctx['topics']:
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
    if not user_query or not user_query.strip():
        logger.warning("Empty query provided")
        return classify_query_fallback("")
        
    api_key = current_app.config.get("GROQ_API_KEY")
    if not api_key:
        logger.warning("No Groq API key, using fallback")
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
- "question_generation": Requests to generate/create practice questions, problems, or quizzes
- "vague_question": Unclear or very general questions

For DSA topics like "queue", "stack", "tree", "sorting", "binary search" etc., always use "dsa_specific".
For requests like "generate questions", "create quiz", "practice problems", "give me problems", use "question_generation".

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
        
        choices = response_json.get("choices")
        if isinstance(choices, list) and len(choices) > 0:
            content = choices[0].get("message", {}).get("content", "").strip()
        elif isinstance(choices, dict):
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
# Add this debugging code to your generate_dsa_questions_with_groq function

def generate_dsa_questions_with_groq(topic: str, difficulty: str = 'medium', count: int = 3) -> dict:
    """Generate DSA questions with answers using Groq API"""
    if not topic or not topic.strip():
        logger.warning("Empty topic provided for question generation")
        return {"questions": [], "error": "Topic is required"}
        
    if count <= 0 or count > 10:
        logger.warning(f"Invalid count parameter: {count}")
        count = 3
        
    api_key = current_app.config.get("GROQ_API_KEY")
    if not api_key:
        logger.warning("No Groq API key for question generation")
        return {"questions": [], "error": "API key not available"}
    
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
    
    # SIMPLIFIED prompt for better Groq response
    system_prompt = f"""Generate {count} {difficulty} level coding questions about {formatted_topic}.

For each question, provide:
- Problem statement
- Example input/output  
- Solution explanation
- Python code
- Time/space complexity

Return as JSON:
{{
  "questions": [
    {{
      "question": "problem here",
      "example": "Input: [1,2] Output: 3", 
      "solution": "explanation here",
      "code": "def solve(): pass",
      "time": "O(n)",
      "space": "O(1)"
    }}
  ]
}}"""

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate {count} {difficulty} {formatted_topic} questions as JSON"}
        ],
        "temperature": 0.5,  # Reduced temperature
        "max_tokens": 1500   # Reduced tokens
    }
    
    try:
        logger.info(f"🚀 Calling Groq API for {topic} questions...")
        res = requests.post(current_app.config["GROQ_CHAT_API_URL"], headers=headers, json=payload, timeout=20)
        res.raise_for_status()
        
        response_json = res.json()
        
        # DEBUG: Log the raw response
        logger.info(f"📥 Groq raw response: {response_json}")
        
        choices = response_json.get("choices")
        if isinstance(choices, list) and len(choices) > 0:
            content = choices[0].get("message", {}).get("content", "")
        elif isinstance(choices, dict):
            content = choices.get("message", {}).get("content", "")
        else:
            logger.error(f"❌ Unexpected choices format: {type(choices)}")
            return _generate_fallback_questions(topic, difficulty, count)
        
        # DEBUG: Log the content before parsing
        logger.info(f"📄 Groq content before cleaning: {repr(content[:500])}")
        
        # Clean up JSON response
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        # DEBUG: Log cleaned content
        logger.info(f"🧹 Cleaned content: {repr(content[:500])}")
        
        try:
            questions_data = json.loads(content)
            
            # DEBUG: Log parsed data
            logger.info(f"✅ Successfully parsed questions: {len(questions_data.get('questions', []))} questions")
            logger.info(f"📋 Question titles: {[q.get('question', 'No title')[:50] for q in questions_data.get('questions', [])]}")
            
            return questions_data
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            logger.error(f"🔍 Failed content: {repr(content)}")
            
            # Try to extract questions from non-JSON content
            return _extract_questions_from_text(content, topic, difficulty)
            
    except requests.RequestException as e:
        logger.error(f"❌ Groq API request error: {e}")
        return _generate_fallback_questions(topic, difficulty, count)
    except Exception as e:
        logger.error(f"❌ Unexpected error in question generation: {e}")
        return _generate_fallback_questions(topic, difficulty, count)

def _extract_questions_from_text(content: str, topic: str, difficulty: str) -> dict:
    """Extract questions from non-JSON Groq response"""
    if not content or not isinstance(content, str):
        logger.warning("Empty or invalid content provided for text extraction")
        return {"questions": []}
        
    logger.info("🔧 Attempting to extract questions from text response...")
    
    # Simple extraction - look for common patterns
    questions = []
    
    # Split by question numbers or common separators
    parts = re.split(r'\n(?=\*\*Question|\d+\.|\#)', content, flags=re.MULTILINE)
    
    for i, part in enumerate(parts[:3], 1):  # Limit to 3 questions
        if len(part.strip()) > 50:  # Only process substantial content
            questions.append({
                "id": i,
                "question": f"Generated {topic} problem #{i}",
                "example": "See detailed explanation below",
                "solution": part.strip()[:500] + "..." if len(part) > 500 else part.strip(),
                "code": "# See solution explanation above for implementation details",
                "time": "O(n)",
                "space": "O(1)"
            })
    
    if not questions:
        # If extraction fails, create one question with all content
        questions = [{
            "id": 1,
            "question": f"{difficulty.title()} {topic.replace('_', ' ').title()} Problem",
            "example": "Multiple examples provided in solution",
            "solution": content[:1000] + "..." if len(content) > 1000 else content,
            "code": "# Implementation details provided in the explanation above",
            "time": "Varies based on approach",
            "space": "Varies based on approach"
        }]
    
    logger.info(f"🎯 Extracted {len(questions)} questions from text")
    return {"questions": questions}

def _generate_fallback_questions(topic: str, difficulty: str, count: int) -> dict:
    """This should ONLY be called when Groq completely fails"""
    logger.warning(f"⚠️ Using fallback questions for {topic} - Groq API failed!")
    
    # Your existing fallback code here...
    # (Keep your existing fallback implementation)
    
    return {
        "questions": [{
            "id": 1,
            "question": f"FALLBACK: {topic} problem (Groq API failed)",
            "example": "This is a fallback question",
            "solution": "The Groq API failed to generate questions. Please try again.",
            "code": "# Fallback code",
            "time": "O(n)",
            "space": "O(1)"
        }]
    }



def _generate_fallback_questions(topic: str, difficulty: str, count: int) -> dict:
    """Generate basic questions when API fails - ENHANCED for better display"""
    if not topic or not isinstance(topic, str):
        topic = "general"
        
    if not difficulty or not isinstance(difficulty, str):
        difficulty = "medium"
        
    if not isinstance(count, int) or count <= 0:
        count = 1
        
    basic_questions = {
        'array': {
            'question': 'Find the maximum element in an array',
            'examples': 'Input: [3, 7, 1, 9, 2] Output: 9',
            'solution': 'Iterate through the array keeping track of the maximum value seen so far. Start with the first element as max, then compare each subsequent element.',
            'code': 'def find_max(arr):\n    if not arr:\n        return None\n    max_val = arr[0]\n    for num in arr[1:]:\n        if num > max_val:\n            max_val = num\n    return max_val',
            'time_complexity': 'O(n)',
            'space_complexity': 'O(1)'
        },
        'linked_list': {
            'question': 'Reverse a singly linked list',
            'examples': 'Input: 1->2->3->4->5 Output: 5->4->3->2->1',
            'solution': 'Use three pointers: prev, curr, and next. Iterate through the list, reversing the direction of each link.',
            'code': 'def reverse_list(head):\n    prev = None\n    curr = head\n    while curr:\n        next_node = curr.next\n        curr.next = prev\n        prev = curr\n        curr = next_node\n    return prev',
            'time_complexity': 'O(n)',
            'space_complexity': 'O(1)'
        },
        'tree': {
            'question': 'Find the height of a binary tree',
            'examples': 'Input: Tree with root->left->right, root->right Output: 2',
            'solution': 'Use recursion. Height = max(left_subtree_height, right_subtree_height) + 1. Base case: empty tree has height 0.',
            'code': 'def tree_height(root):\n    if not root:\n        return 0\n    left_height = tree_height(root.left)\n    right_height = tree_height(root.right)\n    return max(left_height, right_height) + 1',
            'time_complexity': 'O(n)',
            'space_complexity': 'O(h)'
        },
        'graph': {
            'question': 'Implement breadth-first search (BFS) traversal',
            'examples': 'Input: Graph with vertices 0,1,2,3 and edges [(0,1),(0,2),(1,3)] Output: [0,1,2,3]',
            'solution': 'Use a queue to visit nodes level by level. Mark visited nodes to avoid cycles.',
            'code': 'from collections import deque\n\ndef bfs(graph, start):\n    visited = set()\n    queue = deque([start])\n    result = []\n    \n    while queue:\n        node = queue.popleft()\n        if node not in visited:\n            visited.add(node)\n            result.append(node)\n            queue.extend(graph[node])\n    return result',
            'time_complexity': 'O(V + E)',
            'space_complexity': 'O(V)'
        },
        'sorting': {
            'question': 'Implement merge sort algorithm',
            'examples': 'Input: [64, 34, 25, 12, 22, 11, 90] Output: [11, 12, 22, 25, 34, 64, 90]',
            'solution': 'Divide array into halves, recursively sort each half, then merge the sorted halves.',
            'code': 'def merge_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    \n    mid = len(arr) // 2\n    left = merge_sort(arr[:mid])\n    right = merge_sort(arr[mid:])\n    \n    return merge(left, right)\n\ndef merge(left, right):\n    result = []\n    i = j = 0\n    while i < len(left) and j < len(right):\n        if left[i] <= right[j]:\n            result.append(left[i])\n            i += 1\n        else:\n            result.append(right[j])\n            j += 1\n    result.extend(left[i:])\n    result.extend(right[j:])\n    return result',
            'time_complexity': 'O(n log n)',
            'space_complexity': 'O(n)'
        }
    }
    
    default_data = basic_questions.get(topic, {
        'question': f'Solve a {difficulty} level {topic} problem',
        'examples': 'Example will be provided based on the specific problem',
        'solution': f'Apply {topic} concepts step by step to solve the problem efficiently',
        'code': f'# {topic.title()} implementation\n# Code will depend on the specific problem',
        'time_complexity': 'O(n)',
        'space_complexity': 'O(1)'
    })
    
    return {
        "questions": [{
            "id": 1,
            "question": default_data['question'],
            "examples": default_data['examples'],
            "solution": default_data['solution'],
            "code": default_data['code'],
            "time_complexity": default_data['time_complexity'],
            "space_complexity": default_data['space_complexity'],
            "difficulty": difficulty,
            "topic": topic
        }]
    }

def answer_dsa_question_with_groq(question: str, context: str = "") -> dict:
    """Answer DSA questions directly using Groq API"""
    if not question or not question.strip():
        logger.warning("Empty question provided")
        return {"answer": "Question is required", "error": True}
        
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
    if not classification:
        logger.warning("No classification provided")
        return None
        
    if not original_query or not original_query.strip():
        logger.warning("No original query provided")
        return None
        
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
    
    # ENHANCED: Better question generation handling
    if t == "question_generation":
        processor = QueryProcessor()
        ctx = processor.extract_dsa_context(original_query)
        
        # Determine topic - enhanced detection
        topic = 'general'  # default
        if ctx['topics']:
            topic = ctx['topics'][0]
        else:
            # Try to extract topic from query manually
            query_lower = original_query.lower()
            for topic_key, keywords in DSA_TOPICS.items():
                if any(keyword in query_lower for keyword in keywords):
                    topic = topic_key
                    break
        
        # Determine difficulty from query
        difficulty = 'medium'  # default
        query_lower = original_query.lower()
        if any(word in query_lower for word in ['easy', 'beginner', 'simple', 'basic']):
            difficulty = 'easy'
        elif any(word in query_lower for word in ['hard', 'difficult', 'advanced', 'expert', 'challenging']):
            difficulty = 'hard'
        
        # Generate questions using Groq API
        logger.info(f"Generating questions for topic: {topic}, difficulty: {difficulty}")
        questions_data = generate_dsa_questions_with_groq(topic, difficulty, 2)
        
        if questions_data.get("error") or not questions_data.get("questions"):
            return {
                **base,
                "best_book": {
                    "title": "Question Generation 🤔",
                    "content": "I'm having trouble generating questions right now. Please specify a topic (arrays, trees, graphs, etc.) and I'll help you practice!\n\nExample: 'Generate easy array questions' or 'Give me graph problems'"
                },
                "summary": "Specify a DSA topic for practice questions."
            }
        
        # FIXED: Better content formatting for frontend display
        questions = questions_data.get("questions", [])
        if questions:
            content = f"Here are some **{difficulty}** practice questions about **{topic.replace('_', ' ').title()}**:\n\n"
            
            for i, q in enumerate(questions[:2], 1):
                content += f"## 📝 Question {i}\n\n"
                content += f"**Problem:** {q.get('question', 'N/A')}\n\n"
                
                if q.get('examples'):
                    content += f"**Example:** {q.get('examples')}\n\n"
                
                content += f"**Solution Approach:**\n{q.get('solution', 'See code implementation')}\n\n"
                
                if q.get('code'):
                    content += f"**Implementation:**\n```python\n{q.get('code')}\n```\n\n"
                
                content += f"**Complexity Analysis:**\n"
                content += f"- Time: {q.get('time_complexity', 'O(n)')}\n"
                content += f"- Space: {q.get('space_complexity', 'O(1)')}\n\n"
                
                if i < len(questions):
                    content += "---\n\n"
            
            # Add encouraging message
            content += f"\n💡 **Tips:** Practice these step by step. Start with the examples and try to implement before looking at the solution!"
        else:
            content = f"I can help you practice {topic.replace('_', ' ')} problems. What specific aspect would you like to focus on?"
        
        return {
            **base,
            "best_book": {
                "title": f"{difficulty.title()} {topic.replace('_', ' ').title()} Practice Questions 📚",
                "content": content
            },
            "summary": f"Generated {len(questions)} practice questions for {topic.replace('_', ' ')}"
        }
    
    if t == "vague_question":
        if "dsa" in original_query.lower():
            return {
                **base,
                "best_book": {
                    "title": "What is DSA? 🎯",
                    "content": "DSA stands for **Data Structures and Algorithms**.\n\n**Data Structures** organize and store data efficiently:\n- Arrays, Linked Lists, Stacks, Queues\n- Trees, Graphs, Hash Tables\n\n**Algorithms** solve problems step-by-step:\n- Sorting, Searching\n- Graph traversal, Dynamic Programming\n\nDSA is essential for coding interviews and building scalable systems!"
                },
                "summary": "DSA = Data Structures + Algorithms for efficient problem solving."
            }
        return {
            **base,
            "best_book": {
                "title": "I'm here to help! 🤝",
                "content": "Please specify what you'd like to learn about:\n\n**Topics I can help with:**\n- Data Structures (arrays, trees, graphs, etc.)\n- Algorithms (sorting, searching, DP, etc.)\n- Complexity analysis\n- Practice problems generation\n\n**Try asking:**\n- \"Explain binary trees\"\n- \"Generate array problems\"\n- \"How does merge sort work?\""
            },
            "summary": "Specify a DSA topic and I'll help you learn!"
        }
    
    # IMPORTANT: Return None for dsa_specific so it goes to the main DSA processing
    return None

def enhanced_summarize_with_context(text: str, ctx: dict, original_query: str) -> str | None:
    if not text or not text.strip():
        logger.warning("Empty text provided for summarization")
        return None
        
    if not ctx:
        logger.warning("No context provided for summarization")
        return None
        
    api_key = current_app.config.get("GROQ_API_KEY")
    if not api_key:
        logger.warning("No Groq API key for summarization")
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
    if ctx.get('question_generation_asked'):
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
