# app/services/intent.py - Enhanced Intent Classification and Response Generation
import json
import re
import requests
import logging
from flask import current_app
from typing import Dict, List, Optional, Any

logger = logging.getLogger("dsa-mentor")

# DSA Topics Mapping
DSA_TOPICS = {
    'array': ['array', 'arrays', 'list', 'arraylist', 'vector'],
    'linked_list': ['linked list', 'linkedlist', 'node', 'pointer', 'singly', 'doubly'],
    'stack': ['stack', 'lifo', 'push', 'pop', 'call stack'],
    'queue': ['queue', 'fifo', 'enqueue', 'dequeue', 'priority queue'],
    'tree': ['tree', 'binary tree', 'bst', 'binary search tree', 'avl', 'heap', 'trie'],
    'graph': ['graph', 'vertex', 'edge', 'adjacency', 'dijkstra', 'bfs', 'dfs', 'spanning tree'],
    'sorting': ['sort', 'sorting', 'bubble sort', 'merge sort', 'quick sort', 'heap sort', 'radix sort'],
    'searching': ['search', 'searching', 'binary search', 'linear search', 'hash table'],
    'dynamic_programming': ['dp', 'dynamic programming', 'memoization', 'tabulation', 'optimization'],
    'recursion': ['recursion', 'recursive', 'backtracking', 'divide and conquer'],
    'hashing': ['hash', 'hashing', 'hash table', 'hash map', 'collision'],
    'string': ['string', 'substring', 'pattern matching', 'kmp', 'rabin karp']
}


class QueryProcessor:
    """Enhanced query processing with better context extraction"""
    
    @staticmethod
    def clean_and_normalize_query(query: str) -> str:
        """Clean and normalize user query with improved validation"""
        if not query or not isinstance(query, str):
            return ""
        
        # Basic cleaning
        query = re.sub(r'\s+', ' ', query.strip())
        normalized = re.sub(r'[^\w\s?!.+\-(){}[\]]', '', query.lower())
        
        # Common typo corrections
        typo_corrections = {
            r'\balgorithem\b': 'algorithm',
            r'\balgoritm\b': 'algorithm',
            r'\blinklist\b': 'linked list',
            r'\bgrapth\b': 'graph',
            r'\bsearch\b': 'searching',
            r'\bsort\b': 'sorting',
            r'\brecursiv\b': 'recursion',
            r'\bdp\b': 'dynamic programming',
            r'\bbfs\b': 'breadth first search',
            r'\bdfs\b': 'depth first search'
        }
        
        for pattern, correction in typo_corrections.items():
            normalized = re.sub(pattern, correction, normalized)
        
        return normalized
    
    @staticmethod
    def extract_dsa_context(query: str) -> Dict[str, Any]:
        """Extract comprehensive DSA context from query"""
        if not query or not isinstance(query, str):
            return {
                'topics': [],
                'complexity_asked': False,
                'implementation_asked': False,
                'example_asked': False,
                'comparison_asked': False,
                'question_generation_asked': False,
                'difficulty_level': 'medium',
                'language_preference': None
            }
        
        normalized = query.lower()
        
        ctx = {
            'topics': [],
            'complexity_asked': False,
            'implementation_asked': False,
            'example_asked': False,
            'comparison_asked': False,
            'question_generation_asked': False,
            'difficulty_level': 'medium',
            'language_preference': None
        }
        
        # Topic detection with confidence scoring
        topic_scores = {}
        for topic, keywords in DSA_TOPICS.items():
            score = sum(1 for keyword in keywords if keyword in normalized)
            if score > 0:
                topic_scores[topic] = score
        
        # Sort topics by relevance
        ctx['topics'] = sorted(topic_scores.keys(), key=lambda x: topic_scores[x], reverse=True)
        
        # Intent detection
        complexity_keywords = ['time complexity', 'space complexity', 'big o', 'complexity', 'runtime', 'efficiency']
        ctx['complexity_asked'] = any(w in normalized for w in complexity_keywords)
        
        implementation_keywords = ['implement', 'code', 'program', 'write', 'coding', 'solution', 'algorithm']
        ctx['implementation_asked'] = any(w in normalized for w in implementation_keywords)
        
        example_keywords = ['example', 'sample', 'demo', 'show me', 'illustrate']
        ctx['example_asked'] = any(w in normalized for w in example_keywords)
        
        comparison_keywords = ['vs', 'versus', 'compare', 'difference', 'better', 'which is', 'pros and cons']
        ctx['comparison_asked'] = any(w in normalized for w in comparison_keywords)
        
        question_gen_keywords = [
            'generate question', 'create question', 'ask question', 'practice question',
            'quiz', 'test me', 'give me question', 'generate problem', 'practice problem',
            'problems to solve', 'exercises'
        ]
        ctx['question_generation_asked'] = any(w in normalized for w in question_gen_keywords)
        
        # Difficulty level detection
        if any(word in normalized for word in ['easy', 'beginner', 'simple', 'basic', 'introduction']):
            ctx['difficulty_level'] = 'easy'
        elif any(word in normalized for word in ['hard', 'difficult', 'advanced', 'expert', 'challenging', 'complex']):
            ctx['difficulty_level'] = 'hard'
        
        # Programming language detection
        languages = ['python', 'java', 'javascript', 'cpp', 'c++', 'c', 'go', 'rust', 'swift']
        for lang in languages:
            if lang in normalized:
                ctx['language_preference'] = lang
                break
        
        return ctx


def classify_query_fallback(query: str) -> Dict[str, Any]:
    """Enhanced fallback classification with better DSA detection"""
    if not query or not isinstance(query, str):
        return {
            "type": "vague_question",
            "confidence": 0.3,
            "is_dsa": False,
            "reasoning": "empty or invalid query"
        }
    
    q = query.lower().strip()
    
    # Greeting patterns
    greeting_patterns = [
        'hi', 'hello', 'hey', 'greetings', 'good morning', 
        'good afternoon', 'good evening', 'howdy', 'sup'
    ]
    if any(x in q for x in greeting_patterns) and len(q) < 50:
        return {
            "type": "greeting",
            "confidence": 0.9,
            "is_dsa": False,
            "reasoning": "greeting pattern detected"
        }
    
    # Casual chat patterns
    casual_patterns = [
        'how are you', 'how r u', 'whats up', "what's up", 
        "how's it going", "how do you do", "nice to meet you"
    ]
    if any(x in q for x in casual_patterns):
        return {
            "type": "casual_chat",
            "confidence": 0.8,
            "is_dsa": False,
            "reasoning": "casual conversation pattern"
        }
    
    # Question generation patterns
    question_patterns = [
        'generate question', 'create question', 'practice question', 'quiz me',
        'test me', 'give me question', 'generate problem', 'practice problem',
        'give me practice', 'problems to solve', 'exercises'
    ]
    if any(x in q for x in question_patterns):
        return {
            "type": "question_generation",
            "confidence": 0.95,
            "is_dsa": True,
            "reasoning": "question generation request detected"
        }
    
    # DSA topic detection
    processor = QueryProcessor()
    ctx = processor.extract_dsa_context(q)
    
    if ctx['topics']:
        confidence = min(0.9, 0.6 + len(ctx['topics']) * 0.1)
        return {
            "type": "dsa_specific",
            "confidence": confidence,
            "is_dsa": True,
            "reasoning": f"DSA topics detected: {', '.join(ctx['topics'][:3])}"
        }
    
    # Additional DSA keywords
    dsa_keywords = [
        'algorithm', 'complexity', 'data structure', 'big o notation',
        'coding interview', 'leetcode', 'competitive programming',
        'optimization', 'efficient', 'performance'
    ]
    
    keyword_matches = sum(1 for keyword in dsa_keywords if keyword in q)
    if keyword_matches > 0:
        confidence = min(0.8, 0.5 + keyword_matches * 0.1)
        return {
            "type": "dsa_specific",
            "confidence": confidence,
            "is_dsa": True,
            "reasoning": f"DSA keywords detected ({keyword_matches} matches)"
        }
    
    # Programming-related terms
    programming_terms = [
        'code', 'programming', 'function', 'variable', 'loop',
        'condition', 'syntax', 'debug', 'compile', 'runtime'
    ]
    
    if any(term in q for term in programming_terms):
        return {
            "type": "dsa_specific",
            "confidence": 0.6,
            "is_dsa": True,
            "reasoning": "programming-related terms detected"
        }
    
    return {
        "type": "vague_question",
        "confidence": 0.4,
        "is_dsa": False,
        "reasoning": "no specific pattern detected"
    }


def classify_query_with_groq(user_query: str) -> Dict[str, Any]:
    """Enhanced Groq API classification with comprehensive error handling"""
    if not user_query or not user_query.strip():
        logger.warning("Empty query provided to classifier")
        return classify_query_fallback("")
    
    try:
        # Get API configuration
        api_key = current_app.config.get("GROQ_API_KEY")
        api_url = current_app.config.get("GROQ_CHAT_API_URL")
        
        if not api_key or not api_url:
            logger.warning("Groq API not configured, using fallback")
            return classify_query_fallback(user_query)
        
    except Exception as e:
        logger.warning(f"Error accessing config, using fallback: {e}")
        return classify_query_fallback(user_query)
    
    # Prepare enhanced API request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Enhanced system prompt with better instructions
    system_prompt = """You are an intelligent intent classifier for a DSA (Data Structures & Algorithms) educational chatbot.

Classify user queries into these categories:
- "greeting": Hi, hello, good morning, casual greetings
- "casual_chat": How are you, what's up, personal conversation
- "fun_chat": General friendly conversation, jokes, off-topic
- "dsa_specific": Questions about algorithms, data structures, coding, complexity, programming concepts
- "question_generation": Requests to generate/create practice questions, problems, quizzes, or exercises
- "vague_question": Unclear, very general, or ambiguous questions

Guidelines:
1. DSA-related terms: array, linked list, tree, graph, sorting, searching, recursion, dynamic programming, etc. → "dsa_specific"
2. Requests like "generate questions", "create quiz", "practice problems", "test me" → "question_generation"  
3. Programming concepts: complexity, algorithms, data structures, coding → "dsa_specific"
4. Simple greetings without follow-up questions → "greeting"
5. Personal questions or casual conversation → "casual_chat"

Respond with ONLY valid JSON in this exact format:
{"type": "category", "confidence": 0.8, "is_dsa": true/false, "reasoning": "brief explanation"}

Confidence scale: 0.1-1.0 (higher for clear, unambiguous queries)
Set is_dsa=true for dsa_specific and question_generation categories."""
    
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Classify this query: '{user_query}'"}
        ],
        "temperature": 0.1,
        "max_tokens": 200,
        "top_p": 0.9
    }
    
    try:
        logger.debug(f"🔍 Calling Groq API for classification: '{user_query[:50]}...'")
        
        response = requests.post(
            api_url, 
            headers=headers, 
            json=payload, 
            timeout=15
        )
        response.raise_for_status()
        
        response_json = response.json()
        
        # Enhanced response parsing
        content = _extract_response_content(response_json)
        if not content:
            logger.error("Empty content from Groq API")
            return classify_query_fallback(user_query)
        
        # Clean and parse JSON
        cleaned_content = _clean_json_content(content)
        
        try:
            parsed = json.loads(cleaned_content)
            return _validate_classification_result(parsed, user_query)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}, content: {repr(cleaned_content[:200])}")
            return classify_query_fallback(user_query)
        
    except requests.exceptions.Timeout:
        logger.error("Groq API timeout - using fallback")
        return classify_query_fallback(user_query)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Groq API request error: {e} - using fallback")
        return classify_query_fallback(user_query)
        
    except Exception as e:
        logger.error(f"Unexpected error in Groq classification: {e} - using fallback")
        return classify_query_fallback(user_query)


def _extract_response_content(response_json: Dict) -> Optional[str]:
    """Extract content from Groq API response with multiple fallbacks"""
    try:
        # Try different response formats
        if "choices" in response_json:
            choices = response_json["choices"]
            
            if isinstance(choices, list) and len(choices) > 0:
                choice = choices[0]
            elif isinstance(choices, dict):
                choice = choices
            else:
                return None
            
            if "message" in choice:
                return choice["message"].get("content", "").strip()
            elif "text" in choice:
                return choice["text"].strip()
        
        # Direct content field
        if "content" in response_json:
            return response_json["content"].strip()
            
        return None
        
    except Exception as e:
        logger.error(f"Error extracting response content: {e}")
        return None


def _clean_json_content(content: str) -> str:
    """Clean and extract JSON from Groq response"""
    if not content:
        return ""
    
    # Remove code block markers
    patterns = [
        r'```json\s*(.*?)\s*```',
        r'```\s*(.*?)\s*```',
        r'json\s*(.*?)$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            break
    
    # Remove any leading/trailing non-JSON content
    start = content.find('{')
    end = content.rfind('}')
    
    if start != -1 and end != -1 and start <= end:
        content = content[start:end+1]
    
    return content.strip()


def _validate_classification_result(parsed: Dict, user_query: str) -> Dict[str, Any]:
    """Validate and normalize classification result"""
    if not isinstance(parsed, dict):
        raise ValueError("Classification result must be a dictionary")
    
    # Validate required fields
    if not isinstance(parsed.get("type"), str):
        logger.error("Missing or invalid 'type' field in classification")
        raise ValueError("Invalid classification format")
    
    valid_types = ["greeting", "casual_chat", "fun_chat", "dsa_specific", "question_generation", "vague_question"]
    if parsed["type"] not in valid_types:
        logger.warning(f"Invalid type '{parsed['type']}', defaulting to 'vague_question'")
        parsed["type"] = "vague_question"
    
    # Normalize confidence
    confidence = parsed.get("confidence", 0.5)
    if not isinstance(confidence, (int, float)):
        confidence = 0.5
    parsed["confidence"] = max(0.0, min(1.0, float(confidence)))
    
    # Normalize is_dsa
    if "is_dsa" not in parsed:
        parsed["is_dsa"] = parsed["type"] in ["dsa_specific", "question_generation"]
    else:
        parsed["is_dsa"] = bool(parsed["is_dsa"])
    
    # Add reasoning if missing
    if "reasoning" not in parsed or not parsed["reasoning"]:
        parsed["reasoning"] = f"Classified as {parsed['type']}"
    
    # Validate consistency
    if parsed["type"] in ["dsa_specific", "question_generation"] and not parsed["is_dsa"]:
        parsed["is_dsa"] = True
        logger.debug("Corrected is_dsa flag for DSA-related classification")
    
    logger.info(f"✅ Groq classification successful: {parsed['type']} (confidence: {parsed['confidence']:.2f})")
    return parsed


def generate_response_by_intent(classification: Dict[str, Any], original_query: str) -> Optional[Dict]:
    """Generate contextual responses based on classification with enhanced content"""
    if not classification or not original_query:
        logger.warning("Missing classification or query for response generation")
        return None
    
    base_response = {"top_dsa": [], "video_suggestions": []}
    intent_type = classification.get("type", "general")
    
    # Enhanced response generation based on intent
    if intent_type == "greeting":
        return {
            **base_response,
            "best_book": {
                "title": "Hello! 👋 Welcome to DSA Mentor",
                "content": "Hi there! I'm your AI companion for mastering Data Structures and Algorithms. I can help you with:\n\n• **Algorithm explanations** with step-by-step breakdowns\n• **Code implementations** in multiple languages\n• **Complexity analysis** and optimization tips\n• **Practice problems** tailored to your level\n• **Interview preparation** strategies\n\nWhat DSA topic would you like to explore today?"
            },
            "summary": "Ready to help you master DSA concepts!"
        }
    
    elif intent_type == "casual_chat":
        return {
            **base_response,
            "best_book": {
                "title": "I'm doing great! 😊",
                "content": "Thanks for asking! I'm here and excited to help you learn Data Structures and Algorithms. \n\nWhether you're preparing for coding interviews, working on assignments, or just curious about how algorithms work, I'm here to guide you through it all.\n\n**What can we explore together today?**\n• Binary trees and traversals\n• Sorting and searching algorithms\n• Dynamic programming patterns\n• Graph algorithms\n• Or any other DSA topic you're curious about!"
            },
            "summary": "Ready to dive into some awesome DSA learning!"
        }
    
    elif intent_type == "fun_chat":
        return {
            **base_response,
            "best_book": {
                "title": "That's awesome! 🎉",
                "content": "I love friendly conversations! While I enjoy chatting, I'm most passionate about helping you master Data Structures and Algorithms.\n\n**Did you know?** Some of the most beautiful concepts in computer science come from DSA:\n• The elegance of recursive solutions\n• The power of divide-and-conquer strategies\n• The efficiency of well-designed data structures\n\nReady to explore something fascinating in the world of algorithms?"
            },
            "summary": "Let's blend fun with learning - DSA can be exciting!"
        }
    
    elif intent_type == "question_generation":
        return _handle_question_generation(original_query, base_response)
    
    elif intent_type == "vague_question":
        return _handle_vague_question(original_query, base_response, classification)
    
    # Return None for dsa_specific to allow main DSA processing
    return None


def _handle_question_generation(original_query: str, base_response: Dict) -> Dict:
    """Handle question generation requests with enhanced content"""
    processor = QueryProcessor()
    ctx = processor.extract_dsa_context(original_query)
    
    # Determine topic and difficulty
    topic = ctx['topics'][0] if ctx['topics'] else 'general'
    difficulty = ctx['difficulty_level']
    language = ctx['language_preference'] or 'python'
    
    # Generate enhanced response
    topic_display = topic.replace('_', ' ').title()
    
    content = f"# 🎯 {difficulty.title()} {topic_display} Practice Problems\n\n"
    
    if topic == 'general':
        content += """I'd be happy to generate practice problems for you! To provide the most relevant questions, please specify:

**Topics I can help with:**
• **Arrays & Strings** - Two pointers, sliding window, manipulation
• **Linked Lists** - Traversal, reversal, cycle detection
• **Stacks & Queues** - Implementation, applications, monotonic stacks
• **Trees** - Binary trees, BST, traversals, lowest common ancestor
• **Graphs** - BFS, DFS, shortest path, topological sort
• **Dynamic Programming** - 1D/2D DP, optimization problems
• **Sorting & Searching** - Binary search, merge sort, quick sort
• **Recursion & Backtracking** - Permutations, combinations, N-queens

**Example requests:**
• "Generate medium-level binary tree problems"
• "Create easy array manipulation questions"
• "Give me hard dynamic programming challenges"

What specific topic interests you most?"""
    
    else:
        # Topic-specific problem generation
        problems = _get_sample_problems(topic, difficulty, language)
        content += f"Here are some **{difficulty}** practice problems for **{topic_display}**:\n\n"
        
        for i, problem in enumerate(problems[:2], 1):
            content += f"## 📝 Problem {i}: {problem['title']}\n\n"
            content += f"**Description:** {problem['description']}\n\n"
            
            if problem.get('example'):
                content += f"**Example:**\n```\n{problem['example']}\n```\n\n"
            
            content += f"**Approach:** {problem['approach']}\n\n"
            
            if problem.get('code'):
                content += f"**{language.title()} Implementation:**\n```{language}\n{problem['code']}\n```\n\n"
            
            content += f"**Time Complexity:** {problem['time_complexity']}\n"
            content += f"**Space Complexity:** {problem['space_complexity']}\n\n"
            
            if i < len(problems):
                content += "---\n\n"
        
        content += f"\n💡 **Next Steps:**\n"
        content += f"• Try implementing these solutions step by step\n"
        content += f"• Test with different edge cases\n"
        content += f"• Analyze the time and space complexity\n"
        content += f"• Ask me if you need clarification on any concept!\n\n"
        content += f"Would you like more **{topic_display}** problems or questions on a different topic?"
    
    return {
        **base_response,
        "best_book": {
            "title": f"{difficulty.title()} {topic_display} Practice",
            "content": content
        },
        "summary": f"Generated {difficulty} level practice problems for {topic_display}"
    }


def _get_sample_problems(topic: str, difficulty: str, language: str) -> List[Dict]:
    """Generate sample problems for different topics and difficulty levels"""
    
    problems_db = {
        'array': {
            'easy': [
                {
                    'title': 'Two Sum',
                    'description': 'Given an array of integers and a target sum, return indices of two numbers that add up to the target.',
                    'example': 'Input: nums = [2,7,11,15], target = 9\nOutput: [0,1]',
                    'approach': 'Use a hash map to store seen numbers and their indices. For each number, check if (target - number) exists in the map.',
                    'code': 'def two_sum(nums, target):\n    seen = {}\n    for i, num in enumerate(nums):\n        complement = target - num\n        if complement in seen:\n            return [seen[complement], i]\n        seen[num] = i\n    return []',
                    'time_complexity': 'O(n)',
                    'space_complexity': 'O(n)'
                }
            ],
            'medium': [
                {
                    'title': '3Sum',
                    'description': 'Given an array of integers, find all unique triplets that sum to zero.',
                    'example': 'Input: nums = [-1,0,1,2,-1,-4]\nOutput: [[-1,-1,2],[-1,0,1]]',
                    'approach': 'Sort the array, then use three pointers: fix one and use two pointers to find the other two.',
                    'code': 'def three_sum(nums):\n    nums.sort()\n    result = []\n    for i in range(len(nums) - 2):\n        if i > 0 and nums[i] == nums[i-1]:\n            continue\n        left, right = i + 1, len(nums) - 1\n        while left < right:\n            total = nums[i] + nums[left] + nums[right]\n            if total == 0:\n                result.append([nums[i], nums[left], nums[right]])\n                while left < right and nums[left] == nums[left+1]:\n                    left += 1\n                while left < right and nums[right] == nums[right-1]:\n                    right -= 1\n                left += 1\n                right -= 1\n            elif total < 0:\n                left += 1\n            else:\n                right -= 1\n    return result',
                    'time_complexity': 'O(n²)',
                    'space_complexity': 'O(1)'
                }
            ]
        },
        'tree': {
            'easy': [
                {
                    'title': 'Maximum Depth of Binary Tree',
                    'description': 'Find the maximum depth of a binary tree.',
                    'example': 'Input: [3,9,20,null,null,15,7]\nOutput: 3',
                    'approach': 'Use recursion: depth of a node = 1 + max(depth of left child, depth of right child)',
                    'code': 'def max_depth(root):\n    if not root:\n        return 0\n    return 1 + max(max_depth(root.left), max_depth(root.right))',
                    'time_complexity': 'O(n)',
                    'space_complexity': 'O(h) where h is height'
                }
            ]
        }
    }
    
    # Return problems for the topic and difficulty, with fallback
    topic_problems = problems_db.get(topic, problems_db['array'])
    difficulty_problems = topic_problems.get(difficulty, topic_problems.get('easy', []))
    
    if not difficulty_problems:
        # Generate generic problem structure
        return [{
            'title': f'{topic.title()} Problem',
            'description': f'A {difficulty} level problem involving {topic.replace("_", " ")}.',
            'approach': 'Think about the key properties and operations of this data structure.',
            'time_complexity': 'O(n)',
            'space_complexity': 'O(1)'
        }]
    
    return difficulty_problems


def _handle_vague_question(original_query: str, base_response: Dict, classification: Dict) -> Dict:
    """Handle vague questions with helpful guidance"""
    confidence = classification.get('confidence', 0.5)
    
    if "dsa" in original_query.lower() or "data structure" in original_query.lower():
        return {
            **base_response,
            "best_book": {
                "title": "DSA Overview 🎯",
                "content": """# Data Structures and Algorithms (DSA)

**DSA** is the foundation of computer science and programming interviews!

## 📊 **Data Structures** organize and store data efficiently:
• **Linear:** Arrays, Linked Lists, Stacks, Queues
• **Non-linear:** Trees, Graphs, Heaps
• **Hash-based:** Hash Tables, Hash Sets

## ⚡ **Algorithms** solve problems step-by-step:
• **Searching:** Binary Search, Linear Search
• **Sorting:** Merge Sort, Quick Sort, Heap Sort
• **Graph:** BFS, DFS, Dijkstra, Topological Sort
• **Dynamic Programming:** Optimization problems
• **Greedy:** Local optimal choices

## 🎯 **Why DSA matters:**
• **Coding Interviews:** Essential for FAANG and tech companies
• **Problem Solving:** Develop algorithmic thinking
• **Performance:** Write efficient, scalable code
• **Foundation:** Core of computer science concepts

**Ready to dive deeper?** Ask me about any specific topic, like:
• "Explain binary search trees"
• "How does merge sort work?"
• "Generate practice problems for arrays"
"""
            },
            "summary": "DSA combines efficient data organization with powerful problem-solving algorithms!"
        }
    
    # General vague question
    content = "I'm here to help you learn Data Structures and Algorithms! 🚀\n\n"
    
    if confidence < 0.4:
        content += "Your question seems quite broad. To give you the most helpful answer, try being more specific.\n\n"
    
    content += """**Here's how I can help you:**

🔍 **Explain Concepts:** "What is a binary search tree?" or "How does dynamic programming work?"

💻 **Code Examples:** "Implement merge sort in Python" or "Show me how to reverse a linked list"

📈 **Complexity Analysis:** "What's the time complexity of quicksort?" or "Analyze space complexity of DFS"

🎯 **Practice Problems:** "Generate easy array problems" or "Give me graph algorithm questions"

🆚 **Compare Algorithms:** "Binary search vs linear search" or "Stack vs queue differences"

**Popular topics to explore:**
• Arrays and String Manipulation
• Linked Lists and Pointers  
• Stacks, Queues, and Trees
• Graph Algorithms and Traversal
• Sorting and Searching
• Dynamic Programming
• Recursion and Backtracking

**What specific DSA topic interests you most?**"""
    
    return {
        **base_response,
        "best_book": {
            "title": "How can I help you learn DSA? 🤔",
            "content": content
        },
        "summary": "Ask me about specific DSA topics for personalized help!"
    }


def enhanced_summarize_with_context(text: str, ctx: Dict, original_query: str) -> Optional[str]:
    """Enhanced summarization with DSA context awareness"""
    if not text or not text.strip():
        return None
    
    try:
        # Extract key information based on context
        topics = ctx.get('topics', [])
        
        if ctx.get('complexity_asked'):
            # Focus on complexity analysis
            summary = f"**Complexity Analysis:**\n\n{text[:500]}..."
        elif ctx.get('implementation_asked'):
            # Focus on implementation details
            summary = f"**Implementation Guide:**\n\n{text[:500]}..."
        elif ctx.get('comparison_asked'):
            # Focus on comparisons
            summary = f"**Comparison Overview:**\n\n{text[:500]}..."
        else:
            # General summarization
            summary = f"**About {', '.join(topics[:2]) if topics else 'DSA'}:**\n\n{text[:500]}..."
        
        if len(text) > 500:
            summary += f"\n\n*This is a summary. Ask for more details about specific aspects!*"
        
        return summary
        
    except Exception as e:
        logger.error(f"Enhanced summarization failed: {e}")
        return text[:300] + "..." if len(text) > 300 else text
