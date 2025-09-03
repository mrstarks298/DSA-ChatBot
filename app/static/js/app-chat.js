// ===== DSA MENTOR - CHAT SYSTEM =====
(() => {
    'use strict';

    // Wait for app modules to be ready
    function waitForApp() {
        return new Promise((resolve) => {
            const checkApp = () => {
                if (window.app && window.app.state && window.app.auth) {
                    resolve();
                } else {
                    setTimeout(checkApp, 100);
                }
            };
            checkApp();
        });
    }

    // ===== SCROLL MANAGER =====
    const ScrollManager = {
        autoScrollEnabled: true,
        scrollThreshold: 100,
        scrollButton: null,

        init() {
            this.createScrollButton();
            this.attachScrollListeners();
        },

        createScrollButton() {
            if (document.getElementById('scrollToBottomBtn')) return;

            const scrollBtn = document.createElement('button');
            scrollBtn.id = 'scrollToBottomBtn';
            scrollBtn.className = 'scroll-to-bottom-btn';
            scrollBtn.innerHTML = '↓';
            scrollBtn.title = 'Scroll to bottom';
            scrollBtn.setAttribute('aria-label', 'Scroll to bottom of chat');
            
            scrollBtn.addEventListener('click', () => {
                this.scrollToBottom(true);
            });

            document.body.appendChild(scrollBtn);
            this.scrollButton = scrollBtn;
        },

        attachScrollListeners() {
            const debouncedUpdate = this.debounce(() => {
                this.updateScrollButton();
                this.updateAutoScrollState();
            }, 100);

            window.addEventListener('scroll', debouncedUpdate);
            window.addEventListener('resize', debouncedUpdate);
        },

        updateScrollButton() {
            if (!this.scrollButton) return;
            const isNearBottom = this.isNearBottom();
            this.scrollButton.classList.toggle('visible', !isNearBottom);
        },

        updateAutoScrollState() {
            this.autoScrollEnabled = this.isNearBottom();
        },

        isNearBottom() {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            const windowHeight = window.innerHeight;
            const documentHeight = document.documentElement.scrollHeight;
            return documentHeight - (scrollTop + windowHeight) < this.scrollThreshold;
        },

        scrollToBottom(force = false) {
            if (force || this.autoScrollEnabled) {
                window.scrollTo({
                    top: document.documentElement.scrollHeight,
                    behavior: 'smooth'
                });
                this.autoScrollEnabled = true;
            }
        },

        onNewContent() {
            if (this.autoScrollEnabled) {
                setTimeout(() => this.scrollToBottom(), 50);
            }
        },

        debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        }
    };

    // ===== STREAMING RESPONSE WRITER =====
    const StreamingWriter = {
        activeAnimations: new Set(),

        async writeText(element, text, options = {}) {
            const { 
                speed = 15, 
                enableMarkdown = true, 
                onComplete = null, 
                onProgress = null 
            } = options;

            const animationId = `${Date.now()}_${Math.random()}`;
            this.activeAnimations.add(animationId);

            try {
                element.innerHTML = '';

                if (enableMarkdown) {
                    await this.writeMarkdown(element, text, speed, animationId, onProgress);
                } else {
                    await this.writePlain(element, text, speed, animationId, onProgress);
                }

                if (onComplete) onComplete();
            } catch (error) {
                console.error('Streaming write error:', error);
            } finally {
                this.activeAnimations.delete(animationId);
            }
        },

        async writePlain(element, text, speed, animationId, onProgress) {
            return new Promise((resolve) => {
                let index = 0;
                const writeChar = () => {
                    if (!this.activeAnimations.has(animationId)) {
                        return resolve();
                    }

                    if (index < text.length) {
                        element.textContent += text[index++];
                        ScrollManager.onNewContent();
                        
                        if (onProgress) {
                            onProgress(index / text.length);
                        }
                        
                        setTimeout(writeChar, speed);
                    } else {
                        resolve();
                    }
                };
                writeChar();
            });
        },

        async writeMarkdown(element, text, speed, animationId, onProgress) {
            const html = this.markdownToHtml(text);
            const tempElement = document.createElement('div');
            tempElement.innerHTML = html;
            await this.streamHTML(element, tempElement, speed, animationId, onProgress);
        },

        async streamHTML(target, source, speed, animationId, onProgress) {
            target.innerHTML = source.innerHTML;
            const textNodes = this.getTextNodes(target);
            const totalLength = textNodes.reduce((sum, node) => sum + node.textContent.length, 0);
            let processedLength = 0;

            textNodes.forEach(node => {
                const originalText = node.textContent;
                node.textContent = '';
                node.setAttribute('data-original-text', originalText);
            });

            for (const node of textNodes) {
                if (!this.activeAnimations.has(animationId)) break;

                const originalText = node.getAttribute('data-original-text');
                if (originalText) {
                    await this.animateTextNode(node, originalText, speed, animationId);
                    processedLength += originalText.length;
                    
                    if (onProgress) {
                        onProgress(processedLength / totalLength);
                    }
                }
            }
        },

        async animateTextNode(node, text, speed, animationId) {
            return new Promise((resolve) => {
                let index = 0;
                const writeChar = () => {
                    if (!this.activeAnimations.has(animationId) || index >= text.length) {
                        return resolve();
                    }

                    node.textContent += text[index++];
                    
                    if (index % 5 === 0) {
                        ScrollManager.onNewContent();
                    }
                    
                    setTimeout(writeChar, speed);
                };
                writeChar();
            });
        },

        getTextNodes(element) {
            const nodes = [];
            const walker = document.createTreeWalker(
                element,
                NodeFilter.SHOW_TEXT,
                node => node.textContent.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT,
                false
            );
            
            let node;
            while (node = walker.nextNode()) {
                nodes.push(node);
            }
            return nodes;
        },

        markdownToHtml(text) {
            return text
                .replace(/\*\*([\s\S]*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*([\s\S]*?)\*/g, '<em>$1</em>')
                .replace(/`([\s\S]*?)`/g, '<code>$1</code>')
                .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
                .replace(/^### (.*$)/gim, '<h3>$1</h3>')
                .replace(/^## (.*$)/gim, '<h2>$1</h2>')
                .replace(/^# (.*$)/gim, '<h1>$1</h1>')
                .replace(/\n/g, '<br>')
                .replace(/^(.*)$/gm, '<p>$1</p>')
                .replace(/<p><\/p>/g, '');
        },

        stopAll() {
            this.activeAnimations.clear();
        }
    };

    // ===== MAIN SEND MESSAGE FUNCTION =====
    window.sendMessage = async function() {
        try {
            await waitForApp();
            
            const chatInput = document.getElementById('chatInput');
            const sendButton = document.getElementById('sendButton');
            
            if (!chatInput || !sendButton) {
                console.error('Chat elements not found');
                return;
            }

            const message = chatInput.value.trim();
            if (!message) {
                console.warn('Empty message, not sending');
                return;
            }

            // Check authentication
            if (!window.app.auth.isAuthenticated()) {
                console.log('User not authenticated, showing auth overlay');
                window.app.auth.showAuthOverlay();
                return;
            }

            console.log('Sending message:', message);

            // Disable input while sending
            sendButton.disabled = true;
            chatInput.disabled = true;
            sendButton.textContent = 'Sending...';

            // Add user message to chat
            addMessageToChat('user', message);
            chatInput.value = '';

            // Show typing indicator
            const typingId = addTypingIndicator();

            try {
                // Send to backend
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({ query: message })
                });

                // Remove typing indicator
                removeTypingIndicator(typingId);

                if (!response.ok) {
                    if (response.status === 401) {
                        window.app.auth.showAuthOverlay();
                        addMessageToChat('assistant', 'Please sign in to continue our conversation.');
                        return;
                    }
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                console.log('Received response:', data);

                // Add bot response with streaming
                const botMessage = data.response || data.best_book?.content || 'Sorry, I could not process your request.';
                const messageId = addMessageToChat('assistant', '');
                await streamBotResponse(messageId, botMessage);

                // Add additional content if available
                if (data.video_suggestions && data.video_suggestions.length > 0) {
                    addVideoSuggestions(data.video_suggestions);
                }

            } catch (error) {
                console.error('Send message error:', error);
                removeTypingIndicator(typingId);
                
                let errorMessage = 'Sorry, there was an error processing your request. Please try again.';
                
                if (error.message.includes('401')) {
                    errorMessage = 'Please sign in to continue our conversation.';
                    window.app.auth.showAuthOverlay();
                } else if (error.message.includes('fetch')) {
                    errorMessage = 'Network error. Please check your connection and try again.';
                }

                addMessageToChat('assistant', errorMessage);
                
                if (window.app && window.app.util && window.app.util.showToast) {
                    window.app.util.showToast('Failed to send message', 'error');
                }
            }

        } catch (error) {
            console.error('Critical send message error:', error);
            if (window.app && window.app.util && window.app.util.showToast) {
                window.app.util.showToast('An unexpected error occurred', 'error');
            }
        } finally {
            // Re-enable input
            const chatInput = document.getElementById('chatInput');
            const sendButton = document.getElementById('sendButton');
            
            if (sendButton) {
                sendButton.disabled = false;
                sendButton.textContent = 'Send';
            }
            
            if (chatInput) {
                chatInput.disabled = false;
                chatInput.focus();
            }
        }
    };

    // ===== HELPER FUNCTIONS =====
    function addMessageToChat(sender, content) {
        const chatContent = document.getElementById('chatContent');
        const welcomeScreen = document.getElementById('welcomeScreen');

        // Hide welcome screen on first message
        if (welcomeScreen && sender === 'user') {
            welcomeScreen.style.display = 'none';
        }

        if (!chatContent) {
            console.error('Chat content element not found');
            return;
        }

        const messageId = `message_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const messageDiv = document.createElement('div');
        messageDiv.id = messageId;
        messageDiv.className = `message ${sender}-message`;
        
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-text">${escapeHtml(content)}</div>
                ${sender === 'assistant' ? `
                    <div class="message-actions">
                        <button onclick="copyMessage('${messageId}')" class="action-btn" title="Copy">
                            📋
                        </button>
                        <button onclick="saveMessage('${messageId}')" class="action-btn" title="Save">
                            💾
                        </button>
                    </div>
                ` : ''}
            </div>
        `;

        chatContent.appendChild(messageDiv);

        // Smooth scroll to new message
        setTimeout(() => {
            messageDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);

        return messageId;
    }

    function addTypingIndicator() {
        const typingId = `typing_${Date.now()}`;
        const chatContent = document.getElementById('chatContent');
        
        if (!chatContent) return null;

        const typingDiv = document.createElement('div');
        typingDiv.id = typingId;
        typingDiv.className = 'message assistant-message typing-message';
        typingDiv.innerHTML = `
            <div class="message-content">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;

        chatContent.appendChild(typingDiv);
        
        setTimeout(() => {
            typingDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);

        return typingId;
    }

    function removeTypingIndicator(typingId) {
        if (typingId) {
            const typingElement = document.getElementById(typingId);
            if (typingElement) {
                typingElement.remove();
            }
        }
    }

    async function streamBotResponse(messageId, content) {
        const messageElement = document.getElementById(messageId);
        if (!messageElement) return;

        const textElement = messageElement.querySelector('.message-text');
        if (!textElement) return;

        await StreamingWriter.writeText(textElement, content, {
            speed: 20,
            enableMarkdown: true,
            onProgress: (progress) => {
                // Optional: show progress indicator
            },
            onComplete: () => {
                ScrollManager.onNewContent();
            }
        });
    }

    function addVideoSuggestions(videos) {
        if (!videos || videos.length === 0) return;

        const chatContent = document.getElementById('chatContent');
        if (!chatContent) return;

        const videoContainer = document.createElement('div');
        videoContainer.className = 'video-suggestions';
        videoContainer.innerHTML = `
            <h3>Related Videos</h3>
            <div class="video-grid">
                ${videos.slice(0, 3).map(video => `
                    <div class="video-card" onclick="openVideoModal('${video.embed_url}', '${escapeHtml(video.title)}')">
                        <img src="${video.thumbnail_url}" alt="${escapeHtml(video.title)}" loading="lazy">
                        <div class="video-info">
                            <h4>${escapeHtml(video.title)}</h4>
                            <p>${escapeHtml(video.description)}</p>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        chatContent.appendChild(videoContainer);
        ScrollManager.onNewContent();
    }

    function escapeHtml(text) {
        if (!text) return '';
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // ===== GLOBAL HELPER FUNCTIONS =====
    window.copyMessage = function(messageId) {
        const messageElement = document.getElementById(messageId);
        if (messageElement) {
            const textElement = messageElement.querySelector('.message-text');
            if (textElement) {
                navigator.clipboard.writeText(textElement.textContent).then(() => {
                    if (window.app && window.app.util && window.app.util.showToast) {
                        window.app.util.showToast('Message copied!', 'success');
                    }
                }).catch(err => {
                    console.error('Copy failed:', err);
                });
            }
        }
    };

    window.saveMessage = function(messageId) {
        const messageElement = document.getElementById(messageId);
        if (messageElement && window.app && window.app.saved) {
            const textElement = messageElement.querySelector('.message-text');
            if (textElement) {
                const content = textElement.textContent;
                const title = content.substring(0, 50) + (content.length > 50 ? '...' : '');
                window.app.saved.saveMessage(messageId, content, title);
            }
        }
    };

    window.openVideoModal = function(embedUrl, title) {
        const modal = document.getElementById('videoModal');
        const embed = document.getElementById('videoEmbed');
        const titleElement = document.getElementById('videoTitle');
        
        if (modal && embed) {
            embed.src = embedUrl;
            if (titleElement) {
                titleElement.textContent = title;
            }
            modal.classList.add('active');
        }
    };

    // ===== INITIALIZATION =====
    function initializeChatSystem() {
        console.log('🚀 Initializing DSA Mentor Chat System...');
        
        ScrollManager.init();
        
        // Set up auto-resize for textarea
        const textarea = document.getElementById('chatInput');
        if (textarea) {
            const autoResize = () => {
                textarea.style.height = 'auto';
                const newHeight = Math.min(textarea.scrollHeight, 120);
                textarea.style.height = newHeight + 'px';
            };

            textarea.addEventListener('input', autoResize);
            textarea.addEventListener('paste', () => setTimeout(autoResize, 10));

            // Enter key handler
            textarea.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
                    e.preventDefault();
                    if (window.sendMessage && !textarea.disabled) {
                        window.sendMessage();
                    }
                }
            });

            autoResize();
        }
        
        console.log('✅ Chat system initialized');
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeChatSystem);
    } else {
        initializeChatSystem();
    }

})();