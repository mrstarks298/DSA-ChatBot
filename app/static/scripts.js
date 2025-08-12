<script>
document.addEventListener('DOMContentLoaded', function() {
    const chatContent = document.getElementById('chatContent');
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendButton');
    const newThreadBtn = document.getElementById('newThreadBtn');
    const welcomeScreen = document.getElementById('welcomeScreen');
    const themeToggle = document.getElementById('themeToggle');
    const shareBtn = document.getElementById('shareBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const savedList = document.getElementById('savedList');
    const emptySaved = document.getElementById('emptySaved');
    const clearSavedBtn = document.getElementById('clearSavedBtn');
    
    let isFirstMessage = true;
    let savedMessages = new Map();
    let currentThreadId = generateThreadId();
    let authCheckInterval;
    
    // Get user data from Flask template (this comes from your server)
    let serverUser = {{ user|tojson|safe }};
    
    // Enhanced Authentication functions
    function checkAuthentication() {
        console.log('Checking authentication...', serverUser);
        
        // Check if serverUser exists and has required properties
        if (serverUser && 
            serverUser.is_authenticated === true && 
            serverUser.name && 
            serverUser.email) {
            
            hideAuthOverlay();
            updateUserProfile(serverUser);
            
            // Enable app functionality
            if (chatInput) chatInput.disabled = false;
            if (sendButton) sendButton.disabled = false;
            
            // Start periodic auth checks
            startPeriodicAuthCheck();
            
            return true;
        } else {
            showAuthOverlay();
            
            // Disable app functionality
            if (chatInput) chatInput.disabled = true;
            if (sendButton) sendButton.disabled = true;
            
            // Stop periodic auth checks
            stopPeriodicAuthCheck();
            
            return false;
        }
    }
    
    // Periodic authentication check for cross-device login detection
    function periodicAuthCheck() {
        fetch('/auth-status')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                const wasAuthenticated = serverUser.is_authenticated;
                const isNowAuthenticated = data.is_authenticated;
                
                // Check if authentication status changed
                if (wasAuthenticated !== isNowAuthenticated) {
                    console.log('Authentication status changed, reloading...');
                    notifyAuthChange();
                    window.location.reload();
                    return;
                }
                
                // Check if user changed (different user ID)
                if (isNowAuthenticated && 
                    serverUser.id && 
                    data.user_id && 
                    serverUser.id !== data.user_id) {
                    console.log('Different user detected, reloading...');
                    notifyAuthChange();
                    window.location.reload();
                }
            })
            .catch(error => {
                console.log('Periodic auth check failed:', error);
                // Don't reload on network errors, just log them
            });
    }
    
    function startPeriodicAuthCheck() {
        // Check every 30 seconds
        if (authCheckInterval) {
            clearInterval(authCheckInterval);
        }
        authCheckInterval = setInterval(periodicAuthCheck, 30000);
    }
    
    function stopPeriodicAuthCheck() {
        if (authCheckInterval) {
            clearInterval(authCheckInterval);
            authCheckInterval = null;
        }
    }
    
    // Cross-tab authentication synchronization
    function notifyAuthChange() {
        try {
            localStorage.setItem('auth_change', Date.now().toString());
            localStorage.removeItem('auth_change');
        } catch (error) {
            console.log('Could not notify auth change:', error);
        }
    }
    
    // Listen for auth changes in other tabs
    window.addEventListener('storage', function(e) {
        if (e.key === 'auth_change') {
            console.log('Auth change detected in another tab');
            setTimeout(() => {
                window.location.reload();
            }, 1000); // Small delay to avoid race conditions
        }
    });
    
    function showAuthOverlay() {
        document.body.classList.add('auth-required');
        const overlay = document.getElementById('authOverlay');
        if (overlay) {
            overlay.classList.remove('hidden');
            overlay.style.opacity = '1';
        }
    }
    
    function hideAuthOverlay() {
        document.body.classList.remove('auth-required');
        const overlay = document.getElementById('authOverlay');
        if (overlay) {
            overlay.style.opacity = '0';
            setTimeout(() => {
                overlay.classList.add('hidden');
            }, 300);
        }
    }
    
    function updateUserProfile(userData) {
        if (userData && userData.is_authenticated) {
            const profileAvatar = document.querySelector('.profile-avatar');
            const profileName = document.querySelector('.profile-name');
            const profileStatus = document.querySelector('.profile-status');
            
            if (profileAvatar && userData.name) {
                profileAvatar.textContent = userData.name.charAt(0).toUpperCase();
            }
            if (profileName && userData.name) {
                profileName.textContent = userData.name;
            }
            if (profileStatus && userData.email) {
                profileStatus.textContent = userData.email;
            }
        }
    }
    
    // Enhanced Login button handler
    const loginBtn = document.querySelector('.login-btn');
    if (loginBtn) {
        loginBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Login button clicked');
            
            // Add loading state
            const originalText = loginBtn.innerHTML;
            loginBtn.disabled = true;
            loginBtn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="animate-spin">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" stroke-dasharray="32" stroke-dashoffset="32">
                        <animate attributeName="stroke-dasharray" dur="2s" values="32;16;32" repeatCount="indefinite"/>
                        <animate attributeName="stroke-dashoffset" dur="2s" values="32;0;32" repeatCount="indefinite"/>
                    </circle>
                </svg>
                Redirecting...
            `;
            
            // Small delay to show loading state
            setTimeout(() => {
                window.location.href = '/login';
            }, 500);
            
            // Fallback to restore button if redirect fails
            setTimeout(() => {
                loginBtn.disabled = false;
                loginBtn.innerHTML = originalText;
            }, 5000);
        });
    }
    
    // Check authentication on page load
    checkAuthentication();
    
    // Generate unique thread ID
    function generateThreadId() {
        return 'thread_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    // Load saved messages from memory (no localStorage)
    function loadSavedMessages() {
        try {
            // Initialize empty map - no localStorage usage
            savedMessages = new Map();
        } catch (error) {
            console.log('Error loading saved messages:', error);
            savedMessages = new Map();
        }
        updateSavedMessagesList();
    }
    
    // Save messages to memory (no localStorage)
    function saveSavedMessages() {
        // Messages are kept in memory only during session
        // No localStorage usage to comply with Claude.ai restrictions
        console.log('Messages saved to session memory');
    }
    
    // Theme toggle functionality
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const body = document.body;
            const currentTheme = body.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            
            body.setAttribute('data-theme', newTheme);
            
            // Toggle icons
            const sunIcon = themeToggle.querySelector('.sun-icon');
            const moonIcon = themeToggle.querySelector('.moon-icon');
            
            if (newTheme === 'dark') {
                if (sunIcon) sunIcon.style.display = 'none';
                if (moonIcon) moonIcon.style.display = 'block';
            } else {
                if (sunIcon) sunIcon.style.display = 'block';
                if (moonIcon) moonIcon.style.display = 'none';
            }
        });
    }
    
    // Load default theme
    const defaultTheme = 'light';
    document.body.setAttribute('data-theme', defaultTheme);
    if (defaultTheme === 'dark') {
        const sunIcon = themeToggle?.querySelector('.sun-icon');
        const moonIcon = themeToggle?.querySelector('.moon-icon');
        if (sunIcon) sunIcon.style.display = 'none';
        if (moonIcon) moonIcon.style.display = 'block';
    }

    // Share functionality
    if (shareBtn) {
        shareBtn.addEventListener('click', function() {
            const shareModal = document.getElementById('shareModal');
            if (shareModal) shareModal.classList.add('active');
        });
    }

    // Download functionality
    if (downloadBtn) {
        downloadBtn.addEventListener('click', function() {
            downloadChat();
        });
    }

    // Clear saved messages
    if (clearSavedBtn) {
        clearSavedBtn.addEventListener('click', function() {
            savedMessages.clear();
            saveSavedMessages();
            updateSavedMessagesList();
            showToast('All saved messages cleared!');
        });
    }
    
    // New thread button
    if (newThreadBtn) {
        newThreadBtn.addEventListener('click', function() {
            currentThreadId = generateThreadId();
            
            if (chatContent) {
                chatContent.innerHTML = `
                    <div class="welcome-screen">
                        <h1 class="welcome-title">New Thread Started</h1>
                        <p class="welcome-subtitle">Ask me anything about Data Structures and Algorithms!</p>
                        <div class="suggestion-cards">
                            <div class="suggestion-card" onclick="askQuestion('Explain binary search algorithm with complexity analysis')">
                                <h4>🔍 Algorithm Analysis</h4>
                                <p>Learn about time and space complexity with detailed explanations</p>
                            </div>
                            <div class="suggestion-card" onclick="askQuestion('Show me how to implement a binary tree in Python')">
                                <h4>💻 Code Implementation</h4>
                                <p>Get clean, well-commented code in your preferred language</p>
                            </div>
                            <div class="suggestion-card" onclick="askQuestion('What are the best practices for solving dynamic programming problems?')">
                                <h4>🎯 Problem Solving</h4>
                                <p>Discover patterns and techniques for interview success</p>
                            </div>
                            <div class="suggestion-card" onclick="askQuestion('Give me practice problems for graph traversal')">
                                <h4>📝 Practice Problems</h4>
                                <p>Find curated problems to strengthen your skills</p>
                            </div>
                        </div>
                    </div>
                `;
            }
            isFirstMessage = true;
            showToast('New thread started. Your saved messages are still available!');
        });
    }
    
    // Function to ask predefined questions
    window.askQuestion = function(question) {
        if (!serverUser.is_authenticated) {
            showAuthOverlay();
            showToast('Please login to continue');
            return;
        }
        if (chatInput) {
            chatInput.value = question;
            sendMessage();
        }
    };

    // Function to extract YouTube video ID
    function extractYouTubeID(url) {
        if (!url) return null;
        
        const patterns = [
            /(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]+)/,
            /(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]+)/,
            /(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]+)/,
            /(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([a-zA-Z0-9_-]+)/
        ];
        
        for (const pattern of patterns) {
            const match = url.match(pattern);
            if (match && match[1]) {
                return match[1];
            }
        }
        return null;
    }

    // Function to open video modal
    window.openVideoModal = function(videoUrl, title) {
        const videoId = extractYouTubeID(videoUrl);
        if (videoId) {
            const embedUrl = `https://www.youtube.com/embed/${videoId}`;
            const videoEmbed = document.getElementById('videoEmbed');
            const videoModalTitle = document.getElementById('videoModalTitle');
            const videoModal = document.getElementById('videoModal');
            
            if (videoEmbed) videoEmbed.src = embedUrl;
            if (videoModalTitle) videoModalTitle.textContent = title || 'Video Tutorial';
            if (videoModal) videoModal.classList.add('active');
        } else {
            // Fallback: open in new tab
            window.open(videoUrl, '_blank');
        }
    };

    // Function to close video modal
    window.closeVideoModal = function() {
        const videoModal = document.getElementById('videoModal');
        const videoEmbed = document.getElementById('videoEmbed');
        
        if (videoModal) videoModal.classList.remove('active');
        if (videoEmbed) videoEmbed.src = '';
    };

    // Update saved messages list in sidebar
    function updateSavedMessagesList() {
        if (!savedList) return;
        
        const savedArray = Array.from(savedMessages.values());
        
        if (savedArray.length === 0) {
            if (emptySaved) emptySaved.style.display = 'block';
            if (clearSavedBtn) clearSavedBtn.style.display = 'none';
            savedList.innerHTML = '';
            if (emptySaved) savedList.appendChild(emptySaved);
        } else {
            if (emptySaved) emptySaved.style.display = 'none';
            if (clearSavedBtn) clearSavedBtn.style.display = 'block';
            
            savedList.innerHTML = '';
            
            savedArray.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
            
            savedArray.forEach((savedItem, index) => {
                const savedItemElement = document.createElement('li');
                savedItemElement.className = 'saved-item';
                savedItemElement.innerHTML = `
                    <svg class="saved-item-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M19 21L12 16L5 21V5C5 4.46957 5.21071 3.96086 5.58579 3.58579C5.96086 3.21071 6.46957 3 7 3H17C17.5304 3 18.0391 3.21071 18.4142 3.58579C18.7893 3.96086 19 4.46957 19 5V21Z" stroke="currentColor" stroke-width="2" fill="currentColor" fill-opacity="0.2"/>
                    </svg>
                    <div class="saved-item-content">
                        <div class="saved-item-title">${savedItem.title}</div>
                        <div class="saved-item-preview">${savedItem.preview}</div>
                    </div>
                    <button class="saved-item-delete" onclick="removeSavedMessage('${savedItem.id}')">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                        </svg>
                    </button>
                `;
                
                savedItemElement.addEventListener('click', function(e) {
                    if (!e.target.closest('.saved-item-delete')) {
                        showSavedMessageContent(savedItem);
                    }
                });
                
                savedList.appendChild(savedItemElement);
            });
        }
    }

    // Show saved message content
    function showSavedMessageContent(savedItem) {
        const welcomeScreen = document.getElementById('welcomeScreen') || 
                             document.querySelector('.welcome-screen');
        if (welcomeScreen && welcomeScreen.style.display !== 'none') {
            welcomeScreen.style.display = 'none';
            isFirstMessage = false;
        }
        
        addSavedMessageToChat(savedItem);
    }

    // Add saved message to chat
    function addSavedMessageToChat(savedItem) {
        if (!chatContent) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        messageDiv.id = `restored-${savedItem.id}`;
        
        messageDiv.innerHTML = `
            <div class="message-header">
                <div class="avatar bot-avatar" style="background: #9333EA;">📌</div>
                <span class="sender-name">Saved Message</span>
                <span style="font-size: 12px; color: var(--text-muted); margin-left: auto;">
                    Saved ${new Date(savedItem.timestamp).toLocaleDateString()}
                </span>
            </div>
            <div class="message-content">
                ${savedItem.fullContent || savedItem.preview}
            </div>
            <div class="message-actions">
                <button class="action-btn" onclick="copyMessage('restored-${savedItem.id}')" title="Copy">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2" stroke="currentColor" stroke-width="2"/>
                        <path d="M5 15H4C3.46957 15 2.96086 14.7893 2.58579 14.4142C2.21071 14.0391 2 13.5304 2 13V4C2 3.46957 2.21071 2.96086 2.58579 2.58579C2.96086 2.21071 3.46957 2 4 2H13C13.5304 2 14.0391 2.21071 14.4142 2.58579C14.7893 2.96086 15 3.46957 15 4V5" stroke="currentColor" stroke-width="2"/>
                    </svg>
                </button>
                <button class="action-btn" onclick="shareMessage('restored-${savedItem.id}')" title="Share">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M4 12V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V12" stroke="currentColor" stroke-width="2"/>
                        <polyline points="16,6 12,2 8,6" stroke="currentColor" stroke-width="2"/>
                        <line x1="12" y1="2" x2="12" y2="15" stroke="currentColor" stroke-width="2"/>
                    </svg>
                </button>
            </div>
        `;
        
        chatContent.appendChild(messageDiv);
        scrollToBottom();
        showToast('💾 Saved message restored to chat!');
    }
    
    // Remove saved message function
    window.removeSavedMessage = function(messageId) {
        if (savedMessages.has(messageId)) {
            savedMessages.delete(messageId);
            saveSavedMessages();
            updateSavedMessagesList();
            showToast('Message removed from saved items!');
        }
    };
    
    // Enhanced Send message function with session handling
    async function sendMessage() {
        // Check authentication before sending
        if (!serverUser.is_authenticated) {
            showAuthOverlay();
            showToast('Please login to continue');
            return;
        }
        
        const query = chatInput?.value.trim();
        if (!query) return;
        
        if (isFirstMessage) {
            const welcomeScreen = document.getElementById('welcomeScreen') || 
                                 document.querySelector('.welcome-screen');
            if (welcomeScreen) {
                welcomeScreen.style.display = 'none';
            }
            isFirstMessage = false;
        }
        
        addMessage('user', query);
        const loadingId = addLoadingMessage();
        
        if (chatInput) chatInput.value = '';
        if (sendButton) sendButton.disabled = true;
        
        try {
            const response = await fetch('/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query
                }),
            });
            
            // Handle authentication errors
            if (response.status === 401 || response.status === 403) {
                removeLoadingMessage(loadingId);
                showAuthOverlay();
                showToast('Session expired. Please login again.');
                if (sendButton) sendButton.disabled = false;
                return;
            }
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            removeLoadingMessage(loadingId);
            addBotResponse(data);
            
        } catch (error) {
            removeLoadingMessage(loadingId);
            
            // Handle network errors vs server errors
            let errorMessage = 'Sorry, I encountered an error. Please try again.';
            if (error.message.includes('Failed to fetch')) {
                errorMessage = 'Network error. Please check your connection and try again.';
            } else if (error.message.includes('401') || error.message.includes('403')) {
                showAuthOverlay();
                showToast('Session expired. Please login again.');
                if (sendButton) sendButton.disabled = false;
                return;
            }
            
            addMessage('bot', errorMessage);
            console.error('Send message error:', error);
        }
        
        if (sendButton) sendButton.disabled = false;
        if (chatInput) chatInput.focus();
    }
    
    function addMessage(sender, content) {
        if (!chatContent) return;
        
        const messageId = `message-${currentThreadId}-${Date.now()}`;
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        messageDiv.id = messageId;
        
        if (sender === 'user') {
            messageDiv.innerHTML = `
                <div class="message-content">
                    <p>${content}</p>
                </div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="message-header">
                    <div class="avatar bot-avatar">AI</div>
                    <span class="sender-name">DSA Mentor</span>
                </div>
                <div class="message-content">
                    <p>${content}</p>
                </div>
                <div class="message-actions">
                    <button class="action-btn" onclick="copyMessage('${messageId}')" title="Copy">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" stroke="currentColor" stroke-width="2"/>
                            <path d="M5 15H4C3.46957 15 2.96086 14.7893 2.58579 14.4142C2.21071 14.0391 2 13.5304 2 13V4C2 3.46957 2.21071 2.96086 2.58579 2.58579C2.96086 2.21071 3.46957 2 4 2H13C13.5304 2 14.0391 2.21071 14.4142 2.58579C14.7893 2.96086 15 3.46957 15 4V5" stroke="currentColor" stroke-width="2"/>
                        </svg>
                    </button>
                    <button class="action-btn" onclick="saveMessage('${messageId}')" title="Save for later">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M19 21L12 16L5 21V5C5 4.46957 5.21071 3.96086 5.58579 3.58579C5.96086 3.21071 6.46957 3 7 3H17C17.5304 3 18.0391 3.21071 18.4142 3.58579C18.7893 3.96086 19 4.46957 19 5V21Z" stroke="currentColor" stroke-width="2"/>
                        </svg>
                    </button>
                    <button class="action-btn" onclick="shareMessage('${messageId}')" title="Share">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M4 12V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V12" stroke="currentColor" stroke-width="2"/>
                            <polyline points="16,6 12,2 8,6" stroke="currentColor" stroke-width="2"/>
                            <line x1="12" y1="2" x2="12" y2="15" stroke="currentColor" stroke-width="2"/>
                        </svg>
                    </button>
                </div>
            `;
        }
        
        chatContent.appendChild(messageDiv);
        scrollToBottom();
    }
    
    function addBotResponse(data) {
        if (!chatContent) return;
        
        const messageId = `message-${currentThreadId}-${Date.now()}`;
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        messageDiv.id = messageId;
        
        let responseHTML = `
            <div class="message-header">
                <div class="avatar bot-avatar">AI</div>
                <span class="sender-name">DSA Mentor</span>
            </div>
            <div class="message-content">
        `;
        
        // Handle title from best_book
        if (data.best_book && data.best_book.title) {
            responseHTML += `<div class="concept-title">${data.best_book.title}</div>`;
        }
        
        // Handle content - prioritize summary, then best_book content
        if (data.summary) {
            responseHTML += `<div class="concept-explanation">${data.summary}</div>`;
        } else if (data.best_book && data.best_book.content) {
            // Format content properly
            let content = data.best_book.content;
            if (content.length > 500) {
                content = content.substring(0, 500) + '...';
            }
            responseHTML += `<div class="concept-explanation">${content}</div>`;
        }
        
        // Add complexity badges if content mentions complexity
        if (data.best_book && data.best_book.content && 
            (data.best_book.content.toLowerCase().includes("complexity") || 
             data.best_book.content.toLowerCase().includes("time") ||
             data.best_book.content.toLowerCase().includes("space"))) {
            responseHTML += `
                <div class="complexity-badges">
                    <span class="complexity-badge">Time Complexity Analysis</span>
                    <span class="complexity-badge">Space Complexity Analysis</span>
                </div>
            `;
        }
        
        // Add practice problems section
        if (data.top_dsa && data.top_dsa.length > 0) {
            responseHTML += `
                <div class="practice-problems">
                    <div class="section-header">📝 Related Practice Problems</div>
            `;
            
            data.top_dsa.forEach(problem => {
                responseHTML += `
                    <div class="problem-card">
                        <div class="problem-title">
                            <span class="problem-section">${problem.section || 'DSA'}:</span> ${problem.question}
                        </div>
                        <div class="problem-description">${problem.description || 'Practice this fundamental concept to strengthen your understanding.'}</div>
                        <div class="problem-links">
                            ${problem.article_link ? `<a href="${problem.article_link}" target="_blank" class="problem-link">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" stroke-width="2"/>
                                    <polyline points="14,2 14,8 20,8" stroke="currentColor" stroke-width="2"/>
                                </svg>
                                Article
                            </a>` : ''}
                            ${problem.practice_link ? `<a href="${problem.practice_link}" target="_blank" class="problem-link">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M9 12L11 14L15 10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" stroke-width="2"/>
                                </svg>
                                Practice
                            </a>` : ''}
                        </div>
                    </div>
                `;
            });
            
            responseHTML += `</div>`;
        }

        // Add video suggestions section
        if (data.video_suggestions && data.video_suggestions.length > 0) {
            responseHTML += `
                <div class="video-suggestions">
                    <div class="section-header">🎥 Recommended Video Tutorials</div>
            `;
            
            data.video_suggestions.forEach(video => {
                responseHTML += `
                    <div class="video-card">
                        <div class="video-header">
                            <div class="video-thumbnail">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <polygon points="5,3 19,12 5,21" fill="currentColor"/>
                                </svg>
                            </div>
                            <div class="video-info">
                                <div class="video-title">${video.title || 'Video Tutorial'}</div>
                                <div class="video-meta">
                                    <span>${video.topic || 'DSA'}</span>
                                    ${video.difficulty ? `<span class="video-difficulty">${video.difficulty}</span>` : ''}
                                    ${video.duration ? `<span>⏱️ ${video.duration}</span>` : ''}
                                </div>
                                <div class="video-description">${video.description || video.subtopic || 'Learn this concept through video tutorial'}</div>
                            </div>
                        </div>
                        <div class="video-actions">
                            ${video.video_url ? `<button class="video-btn" onclick="openVideoModal('${video.video_url}', '${video.title || 'Video Tutorial'}')">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <polygon points="5,3 19,12 5,21" fill="currentColor"/>
                                </svg>
                                Watch
                            </button>` : ''}
                            ${video.video_url ? `<a href="${video.video_url}" target="_blank" class="video-btn video-btn-secondary">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M18 13V6C18 5.46957 17.7893 4.96086 17.4142 4.58579C17.0391 4.21071 16.5304 4 16 4H4C3.46957 4 2.96086 4.21071 2.58579 4.58579C2.21071 4.96086 2 5.46957 2 6V18C2 18.5304 2.21071 19.0391 2.58579 19.4142C2.96086 19.7893 3.46957 20 4 20H16C16.5304 20 17.0391 19.7893 17.4142 19.4142C17.7893 19.0391 18 18.5304 18 18V15" stroke="currentColor" stroke-width="2"/>
                                    <polyline points="10,9 21,9 18,6" stroke="currentColor" stroke-width="2"/>
                                    <path d="M21 9V21" stroke="currentColor" stroke-width="2"/>
                                </svg>
                                Open
                            </a>` : ''}
                        </div>
                    </div>
                `;
            });
            
            responseHTML += `</div>`;
        }
        
        responseHTML += `
            </div>
            <div class="message-actions">
                <button class="action-btn" onclick="copyMessage('${messageId}')" title="Copy">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2" stroke="currentColor" stroke-width="2"/>
                        <path d="M5 15H4C3.46957 15 2.96086 14.7893 2.58579 14.4142C2.21071 14.0391 2 13.5304 2 13V4C2 3.46957 2.21071 2.96086 2.58579 2.58579C2.96086 2.21071 3.46957 2 4 2H13C13.5304 2 14.0391 2.21071 14.4142 2.58579C14.7893 2.96086 15 3.46957 15 4V5" stroke="currentColor" stroke-width="2"/>
                    </svg>
                </button>
                <button class="action-btn" onclick="saveMessage('${messageId}')" title="Save for later">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M19 21L12 16L5 21V5C5 4.46957 5.21071 3.96086 5.58579 3.58579C5.96086 3.21071 6.46957 3 7 3H17C17.5304 3 18.0391 3.21071 18.4142 3.58579C18.7893 3.96086 19 4.46957 19 5V21Z" stroke="currentColor" stroke-width="2"/>
                    </svg>
                </button>
                <button class="action-btn" onclick="shareMessage('${messageId}')" title="Share">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M4 12V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V12" stroke="currentColor" stroke-width="2"/>
                        <polyline points="16,6 12,2 8,6" stroke="currentColor" stroke-width="2"/>
                        <line x1="12" y1="2" x2="12" y2="15" stroke="currentColor" stroke-width="2"/>
                    </svg>
                </button>
            </div>
        `;
        
        messageDiv.innerHTML = responseHTML;
        chatContent.appendChild(messageDiv);
        scrollToBottom();
    }
      
    function addLoadingMessage() {
        if (!chatContent) return null;
        
        const loadingId = `loading-${Date.now()}`;
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        messageDiv.id = loadingId;
        
        messageDiv.innerHTML = `
          <div class="message-header">
            <div class="avatar bot-avatar">AI</div>
            <span class="sender-name">DSA Mentor</span>
          </div>
          <div class="message-content">
            <div class="loading-message">
              <div class="loading-dots">
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
              </div>
              <span>Thinking...</span>
            </div>
          </div>
        `;
        
        chatContent.appendChild(messageDiv);
        scrollToBottom();
        return loadingId;
    }
      
    function removeLoadingMessage(loadingId) {
        if (loadingId) {
            const loadingElement = document.getElementById(loadingId);
            if (loadingElement) {
                loadingElement.remove();
            }
        }
    }
      
    function scrollToBottom() {
        const chatArea = document.getElementById('chatArea');
        if (chatArea) {
            chatArea.scrollTop = chatArea.scrollHeight;
        }
    }

    // Message action functions
    window.copyMessage = function(messageId) {
        const messageElement = document.getElementById(messageId);
        if (messageElement) {
            const messageContent = messageElement.querySelector('.message-content')?.innerText;
            
            if (messageContent && navigator.clipboard) {
                navigator.clipboard.writeText(messageContent).then(() => {
                    showToast('Message copied to clipboard!');
                }).catch(err => {
                    console.error('Failed to copy: ', err);
                    showToast('Failed to copy message');
                });
            }
        }
    };

    // Save message function
    window.saveMessage = function(messageId) {
        const messageElement = document.getElementById(messageId);
        if (!messageElement) return;
        
        const saveBtn = messageElement.querySelector('.action-btn[onclick*="saveMessage"]');
        
        if (savedMessages.has(messageId)) {
            savedMessages.delete(messageId);
            if (saveBtn) saveBtn.classList.remove('saved');
            saveSavedMessages();
            updateSavedMessagesList();
            showToast('Message removed from saved items');
        } else {
            const messageContent = messageElement.querySelector('.message-content');
            if (messageContent) {
                const title = messageContent.querySelector('.concept-title')?.textContent || 'DSA Response';
                const preview = messageContent.innerText.substring(0, 100) + '...';
                const fullContent = messageContent.innerHTML;
                
                savedMessages.set(messageId, {
                    id: messageId,
                    title: title,
                    preview: preview,
                    fullContent: fullContent,
                    threadId: currentThreadId,
                    timestamp: new Date().toISOString()
                });
                
                if (saveBtn) saveBtn.classList.add('saved');
                saveSavedMessages();
                updateSavedMessagesList();
                showToast('Message saved for later!');
            }
        }
    };

    window.shareMessage = function(messageId) {
        const shareModal = document.getElementById('shareModal');
        if (shareModal) shareModal.classList.add('active');
    };

    // Download chat function
    function downloadChat() {
        const messages = document.querySelectorAll('.message');
        
        if (messages.length === 0) {
            showToast('No messages to download!');
            return;
        }
        
        const downloadBtn = document.getElementById('downloadBtn');
        if (!downloadBtn) return;
        
        const originalText = downloadBtn.innerHTML;
        downloadBtn.innerHTML = `
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
            <path d="M14 8l-4 4-2-2" stroke="currentColor" stroke-width="2"/>
          </svg>
        `;
        downloadBtn.disabled = true;
        
        let htmlContent = `
          <div class="pdf-container">
            <div class="pdf-header">
              <h1>DSA Mentor Chat Export</h1>
              <p>Generated on ${new Date().toLocaleDateString()}</p>
            </div>
            <div class="pdf-content">
        `;
        
        messages.forEach((message, index) => {
            if (message.id && message.id.startsWith('loading-')) return;
            
            if (message.classList.contains('user-message')) {
                const content = message.querySelector('.message-content')?.innerHTML;
                if (content) htmlContent += `<div class="message user-message">${content}</div>`;
            } else if (message.classList.contains('bot-message')) {
                const content = message.querySelector('.message-content')?.innerHTML;
                if (content) htmlContent += `<div class="message bot-message">${content}</div>`;
            }
        });
        
        htmlContent += `
            </div>
          </div>
        `;
        
        fetch('/generate-pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ html: htmlContent })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => Promise.reject(err));
            }
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `dsa-mentor-chat-${new Date().toISOString().split('T')[0]}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            showToast('📄 PDF downloaded successfully!');
        })
        .catch(error => {
            console.error('PDF Error:', error);
            showToast('❌ Error generating PDF. Please try again.');
        })
        .finally(() => {
            downloadBtn.innerHTML = originalText;
            downloadBtn.disabled = false;
        });
    }

    // Modal functions
    window.closeModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.remove('active');
    };

    window.copyShareLink = function() {
        const shareLink = document.getElementById('shareLink');
        if (shareLink && navigator.clipboard) {
            shareLink.select();
            navigator.clipboard.writeText(shareLink.value).then(() => {
                showToast('Share link copied to clipboard!');
                closeModal('shareModal');
            }).catch(err => {
                console.error('Failed to copy share link: ', err);
                showToast('Failed to copy share link');
            });
        }
    };

    // Toast notification
    function showToast(message) {
        const toast = document.getElementById('toast');
        if (toast) {
            toast.textContent = message;
            toast.classList.add('show');
            
            setTimeout(() => {
                toast.classList.remove('show');
            }, 3000);
        }
    }

    // Close modals when clicking outside
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal-overlay')) {
            e.target.classList.remove('active');
        }
        if (e.target.classList.contains('video-modal')) {
            closeVideoModal();
        }
    });
    
    // Event listeners
    if (sendButton) {
        sendButton.addEventListener('click', sendMessage);
    }
    
    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
    
    // Initialize
    loadSavedMessages();
    if (serverUser && serverUser.is_authenticated && chatInput) {
        chatInput.focus();
    }
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', function() {
        stopPeriodicAuthCheck();
    });
});