# IMPROVED app/services/intent.py - Better Error Handling and Code Structure

import json
import re
import requests
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
        """Clean and normalize user query with improved validation"""
        if not query or not isinstance(query, str):
            return ""
        
        # Basic cleaning
        query = re.sub(r'\s+', ' ', query.strip())
        normalized = re.sub(r'[^\w\s?!.+\-]', '', query.lower())
        
        # Common typo corrections
        typo_corrections = {
            r'\balgorithem\b': 'algorithm',
            r'\balgoritm\b': 'algorithm',
            r'\blinklist\b': 'linked list',
            r'\bbst\b': 'binary search tree',
            r'\bgrapth\b': 'graph',
            r'\bsearch\b': 'searching',
            r'\bsort\b': 'sorting',
            r'\brecursiv\b': 'recursion'
        }
        
        for pattern, correction in typo_corrections.items():
            normalized = re.sub(pattern, correction, normalized)
        
        return normalized

    @staticmethod
    def extract_dsa_context(query: str) -> dict:
        """Extract DSA context from query with comprehensive analysis"""
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

        # Topic detection
        for topic, keywords in DSA_TOPICS.items():
            if any(k in normalized for k in keywords):
                ctx['topics'].append(topic)

        # Intent detection
        complexity_keywords = ['time complexity', 'space complexity', 'big o', 'complexity']
        ctx['complexity_asked'] = any(w in normalized for w in complexity_keywords)
        
        implementation_keywords = ['implement', 'code', 'program', 'write', 'coding']
        ctx['implementation_asked'] = any(w in normalized for w in implementation_keywords)
        
        example_keywords = ['example', 'sample', 'demo', 'show me']
        ctx['example_asked'] = any(w in normalized for w in example_keywords)
        
        comparison_keywords = ['vs', 'versus', 'compare', 'difference', 'better']
        ctx['comparison_asked'] = any(w in normalized for w in comparison_keywords)
        
        question_gen_keywords = [
            'generate question', 'create question', 'ask question', 'practice question',
            'quiz', 'test me', 'give me question', 'generate problem', 'practice problem'
        ]
        ctx['question_generation_asked'] = any(w in normalized for w in question_gen_keywords)

        return ctx

def classify_query_fallback(query: str) -> dict:
    """Enhanced fallback classification with better DSA detection"""
    if not query or not isinstance(query, str):
        return {
            "type": "vague_question", 
            "confidence": 0.5, 
            "is_dsa": False, 
            "reasoning": "fallback empty query"
        }

    q = query.lower().strip()

    # Greeting patterns
    greeting_patterns = ['hi', 'hello', 'hey', 'greetings', 'good morning', 'good afternoon']
    if any(x in q for x in greeting_patterns):
        return {
            "type": "greeting", 
            "confidence": 0.8, 
            "is_dsa": False, 
            "reasoning": "fallback greeting pattern"
        }

    # Casual chat patterns
    casual_patterns = ['how are you', 'how r u', 'whats up', "what's up", "how's it going"]
    if any(x in q for x in casual_patterns):
        return {
            "type": "casual_chat", 
            "confidence": 0.8, 
            "is_dsa": False, 
            "reasoning": "fallback casual chat pattern"
        }

    # Question generation patterns
    question_patterns = [
        'generate question', 'create question', 'practice question', 'quiz me', 
        'test me', 'give me question', 'generate problem', 'practice problem', 
        'give me practice'
    ]
    if any(x in q for x in question_patterns):
        return {
            "type": "question_generation", 
            "confidence": 0.9, 
            "is_dsa": True, 
            "reasoning": "question generation request"
        }

    # DSA detection using topics
    processor = QueryProcessor()
    ctx = processor.extract_dsa_context(q)
    
    if ctx['topics']:
        return {
            "type": "dsa_specific", 
            "confidence": 0.9, 
            "is_dsa": True, 
            "reasoning": f"fallback detected: {ctx['topics']}"
        }

    # Additional DSA keywords
    dsa_keywords = [
        'algorithm', 'complexity', 'binary search', 'merge sort', 'linked list',
        'binary tree', 'graph traversal', 'data structure', 'big o', 'recursion',
        'dynamic programming', 'dp', 'leetcode', 'coding interview'
    ]
    
    if any(x in q for x in dsa_keywords):
        return {
            "type": "dsa_specific", 
            "confidence": 0.8, 
            "is_dsa": True, 
            "reasoning": "fallback keyword match"
        }

    return {
        "type": "vague_question", 
        "confidence": 0.5, 
        "is_dsa": False, 
        "reasoning": "fallback default"
    }

def classify_query_with_groq(user_query: str) -> dict:
    """IMPROVED: Groq API classification with robust error handling"""
    if not user_query or not user_query.strip():
        logger.warning("Empty query provided to classifier")
        return classify_query_fallback("")

    try:
        # Get API configuration
        api_key = current_app.config.get("GROQ_API_KEY")
        if not api_key:
            logger.warning("No Groq API key configured, using fallback")
            return classify_query_fallback(user_query)
        
        api_url = current_app.config.get("GROQ_CHAT_API_URL")
        if not api_url:
            logger.warning("No Groq API URL configured, using fallback")
            return classify_query_fallback(user_query)

    except Exception as e:
        logger.warning(f"Error accessing config, using fallback: {e}")
        return classify_query_fallback(user_query)

    # Prepare API request
    headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {api_key}"
    }
    
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
For requests like "generate questions", "create quiz", "practice problems", use "question_generation".

Respond with ONLY valid JSON in this format:
{"type": "category", "confidence": 0.8, "is_dsa": true/false, "reasoning": "explanation"}"""
            },
            {
                "role": "user", 
                "content": f"Classify this user query: '{user_query}'"
            }
        ],
        "temperature": 0.1,
        "max_tokens": 150
    }

    try:
        logger.info(f"🔍 Calling Groq API for classification: '{user_query[:50]}...'")
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        
        response_json = response.json()
        logger.debug(f"Groq API raw response: {response_json}")
        
        # IMPROVED: Better response parsing
        choices = response_json.get("choices")
        content = None
        
        if isinstance(choices, list) and len(choices) > 0:
            message = choices[0].get("message", {})
            content = message.get("content", "").strip()
        elif isinstance(choices, dict):
            message = choices.get("message", {})
            content = message.get("content", "").strip()
        else:
            logger.error(f"Unexpected Groq response format: {type(choices)}")
            return classify_query_fallback(user_query)

        if not content:
            logger.error("Empty content from Groq API")
            return classify_query_fallback(user_query)

        # IMPROVED: Content cleaning and parsing
        content = _clean_json_content(content)
        
        try:
            parsed = json.loads(content)
            return _validate_classification_result(parsed, user_query)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}, content: {repr(content[:200])}")
            return classify_query_fallback(user_query)

    except requests.exceptions.Timeout:
        logger.error("Groq API timeout")
        return classify_query_fallback(user_query)
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Groq API request error: {e}")
        return classify_query_fallback(user_query)
    
    except Exception as e:
        logger.error(f"Unexpected error in Groq classification: {e}")
        return classify_query_fallback(user_query)

def _clean_json_content(content: str) -> str:
    """Clean and extract JSON from Groq response"""
    if not content:
        return ""
    
    # Remove code block markers
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    if content.startswith("json"):
        content = content[4:]
    
    return content.strip()

def _validate_classification_result(parsed: dict, user_query: str) -> dict:
    """Validate and normalize classification result"""
    if not isinstance(parsed, dict):
        raise ValueError("Classification result must be a dictionary")
    
    # Validate required fields
    if not isinstance(parsed.get("type"), str):
        logger.error("Missing or invalid 'type' field in classification")
        raise ValueError("Invalid classification format")
    
    # Ensure confidence is a number
    if "confidence" not in parsed or not isinstance(parsed["confidence"], (int, float)):
        parsed["confidence"] = 0.5
    
    # Ensure confidence is between 0 and 1
    parsed["confidence"] = max(0.0, min(1.0, float(parsed["confidence"])))
    
    # Ensure is_dsa is boolean
    if "is_dsa" not in parsed:
        parsed["is_dsa"] = parsed.get("type") in ["dsa_specific", "question_generation"]
    else:
        parsed["is_dsa"] = bool(parsed["is_dsa"])
    
    # Add reasoning if missing
    if "reasoning" not in parsed:
        parsed["reasoning"] = f"Classified as {parsed['type']}"
    
    logger.info(f"Groq classification successful: {parsed}")
    return parsed

def generate_response_by_intent(classification: dict, original_query: str) -> dict | None:
    """Generate contextual responses based on classification"""
    if not classification or not original_query:
        logger.warning("Missing classification or query for response generation")
        return None

    base_response = {"top_dsa": [], "video_suggestions": []}
    intent_type = classification.get("type", "general")

    # Handle different intent types
    if intent_type == "greeting":
        return {
            **base_response,
            "best_book": {
                "title": "Hello! 👋",
                "content": "Hi there! I'm DSA Mentor, your AI assistant for learning Data Structures and Algorithms.\n\nWhat topic would you like to explore today?"
            },
            "summary": "Ready to help with any DSA topic!"
        }

    elif intent_type == "casual_chat":
        return {
            **base_response,
            "best_book": {
                "title": "I'm doing great! 😊",
                "content": "Thanks for asking! I'm here and ready to help you learn DSA concepts.\n\nWhat would you like to work on?"
            },
            "summary": "I'm doing well and ready to help you learn!"
        }

    elif intent_type == "fun_chat":
        return {
            **base_response,
            "best_book": {
                "title": "That's nice! 🎉",
                "content": "I appreciate the friendly chat! While I love conversation, I'm most helpful with DSA topics.\n\nAsk me about any concept!"
            },
            "summary": "I'm here for both fun and learning!"
        }

    elif intent_type == "question_generation":
        return _handle_question_generation(original_query, base_response)

    elif intent_type == "vague_question":
        return _handle_vague_question(original_query, base_response)

    # Return None for dsa_specific to allow main DSA processing
    return None

def _handle_question_generation(original_query: str, base_response: dict) -> dict:
    """Handle question generation requests"""
    processor = QueryProcessor()
    ctx = processor.extract_dsa_context(original_query)
    
    # Determine topic
    topic = 'general'
    if ctx['topics']:
        topic = ctx['topics'][0]
    else:
        # Manual topic extraction
        query_lower = original_query.lower()
        for topic_key, keywords in DSA_TOPICS.items():
            if any(keyword in query_lower for keyword in keywords):
                topic = topic_key
                break
    
    # Determine difficulty
    difficulty = 'medium'
    query_lower = original_query.lower()
    if any(word in query_lower for word in ['easy', 'beginner', 'simple', 'basic']):
        difficulty = 'easy'
    elif any(word in query_lower for word in ['hard', 'difficult', 'advanced', 'expert', 'challenging']):
        difficulty = 'hard'
    
    try:
        # Generate questions (this would call the question generation function)
        questions_data = generate_dsa_questions_with_groq(topic, difficulty, 2)
        
        if questions_data.get("error") or not questions_data.get("questions"):
            return {
                **base_response,
                "best_book": {
                    "title": "Question Generation 🤔",
                    "content": "I'm having trouble generating questions right now. Please specify a topic (arrays, trees, graphs, etc.) and I'll help you practice!\n\nExample: 'Generate easy array questions' or 'Give me graph problems'"
                },
                "summary": "Specify a DSA topic for practice questions."
            }
        
        questions = questions_data.get("questions", [])
        content = _format_questions_content(questions, topic, difficulty)
        
        return {
            **base_response,
            "best_book": {
                "title": f"{difficulty.title()} {topic.replace('_', ' ').title()} Practice Questions 📚",
                "content": content
            },
            "summary": f"Generated {len(questions)} practice questions for {topic.replace('_', ' ')}"
        }
        
    except Exception as e:
        logger.error(f"Question generation error: {e}")
        return {
            **base_response,
            "best_book": {
                "title": "Question Generation Error 🔧",
                "content": "I encountered an error while generating questions. Please try again or specify a different topic."
            },
            "summary": "Error occurred during question generation."
        }

def _handle_vague_question(original_query: str, base_response: dict) -> dict:
    """Handle vague questions"""
    if "dsa" in original_query.lower():
        return {
            **base_response,
            "best_book": {
                "title": "What is DSA? 🎯",
                "content": "DSA stands for **Data Structures and Algorithms**.\n\n**Data Structures** organize and store data efficiently:\n- Arrays, Linked Lists, Stacks, Queues\n- Trees, Graphs, Hash Tables\n\n**Algorithms** solve problems step-by-step:\n- Sorting, Searching\n- Graph traversal, Dynamic Programming\n\nDSA is essential for coding interviews and building scalable systems!"
            },
            "summary": "DSA = Data Structures + Algorithms for efficient problem solving."
        }

    return {
        **base_response,
        "best_book": {
            "title": "I'm here to help! 🤝",
            "content": "Please specify what you'd like to learn about:\n\n**Topics I can help with:**\n- Data Structures (arrays, trees, graphs, etc.)\n- Algorithms (sorting, searching, DP, etc.)\n- Complexity analysis\n- Practice problems generation\n\n**Try asking:**\n- \"Explain binary trees\"\n- \"Generate array problems\"\n- \"How does merge sort work?\""
        },
        "summary": "Specify a DSA topic and I'll help you learn!"
    }

def _format_questions_content(questions: list, topic: str, difficulty: str) -> str:
    """Format questions for display"""
    if not questions:
        return f"I can help you practice {topic.replace('_', ' ')} problems. What specific aspect would you like to focus on?"
    
    content = f"Here are some **{difficulty}** practice questions about **{topic.replace('_', ' ').title()}**:\n\n"
    
    for i, q in enumerate(questions[:2], 1):
        content += f"## 📝 Question {i}\n\n"
        content += f"**Problem:** {q.get('question', 'N/A')}\n\n"
        
        if q.get('examples'):
            content += f"**Example:** {q.get('examples')}\n\n"
        
        content += f"**Solution Approach:**\n{q.get('solution', 'See code implementation')}\n\n"
        
        if q.get('code'):
            content += f"**Implementation:**\n```python\n{q.get('code')}\n```\n\n"
        
        content += "**Complexity Analysis:**\n"
        content += f"- Time: {q.get('time_complexity', 'O(n)')}\n"
        content += f"- Space: {q.get('space_complexity', 'O(1)')}\n\n"
        
        if i < len(questions):
            content += "---\n\n"
    
    content += "\n💡 **Tips:** Practice these step by step. Start with the examples and try to implement before looking at the solution!"
    
    return content

# Question generation function (simplified version)
def generate_dsa_questions_with_groq(topic: str, difficulty: str = 'medium', count: int = 3) -> dict:
    """Generate DSA questions - placeholder implementation"""
    # This would implement the full question generation logic
    # For now, return a basic structure
    return {
        "questions": [{
            "question": f"Sample {difficulty} {topic} problem",
            "examples": "Input/Output example here",
            "solution": "Step-by-step solution approach",
            "code": "# Python implementation here",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)"
        }]
    }

def enhanced_summarize_with_context(text: str, ctx: dict, original_query: str) -> str | None:
    """Enhanced summarization with context - simplified version"""
    if not text or not text.strip():
        return None
    
    # Simplified summarization - in production, this would use Groq API
    return f"Based on your query about {', '.join(ctx.get('topics', ['DSA']))}, here's a focused summary of the content."
