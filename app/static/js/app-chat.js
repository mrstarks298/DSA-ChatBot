// ===== app-chat.js =====
(() => {
  'use strict';

  // Check for required dependencies
  if (!window.app || !window.app.state || !window.app.util || !window.app.render) {
    console.error('Required app modules not found. Load app-auth.js first.');
    return;
  }

  const $ = (id) => document.getElementById(id);
  const { state, util, auth, render, saved } = window.app;
  const { showToast, updateShareLink } = util;
  const { stopPeriodicAuthCheck } = auth || {};

  // DOM elements
  const chatInput = $('chatInput');
  const sendButton = $('sendButton');
  const downloadBtn = $('downloadBtn');
  const shareBtn = $('shareBtn');
  const clearSavedBtn = $('clearSavedBtn');

  // ===== SCROLL MANAGER =====
  const ScrollManager = {
    autoScrollEnabled: true,
    scrollThreshold: 100,

    init() {
      this.createScrollButton();
      this.attachScrollListeners();
    },

    createScrollButton() {
      if ($('scrollToBottomBtn')) return;

      const scrollBtn = document.createElement('button');
      scrollBtn.id = 'scrollToBottomBtn';
      scrollBtn.className = 'scroll-to-bottom-btn hidden';
      scrollBtn.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="6,9 12,15 18,9"></polyline>
        </svg>
      `;
      
      scrollBtn.style.cssText = `
        position: fixed;
        bottom: 120px;
        right: 20px;
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: #1976d2;
        color: white;
        border: none;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        cursor: pointer;
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s ease;
        opacity: 0;
        visibility: hidden;
      `;

      scrollBtn.addEventListener('click', () => this.scrollToBottom(true));
      document.body.appendChild(scrollBtn);

      this.addScrollButtonStyles();
    },

    addScrollButtonStyles() {
      if (document.getElementById('scroll-btn-styles')) return;

      const style = document.createElement('style');
      style.id = 'scroll-btn-styles';
      style.textContent = `
        .scroll-to-bottom-btn.visible { 
          opacity: 1 !important; 
          visibility: visible !important; 
        }
        .scroll-to-bottom-btn:hover { 
          background: #1565c0 !important; 
          transform: translateY(-2px); 
        }
      `;
      document.head.appendChild(style);
    },

    attachScrollListeners() {
      let scrollTimeout;
      
      window.addEventListener('scroll', () => {
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(() => {
          this.updateScrollButton();
          this.updateAutoScrollState();
        }, 100);
      });
    },

    updateScrollButton() {
      const scrollBtn = $('scrollToBottomBtn');
      if (!scrollBtn) return;

      const isNearBottom = this.isNearBottom();
      scrollBtn.classList.toggle('visible', !isNearBottom);
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
        setTimeout(() => this.scrollToBottom(), 100);
      }
    }
  };

  // ===== STREAMING WRITER =====
  const StreamingWriter = {
    activeAnimations: new Set(),

    async writeText(element, text, options = {}) {
      const { speed = 15, enableMarkdown = true, onComplete = null } = options;
      const animationId = `${Date.now()}_${Math.random()}`;
      
      this.activeAnimations.add(animationId);

      try {
        element.innerHTML = '';
        
        if (enableMarkdown) {
          await this.writeMarkdown(element, text, speed, animationId);
        } else {
          await this.writePlain(element, text, speed, animationId);
        }
        
        if (onComplete) onComplete();
      } finally {
        this.activeAnimations.delete(animationId);
      }
    },

    async writePlain(element, text, speed, animationId) {
      let index = 0;
      
      return new Promise((resolve) => {
        const writeChar = () => {
          if (!this.activeAnimations.has(animationId)) {
            return resolve();
          }
          
          if (index < text.length) {
            element.textContent += text[index++];
            ScrollManager.onNewContent();
            setTimeout(writeChar, speed);
          } else {
            resolve();
          }
        };
        
        writeChar();
      });
    },

    async writeMarkdown(element, text, speed, animationId) {
      const html = this.markdownToHtml(text);
      const tempElement = document.createElement('div');
      tempElement.innerHTML = html;
      
      await this.streamHTML(element, tempElement, speed, animationId);
    },

    async streamHTML(target, source, speed, animationId) {
      const textNodes = this.getTextNodes(source);
      target.innerHTML = source.innerHTML;
      
      const targetTextNodes = this.getTextNodes(target);
      targetTextNodes.forEach(node => node.textContent = '');
      
      for (let i = 0; i < textNodes.length && this.activeAnimations.has(animationId); i++) {
        const sourceText = textNodes[i].textContent;
        const targetNode = targetTextNodes[i];
        
        if (sourceText && targetNode) {
          await this.animateTextNode(targetNode, sourceText, speed, animationId);
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
          
          if (index % 10 === 0) {
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
        null,
        false
      );
      
      let node;
      while (node = walker.nextNode()) {
        if (node.textContent.trim()) {
          nodes.push(node);
        }
      }
      
      return nodes;
    },

    markdownToHtml(text) {
      return text
        .replace(/\*\*([\s\S]*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*([\s\S]*?)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        .replace(/^(.*)$/gm, '<p>$1</p>')
        .replace(/<p><\/p>/g, '');
    },

    stopAll() {
      this.activeAnimations.clear();
    }
  };

  // ===== ENHANCED RENDERER =====
  const EnhancedRenderer = {
    async renderBotResponse(data, messageId) {
      const messageElement = $(messageId);
      if (!messageElement) return;

      const contentElement = messageElement.querySelector('.message-content');
      if (!contentElement) return;

      this.showTypingIndicator(contentElement);
      await new Promise(resolve => setTimeout(resolve, 350));
      await this.streamResponseContent(contentElement, data);
    },

    showTypingIndicator(element) {
      element.innerHTML = `
        <div class="typing-indicator">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      `;

      if (!document.getElementById('typing-styles')) {
        const style = document.createElement('style');
        style.id = 'typing-styles';
        style.textContent = `
          .typing-indicator { 
            display: flex; 
            gap: 4px; 
            padding: 16px 0; 
            align-items: center; 
          }
          .typing-dot { 
            width: 8px; 
            height: 8px; 
            border-radius: 50%; 
            background-color: #64b5f6; 
            animation: typing 1.4s infinite ease-in-out; 
          }
          .typing-dot:nth-child(2) { animation-delay: 0.2s; }
          .typing-dot:nth-child(3) { animation-delay: 0.4s; }
          @keyframes typing {
            0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
            30% { transform: translateY(-10px); opacity: 1; }
          }
        `;
        document.head.appendChild(style);
      }
    },

    async streamResponseContent(element, data) {
      let fullHTML = '';
      
      if (typeof data === 'string') {
        fullHTML = data;
      } else if (data && typeof data === 'object') {
        fullHTML = this.buildResponseHTML(data);
      }

      if (!fullHTML) {
        fullHTML = typeof data === 'string' ? data : 'No response content available.';
      }

      await StreamingWriter.writeText(element, fullHTML, {
        speed: 15,
        enableMarkdown: true,
        onComplete: () => ScrollManager.onNewContent()
      });
    },

    buildResponseHTML(data) {
      let html = '';

      // Title
      if (data.best_book?.title) {
        html += `<div class="concept-title">${this.escapeHtml(data.best_book.title)}</div>`;
      }

      // Summary
      if (data.summary) {
        html += `
          <div class="concept-explanation">
            <h4>📝 Summary</h4>
            <p>${this.escapeHtml(data.summary)}</p>
          </div>
        `;
      }

      // Detailed content
      if (data.best_book?.content) {
        html += `
          <div class="concept-explanation">
            <h4>📚 Detailed Content</h4>
            <div>${this.formatContent(data.best_book.content)}</div>
          </div>
        `;
      }

      // Practice problems
      if (Array.isArray(data.top_dsa) && data.top_dsa.length) {
        html += this.buildPracticeProblemsHTML(data.top_dsa);
      }

      // Video suggestions
      if (Array.isArray(data.video_suggestions) && data.video_suggestions.length) {
        html += this.buildVideoSuggestionsHTML(data.video_suggestions);
      }

      // Fallback content
      if (!html && data.response) {
        html = this.escapeHtml(data.response);
      }

      return html;
    },

    buildPracticeProblemsHTML(problems) {
      let html = `
        <div class="related-qa">
          <h4>🎯 Related Questions</h4>
      `;

      problems.forEach(problem => {
        html += `
          <div class="qa-item">
            <div class="question">${this.escapeHtml(problem.question || 'Practice Question')}</div>
            ${problem.article_link && problem.article_link !== '#' ? 
              `<a href="${problem.article_link}" target="_blank" class="qa-link">📖 Read Article</a>` : ''}
            ${problem.practice_link && problem.practice_link !== '#' ? 
              `<a href="${problem.practice_link}" target="_blank" class="qa-link">💻 Practice</a>` : ''}
          </div>
        `;
      });

      html += '</div>';
      return html;
    },

    buildVideoSuggestionsHTML(videos) {
      let html = `
        <div class="video-suggestions">
          <h4>🎥 Video Recommendations</h4>
          <div class="video-grid">
      `;

      videos.forEach(video => {
        const videoUrl = video.video_url || video.embed_url || '';
        const title = video.title || 'Video Tutorial';
        
        html += `
          <div class="video-card" onclick="openVideoModal('${videoUrl}', '${this.escapeHtml(title)}')">
            ${video.thumbnail_url ? 
              `<img src="${video.thumbnail_url}" alt="${this.escapeHtml(title)}" class="video-thumbnail">` : 
              '<div class="video-thumbnail">▶</div>'}
            <div class="video-info">
              <div class="video-title">${this.escapeHtml(title)}</div>
              <div class="video-meta">
                ${video.difficulty || ''} 
                ${video.duration ? '- ' + video.duration : ''}
              </div>
            </div>
          </div>
        `;
      });

      html += '</div></div>';
      return html;
    },

    formatContent(content) {
      if (!content) return '';
      
      return content
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        .replace(/\*\*([\s\S]*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*([\s\S]*?)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code>$1</code>');
    },

    escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }
  };

  // ===== ENHANCED SEND MESSAGE WITH STREAMING =====
  window.sendMessage = async function() {
    const query = chatInput?.value?.trim();
    if (!query || sendButton?.disabled) return;

    if (sendButton) sendButton.disabled = true;
    if (chatInput) { 
      chatInput.disabled = true; 
      chatInput.style.opacity = '0.7'; 
    }

    try {
      // Hide welcome screen on first message
      const welcomeScreen = $('welcomeScreen');
      if (welcomeScreen) {
        welcomeScreen.style.display = 'none';
        state.isFirstMessage = false;
      }

      render.addMessage?.('user', query);
      if (chatInput) chatInput.value = '';
      ScrollManager.onNewContent();

      const messageId = `msg-${Date.now()}`;
      render.addBotMessage?.('', messageId);

      const payload = { query };
      if (state?.currentThreadId) {
        payload.thread_id = state.currentThreadId;
      }

      // Try streaming endpoint first, fallback to JSON
      let response = await fetch('/query-stream', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json', 
          'Accept': 'text/event-stream, application/json' 
        },
        body: JSON.stringify(payload)
      });

      if (response.status === 404) {
        // Fallback to regular JSON endpoint
        response = await fetch('/query', {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json', 
            'Accept': 'application/json' 
          },
          body: JSON.stringify(payload)
        });
      }

      if (!response.ok) {
        const errorText = await response.text().catch(() => '');
        throw new Error(`Server error: ${response.status} ${errorText}`);
      }

      const contentType = response.headers.get('content-type') || '';
      const placeholder = $(messageId)?.querySelector('.message-content');
      
      if (!placeholder) {
        throw new Error('Message placeholder not found');
      }

      // Handle Server-Sent Events streaming
      if (contentType.includes('text/event-stream') && response.body) {
        await handleStreamingResponse(response, placeholder, messageId);
      } else {
        // Handle regular JSON response
        const data = await response.json();
        
        if (data.thread_id) {
          state.currentThreadId = data.thread_id;
          updateShareLink?.(state.currentThreadId);
        }
        
        await EnhancedRenderer.renderBotResponse(data, messageId);
      }

    } catch (error) {
      console.error('Send message error:', error);
      handleSendError(error, messageId);
    } finally {
      if (sendButton) sendButton.disabled = false;
      if (chatInput) { 
        chatInput.disabled = false; 
        chatInput.style.opacity = '1'; 
        chatInput.focus(); 
      }
    }
  };

  // ===== STREAMING RESPONSE HANDLER =====
  async function handleStreamingResponse(response, placeholder, messageId) {
    EnhancedRenderer.showTypingIndicator(placeholder);

    const decoder = new TextDecoder('utf-8');
    const reader = response.body.getReader();
    let buffer = '';
    let finalJson = null;

    const appendText = (text) => {
      const contentElement = placeholder.querySelector('p') || placeholder;
      const escapedText = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
      contentElement.innerHTML += escapedText;
      ScrollManager.onNewContent();
    };

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';

      for (const eventString of events) {
        const event = parseSSEEvent(eventString);
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
                updateShareLink?.(state.currentThreadId);
              }
            } catch (error) {
              console.error('Failed to parse meta:', error);
            }
            break;
        }
      }
    }

    // Render final response if available
    if (finalJson) {
      await EnhancedRenderer.renderBotResponse(finalJson, messageId);
    }
  }

  function parseSSEEvent(eventString) {
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
  }

  function handleSendError(error, messageId) {
    const messageElement = $(messageId);
    if (messageElement) {
      const content = messageElement.querySelector('.message-content');
      if (content) {
        content.innerHTML = `
          <div class="error-message">
            <h4>❌ Error</h4>
            <p>${this.escapeHtml(error?.message || 'Something went wrong. Please try again.')}</p>
          </div>
        `;
      }
    }
    
    if (typeof showToast === 'function') {
      showToast('Error: ' + (error?.message || 'Request failed'));
    } else {
      console.error('Error:', error?.message || 'Request failed');
    }
  }

  // ===== CHAT UTILITIES =====
  const ChatUtilities = {
    copyMessage(messageId) {
      const messageElement = $(messageId);
      if (!messageElement) return;

      const contentElement = messageElement.querySelector('.message-content');
      if (!contentElement) return;

      const textContent = contentElement.innerText || contentElement.textContent;
      
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(textContent).then(() => {
          showToast?.('📋 Message copied to clipboard!');
        }).catch(() => {
          this.fallbackCopyText(textContent);
        });
      } else {
        this.fallbackCopyText(textContent);
      }
    },

    fallbackCopyText(text) {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      
      try {
        document.execCommand('copy');
        showToast?.('📋 Message copied to clipboard!');
      } catch (error) {
        showToast?.('❌ Failed to copy message');
      }
      
      document.body.removeChild(textarea);
    },

    saveMessage(messageId) {
      const messageElement = $(messageId);
      if (!messageElement) return;

      const contentElement = messageElement.querySelector('.message-content');
      const titleElement = messageElement.querySelector('.concept-title') || 
                          messageElement.querySelector('.sender-name');
      
      if (!contentElement) return;

      const content = contentElement.innerHTML;
      const title = titleElement ? titleElement.textContent : 'DSA Concept';
      
      if (saved?.saveMessage) {
        saved.saveMessage(messageId, title, content);
      }
    },

    shareMessage(messageId) {
      const messageElement = $(messageId);
      if (!messageElement) return;

      const contentElement = messageElement.querySelector('.message-content');
      if (!contentElement) return;

      const textContent = contentElement.innerText || contentElement.textContent;
      const shareData = {
        title: 'DSA Mentor - Shared Message',
        text: textContent.substring(0, 200) + (textContent.length > 200 ? '...' : ''),
        url: window.location.href
      };

      if (navigator.share && navigator.canShare && navigator.canShare(shareData)) {
        navigator.share(shareData).catch(console.error);
      } else {
        const shareUrl = `${window.location.origin}/chat/${state?.currentThreadId || ''}`;
        
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(shareUrl).then(() => {
            showToast?.('🔗 Share link copied to clipboard!');
          });
        } else {
          this.fallbackCopyText(shareUrl);
        }
      }
    },

    async downloadChat() {
      const chatContent = $('chatContent');
      if (!chatContent) return;

      try {
        const html = chatContent.innerHTML;
        const payload = { html, thread_id: state?.currentThreadId || 'unknown' };
        const res = await fetch('/generate-pdf', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          link.download = `dsa-mentor-${state?.currentThreadId || 'chat'}.pdf`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(url);
          showToast?.('📄 PDF downloaded!');
          return;
        }
        if (res.status === 401 || res.status === 403) {
          showToast?.('Please login to download PDF');
        }
        throw new Error(`PDF generation failed (${res.status})`);
      } catch (e) {
        // Fallback to text export
        const messages = chatContent.querySelectorAll('.message');
        let chatText = 'DSA Mentor Chat Export\n';
        chatText += '========================\n\n';
        messages.forEach((message) => {
          const isUser = message.classList.contains('user-message');
          const sender = isUser ? 'You' : 'DSA Mentor';
          const content = message.querySelector('.message-content');
          if (content) {
            const text = content.innerText || content.textContent;
            chatText += `${sender}:\n${text}\n\n`;
          }
        });
        const blob = new Blob([chatText], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `dsa-chat-${new Date().toISOString().split('T')[0]}.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        showToast?.('💾 Chat downloaded as text');
      }
    },

    shareCurrentChat() {
      const shareUrl = `${window.location.origin}/chat/${state?.currentThreadId || ''}`;
      
      if (navigator.share) {
        navigator.share({
          title: 'DSA Mentor Chat',
          text: 'Check out my DSA learning session!',
          url: shareUrl
        }).catch(console.error);
      } else {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(shareUrl).then(() => {
            showToast?.('🔗 Share link copied to clipboard!');
          });
        } else {
          ChatUtilities.fallbackCopyText(shareUrl);
        }
      }
    }
  };

  // ===== GLOBAL FUNCTION BINDINGS =====
  window.copyMessage = ChatUtilities.copyMessage.bind(ChatUtilities);
  window.saveMessage = ChatUtilities.saveMessage.bind(ChatUtilities);
  window.shareMessage = ChatUtilities.shareMessage.bind(ChatUtilities);

  // ===== EVENT LISTENERS =====
  function setupChatEventListeners() {
    // Send button click
    if (sendButton) {
      sendButton.addEventListener('click', () => window.sendMessage());
    }

    // Enter key in chat input
    if (chatInput) {
      chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          window.sendMessage();
        }
      });
    }

    // Download chat (PDF via backend with fallback)
    if (downloadBtn) {
      downloadBtn.addEventListener('click', ChatUtilities.downloadChat);
    }

    // Share chat → open modal and populate link (fallback to native share)
    if (shareBtn) {
      shareBtn.addEventListener('click', () => {
        const shareModal = $('shareModal');
        const shareLink = $('shareLink');
        const url = `${window.location.origin}/chat/${state?.currentThreadId || ''}`;

        if (navigator.share) {
          navigator.share({
            title: 'DSA Mentor Chat',
            text: 'Check out my DSA learning session!',
            url
          }).catch(() => {
            if (shareLink) shareLink.value = url;
            shareModal?.classList.add('active');
          });
        } else {
          if (shareLink) shareLink.value = url;
          shareModal?.classList.add('active');
        }
      });
    }

    // Modal close events
    document.addEventListener('click', (e) => {
      if (e.target.classList?.contains('modal-overlay')) {
        e.target.classList.remove('active');
      }
      if (e.target.classList?.contains('video-modal') && window.closeVideoModal) {
        window.closeVideoModal();
      }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.key === 'b') {
        e.preventDefault();
        ScrollManager.scrollToBottom(true);
        showToast?.('Scrolled to bottom');
      }
    });

    // Before unload cleanup
    window.addEventListener('beforeunload', () => {
      stopPeriodicAuthCheck?.();
      StreamingWriter.stopAll();
    });
  }

  // ===== INITIALIZATION =====
  function initializeChat() {
    try {
      setupChatEventListeners();
      ScrollManager.init();
      
      if (state?.serverUser?.is_authenticated && chatInput) {
        chatInput.focus();
      }
      
      console.log('DSA Mentor Chat module loaded successfully');
    } catch (error) {
      console.error('Failed to initialize app-chat:', error);
      showToast?.('Chat initialization failed');
    }
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeChat);
  } else {
    initializeChat();
  }

  // ===== EXTEND APP OBJECT =====
  window.app.scroll = ScrollManager;
  window.app.streaming = StreamingWriter;
  window.app.enhanced = EnhancedRenderer;
  window.app.chat = ChatUtilities;

  console.log('App chat module loaded');

})();
