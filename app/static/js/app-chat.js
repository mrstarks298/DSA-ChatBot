// ===== DSA MENTOR - UPDATED CHAT SYSTEM =====
(() => {
  'use strict';

  // ===== DEPENDENCY CHECK =====
  if (!window.app || !window.app.state || !window.app.util || !window.app.render) {
    console.error('❌ Required app modules not found. Load app-auth.js first.');
    return;
  }

  // ===== DESTRUCTURE DEPENDENCIES =====
  const $ = (id) => document.getElementById(id);
  const { state, util, auth, render, saved, storage } = window.app;
  const { showToast, updateShareLink, formatError, debounce, scrollToBottom } = util;

  // ===== DOM ELEMENTS =====
  const chatInput = $('chatInput');
  const sendButton = $('sendButton');
  const downloadBtn = $('downloadBtn');
  const shareBtn = $('shareBtn');
  const clearSavedBtn = $('clearSavedBtn');

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
      if ($('scrollToBottomBtn')) return;

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
      const debouncedUpdate = debounce(() => {
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
        // Small delay to ensure content is rendered
        setTimeout(() => this.scrollToBottom(), 50);
      }
    }
  };
  // ===== CORE CHAT FUNCTIONALITY =====
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
    
    // Main send message function
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
                        // Authentication required
                        window.app.auth.showAuthOverlay();
                        addMessageToChat('assistant', 'Please sign in to continue our conversation.');
                        return;
                    }
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                console.log('Received response:', data);
                
                // Add bot response
                const botMessage = data.response || data.best_book?.content || 'Sorry, I could not process your request.';
                addMessageToChat('assistant', botMessage);
                
                // Add additional content if available
                if (data.best_book && data.best_book.content && data.best_book.content !== botMessage) {
                    addMessageToChat('assistant', data.best_book.content);
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
            if (window.showToast) {
                window.showToast('An unexpected error occurred', 'error');
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
    
    // Helper function to add messages to chat
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
                <div class="message-actions">
                    <button class="action-btn copy-btn" onclick="copyMessage('${messageId}')" title="Copy message">
                        📋
                    </button>
                    ${sender === 'assistant' ? `<button class="action-btn save-btn" onclick="saveMessage('${messageId}')" title="Save message">💾</button>` : ''}
                </div>
            </div>
        `;
        
        chatContent.appendChild(messageDiv);
        
        // Smooth scroll to new message
        setTimeout(() => {
            messageDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);
        
        return messageId;
    }
    
    // Helper function to add typing indicator
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
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        
        chatContent.appendChild(typingDiv);
        
        setTimeout(() => {
            typingDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);
        
        return typingId;
    }
    
    // Helper function to remove typing indicator
    function removeTypingIndicator(typingId) {
        if (typingId) {
            const typingElement = document.getElementById(typingId);
            if (typingElement) {
                typingElement.remove();
            }
        }
    }
    
    // Helper function to escape HTML
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Global helper functions
    window.copyMessage = function(messageId) {
        const messageElement = document.getElementById(messageId);
        if (messageElement) {
            const textElement = messageElement.querySelector('.message-text');
            if (textElement) {
                navigator.clipboard.writeText(textElement.textContent).then(() => {
                    if (window.showToast) {
                        window.showToast('Message copied!', 'success');
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
    
    console.log('✅ Chat core functionality loaded');
})();

 
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
      // Set up the target with the complete structure but empty text
      target.innerHTML = source.innerHTML;
      
      const textNodes = this.getTextNodes(target);
      const totalLength = textNodes.reduce((sum, node) => sum + node.textContent.length, 0);
      let processedLength = 0;
      
      // Clear all text content initially
      textNodes.forEach(node => {
        const originalText = node.textContent;
        node.textContent = '';
        node.setAttribute('data-original-text', originalText);
      });

      // Animate each text node sequentially
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
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        .replace(/^(.*)$/gm, '<p>$1</p>')
        .replace(/<p><\/p>/g, '');
    },

    stopAll() {
      this.activeAnimations.clear();
    }
  };

  // ===== ENHANCED RESPONSE RENDERER =====
  const EnhancedRenderer = {
    async renderBotResponse(data, messageId) {
      const messageElement = $(messageId);
      if (!messageElement) return;

      const contentElement = messageElement.querySelector('.message-content');
      if (!contentElement) return;

      // Show typing indicator
      this.showTypingIndicator(contentElement);
      
      // Wait a bit for dramatic effect
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Stream the response content
      await this.streamResponseContent(contentElement, data);
    },

    showTypingIndicator(element) {
      element.innerHTML = `
        <div class="typing-indicator">
          <span>DSA Mentor is thinking</span>
          <div class="typing-dots">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
          </div>
        </div>
      `;
      ScrollManager.onNewContent();
    },

    async streamResponseContent(element, data) {
      try {
        let content = '';
        
        // Build the response content
        if (data.best_book && data.best_book.content) {
          content += `# ${data.best_book.title || 'DSA Insights'}\n\n`;
          content += data.best_book.content;
        }

        if (data.top_dsa && data.top_dsa.length > 0) {
          content += '\n\n## 📚 Related Resources\n\n';
          data.top_dsa.forEach((item, index) => {
            if (item.question) {
              content += `**${index + 1}. ${item.question}**\n`;
              if (item.article_link) {
                content += `[📖 Learn More](${item.article_link}) `;
              }
              if (item.practice_link) {
                content += `[💻 Practice](${item.practice_link})`;
              }
              content += '\n\n';
            }
          });
        }

        if (data.video_suggestions && data.video_suggestions.length > 0) {
          content += '\n\n## 🎥 Video Tutorials\n\n';
          data.video_suggestions.forEach((video, index) => {
            content += `**${index + 1}. ${video.title}**\n`;
            content += `${video.description}\n`;
            content += `Duration: ${video.duration} | Difficulty: ${video.difficulty}\n`;
            if (video.embed_url && video.embed_url !== '#') {
              content += `[🎬 Watch Video](${video.video_url})\n`;
            }
            content += '\n';
          });
        }

        if (data.summary) {
          content += `\n\n---\n\n*${data.summary}*`;
        }

        if (!content.trim()) {
          content = "I'm here to help with your DSA questions! Please feel free to ask about any data structures or algorithms topic.";
        }

        // Stream write the content
        await StreamingWriter.writeText(element, content, {
          speed: 12,
          enableMarkdown: true,
          onProgress: (progress) => {
            ScrollManager.onNewContent();
          }
        });

        // Add interactive elements if needed
        this.addInteractiveElements(element, data);

      } catch (error) {
        console.error('Error streaming response:', error);
        element.innerHTML = `
          <div class="error-message">
            <p>Sorry, I encountered an error while processing your request.</p>
            <p>Please try asking your question again.</p>
          </div>
        `;
      }
    },

    addInteractiveElements(element, data) {
      // Add video buttons
      if (data.video_suggestions && data.video_suggestions.length > 0) {
        const videoLinks = element.querySelectorAll('a[href*="youtube"], a[href*="youtu.be"]');
        videoLinks.forEach((link, index) => {
          const video = data.video_suggestions[index];
          if (video && video.embed_url && video.embed_url !== '#') {
            link.addEventListener('click', (e) => {
              e.preventDefault();
              this.openVideoModal(video);
            });
          }
        });
      }

      ScrollManager.onNewContent();
    },

    openVideoModal(video) {
      const modal = $('videoModal');
      const title = $('videoModalTitle');
      const embed = $('videoEmbed');

      if (modal && title && embed) {
        title.textContent = video.title;
        embed.src = video.embed_url;
        modal.classList.add('active');
        
        // Focus management
        setTimeout(() => {
          const closeBtn = modal.querySelector('.video-modal-close');
          if (closeBtn) closeBtn.focus();
        }, 100);
      }
    }
  };

  // ===== MESSAGE SENDING SYSTEM =====
  const MessageSender = {
    isSending: false,

    async sendMessage() {
      const query = chatInput?.value?.trim();
      if (!query || this.isSending || sendButton?.disabled) {
        return;
      }

      // Check authentication
      if (!auth.isAuthenticated()) {
        showToast('Please sign in to start chatting', 'warning');
        return;
      }

      this.isSending = true;
      this.disableInput();

      try {
        // Hide welcome screen on first message
        if (state.isFirstMessage) {
          const welcomeScreen = $('welcomeScreen');
          if (welcomeScreen) {
            welcomeScreen.style.display = 'none';
          }
          state.isFirstMessage = false;
        }

        // Add user message
        render.addMessage('user', query);
        chatInput.value = '';
        ScrollManager.onNewContent();

        // Create bot message placeholder
        const messageId = `msg-${Date.now()}`;
        render.addBotMessage('', messageId);

        // Prepare payload
        const payload = {
          query: query,
          thread_id: state.currentThreadId
        };

        // Try streaming first, fallback to JSON
        let response = await this.attemptStreamingRequest(payload);
        
        if (response.status === 404) {
          response = await this.attemptJSONRequest(payload);
        }

        if (!response.ok) {
          throw new Error(`Server error: ${response.status}`);
        }

        // Handle the response
        await this.handleResponse(response, messageId);

      } catch (error) {
        console.error('Send message error:', error);
        this.handleSendError(error, messageId);
      } finally {
        this.isSending = false;
        this.enableInput();
      }
    },

    async attemptStreamingRequest(payload) {
      return fetch('/query-stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream, application/json'
        },
        body: JSON.stringify(payload),
        credentials: 'same-origin'
      });
    },

    async attemptJSONRequest(payload) {
      return fetch('/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(payload),
        credentials: 'same-origin'
      });
    },

    async handleResponse(response, messageId) {
      const contentType = response.headers.get('content-type') || '';
      const placeholder = $(messageId)?.querySelector('.message-content');

      if (!placeholder) {
        throw new Error('Message placeholder not found');
      }

      if (contentType.includes('text/event-stream') && response.body) {
        await this.handleStreamingResponse(response, placeholder, messageId);
      } else {
        const data = await response.json();
        if (data.thread_id) {
          state.currentThreadId = data.thread_id;
          updateShareLink(state.currentThreadId);
        }
        await EnhancedRenderer.renderBotResponse(data, messageId);
      }
    },

    async handleStreamingResponse(response, placeholder, messageId) {
      EnhancedRenderer.showTypingIndicator(placeholder);
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let finalJson = null;
      let hasStartedStreaming = false;

      const appendText = (text) => {
        if (!hasStartedStreaming) {
          placeholder.innerHTML = '<p></p>';
          hasStartedStreaming = true;
        }
        
        const contentElement = placeholder.querySelector('p');
        if (contentElement) {
          contentElement.innerHTML += this.escapeHtml(text);
          ScrollManager.onNewContent();
        }
      };

      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const events = buffer.split('\n\n');
          buffer = events.pop() || '';

          for (const eventString of events) {
            const event = this.parseSSEEvent(eventString);
            if (!event) continue;

            switch (event.name) {
              case 'chunk':
                try {
                  const chunkData = JSON.parse(event.data);
                  if (chunkData.text) {
                    appendText(chunkData.text);
                  }
                } catch {
                  appendText(event.data);
                }
                break;

              case 'final_json':
                try {
                  finalJson = JSON.parse(event.data);
                } catch (error) {
                  console.error('Failed to parse final JSON:', error);
                }
                break;

              case 'meta':
                try {
                  const meta = JSON.parse(event.data);
                  if (meta.thread_id) {
                    state.currentThreadId = meta.thread_id;
                    updateShareLink(state.currentThreadId);
                  }
                } catch (error) {
                  console.error('Failed to parse meta:', error);
                }
                break;

              case 'error':
                throw new Error(event.data);
            }
          }
        }

        // Render final response if available
        if (finalJson) {
          await EnhancedRenderer.renderBotResponse(finalJson, messageId);
        }

      } catch (error) {
        console.error('Streaming error:', error);
        throw error;
      }
    },

    parseSSEEvent(eventString) {
      const lines = eventString.split('\n');
      let eventName = 'message';
      let data = '';

      for (const line of lines) {
        if (line.startsWith('event:')) {
          eventName = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          data += line.slice(5).trim();
        }
      }

      return data ? { name: eventName, data } : null;
    },

    escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    },

    handleSendError(error, messageId) {
      const messageElement = $(messageId);
      if (!messageElement) return;

      const content = messageElement.querySelector('.message-content');
      if (!content) return;

      let errorMessage = 'Sorry, I encountered an error processing your request.';
      
      if (error.message.includes('401')) {
        errorMessage = 'Your session has expired. Please sign in again.';
        // Trigger auth check
        auth.performAuthCheck(true);
      } else if (error.message.includes('400')) {
        errorMessage = 'Your message was invalid. Please try rephrasing it.';
      } else if (error.message.includes('500')) {
        errorMessage = 'Server error. Please try again in a moment.';
      } else if (error.message.includes('timeout')) {
        errorMessage = 'Request timed out. Please try again.';
      }

      content.innerHTML = `
        <div class="error-message">
          <div class="error-icon">⚠️</div>
          <div class="error-text">${errorMessage}</div>
          <button onclick="MessageSender.retryLastMessage()" class="retry-btn">Try Again</button>
        </div>
      `;

      showToast('Message failed to send', 'error');
    },

    retryLastMessage() {
      if (chatInput && !this.isSending) {
        chatInput.focus();
        showToast('Please try sending your message again', 'info');
      }
    },

    disableInput() {
      if (sendButton) {
        sendButton.disabled = true;
        sendButton.textContent = 'Sending...';
      }
      
      if (chatInput) {
        chatInput.disabled = true;
        chatInput.style.opacity = '0.7';
      }
    },

    enableInput() {
      if (sendButton) {
        sendButton.disabled = false;
        sendButton.innerHTML = '<span>Send</span><span>🚀</span>';
      }
      
      if (chatInput) {
        chatInput.disabled = false;
        chatInput.style.opacity = '1';
        chatInput.focus();
      }
    }
  };

  // ===== INPUT HANDLING =====
  const InputManager = {
    init() {
      this.setupChatInput();
      this.setupSendButton();
      this.setupAutoResize();
    },

    setupChatInput() {
      if (!chatInput) return;

      // Enter key handling
      chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
          e.preventDefault();
          MessageSender.sendMessage();
        }
      });

      // Input validation
      chatInput.addEventListener('input', (e) => {
        const value = e.target.value;
        const maxLength = state.config.maxQueryLength || 2000;
        
        if (value.length > maxLength) {
          e.target.value = value.substring(0, maxLength);
          showToast(`Message truncated to ${maxLength} characters`, 'warning');
        }
        
        this.updateSendButton();
      });

      // Paste handling
      chatInput.addEventListener('paste', (e) => {
        setTimeout(() => this.updateSendButton(), 10);
      });
    },

    setupSendButton() {
      if (!sendButton) return;

      sendButton.addEventListener('click', () => {
        MessageSender.sendMessage();
      });
    },

    setupAutoResize() {
      if (!chatInput) return;

      const autoResize = () => {
        chatInput.style.height = 'auto';
        const newHeight = Math.min(chatInput.scrollHeight, 120);
        chatInput.style.height = newHeight + 'px';
      };

      chatInput.addEventListener('input', autoResize);
      chatInput.addEventListener('paste', () => setTimeout(autoResize, 10));

      // Initial resize
      autoResize();
    },

    updateSendButton() {
      if (!sendButton || !chatInput) return;

      const hasText = chatInput.value.trim().length > 0;
      const isAuthenticated = auth.isAuthenticated();
      
      sendButton.disabled = !hasText || !isAuthenticated || MessageSender.isSending;
    }
  };

  // ===== EXPORT & SHARE FUNCTIONALITY =====
  const ExportManager = {
    init() {
      this.setupDownloadButton();
      this.setupShareButton();
    },

    setupDownloadButton() {
      if (!downloadBtn) return;

      downloadBtn.addEventListener('click', () => {
        this.exportChat();
      });
    },

    setupShareButton() {
      if (!shareBtn) return;

      shareBtn.addEventListener('click', () => {
        this.shareChat();
      });
    },

    async exportChat() {
      try {
        const chatContent = $('chatContent');
        if (!chatContent) return;

        const messages = Array.from(chatContent.querySelectorAll('.message')).map(msg => {
          const isUser = msg.classList.contains('user-message');
          const content = msg.querySelector('.message-content')?.textContent || '';
          return {
            sender: isUser ? 'user' : 'assistant',
            content: content,
            timestamp: new Date().toISOString()
          };
        });

        if (messages.length === 0) {
          showToast('No messages to export', 'warning');
          return;
        }

        const exportData = {
          title: `DSA Mentor Chat - ${new Date().toLocaleDateString()}`,
          messages: messages,
          threadId: state.currentThreadId,
          exportedAt: new Date().toISOString()
        };

        const blob = new Blob([JSON.stringify(exportData, null, 2)], {
          type: 'application/json'
        });

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dsa-mentor-chat-${Date.now()}.json`;
        a.click();

        URL.revokeObjectURL(url);
        showToast('Chat exported successfully', 'success');

      } catch (error) {
        console.error('Export error:', error);
        showToast('Export failed', 'error');
      }
    },

    shareChat() {
      const shareModal = $('shareModal');
      const shareLink = $('shareLink');
      
      if (shareModal && shareLink) {
        updateShareLink(state.currentThreadId);
        shareModal.classList.add('active');
        
        // Focus management
        setTimeout(() => {
          shareLink.focus();
          shareLink.select();
        }, 100);
      }
    }
  };

  // ===== GLOBAL MESSAGE SENDER =====
  window.sendMessage = MessageSender.sendMessage.bind(MessageSender);

  // ===== SUGGESTION HANDLER =====
  window.sendSuggestion = function(text) {
    if (chatInput && auth.isAuthenticated()) {
      chatInput.value = text;
      chatInput.focus();
      MessageSender.sendMessage();
    } else if (!auth.isAuthenticated()) {
      showToast('Please sign in to start chatting', 'warning');
    }
  };

  // ===== MODAL HANDLERS =====
  window.closeShareModal = function() {
    const modal = $('shareModal');
    if (modal) modal.classList.remove('active');
  };

  window.copyShareLink = function() {
    const shareLink = $('shareLink');
    if (shareLink) {
      shareLink.select();
      
      try {
        document.execCommand('copy');
        showToast('Link copied to clipboard!', 'success');
        closeShareModal();
      } catch (error) {
        console.error('Copy failed:', error);
        showToast('Copy failed. Please copy the link manually.', 'warning');
      }
    }
  };

  window.closeVideoModal = function() {
    const modal = $('videoModal');
    const embed = $('videoEmbed');
    
    if (modal) modal.classList.remove('active');
    if (embed) embed.src = '';
  };

  // ===== INITIALIZATION =====
  document.addEventListener('DOMContentLoaded', () => {
    // Wait for auth system to be ready
    const initChat = () => {
      if (!state.isInitialized) {
        setTimeout(initChat, 100);
        return;
      }

      try {
        console.log('🎯 Initializing chat system...');
        
        ScrollManager.init();
        InputManager.init();
        ExportManager.init();
        
        // Set up periodic input state updates
        setInterval(() => {
          InputManager.updateSendButton();
        }, 1000);

        console.log('✅ Chat system initialized');
        
      } catch (error) {
        console.error('❌ Chat system initialization failed:', error);
      }
    };

    initChat();
  });

  // ===== KEYBOARD SHORTCUTS =====
  document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + Enter to send message
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      MessageSender.sendMessage();
    }
    
    // Escape to close modals
    if (e.key === 'Escape') {
      closeVideoModal();
      closeShareModal();
    }
  });

  // ===== CLEANUP =====
  window.addEventListener('beforeunload', () => {
    StreamingWriter.stopAll();
  });

})();
