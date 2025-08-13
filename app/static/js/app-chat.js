(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);

  const { state, util, auth, render, saved } = window.app;
  const { showToast, updateShareLink } = util;
  const { stopPeriodicAuthCheck } = auth;

  const chatInput     = $('chatInput');
  const sendButton    = $('sendButton');
  const downloadBtn   = $('downloadBtn');
  const shareBtn      = $('shareBtn');
  const clearSavedBtn = $('clearSavedBtn');

  // ===== SCROLL MANAGEMENT =====
  const ScrollManager = {
    autoScrollEnabled: true,
    scrollThreshold: 100, // pixels from bottom
    
    init() {
      this.createScrollButton();
      this.attachScrollListeners();
    },
    
    createScrollButton() {
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
      
      // Add CSS for smooth transitions
      const style = document.createElement('style');
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
      // Disable auto-scroll if user scrolls up manually
      const isNearBottom = this.isNearBottom();
      this.autoScrollEnabled = isNearBottom;
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
        this.autoScrollEnabled = true; // Re-enable after manual scroll to bottom
      }
    },
    
    // Call this when new content is added
    onNewContent() {
      if (this.autoScrollEnabled) {
        // Small delay to ensure content is rendered
        setTimeout(() => this.scrollToBottom(), 100);
      }
    }
  };

  // ===== STREAMING TEXT EFFECT =====
  const StreamingWriter = {
    activeAnimations: new Set(),
    
    async writeText(element, text, options = {}) {
      const {
        speed = 20, // milliseconds between characters
        enableMarkdown = true,
        onComplete = null
      } = options;
      
      // Generate unique ID for this animation
      const animationId = Date.now() + Math.random();
      this.activeAnimations.add(animationId);
      
      try {
        element.innerHTML = '';
        
        if (enableMarkdown) {
          await this.writeMarkdownText(element, text, speed, animationId);
        } else {
          await this.writePlainText(element, text, speed, animationId);
        }
        
        if (onComplete) onComplete();
      } finally {
        this.activeAnimations.delete(animationId);
      }
    },
    
    async writePlainText(element, text, speed, animationId) {
      let currentIndex = 0;
      
      return new Promise((resolve) => {
        const writeChar = () => {
          // Check if animation was cancelled
          if (!this.activeAnimations.has(animationId)) {
            resolve();
            return;
          }
          
          if (currentIndex < text.length) {
            element.textContent += text[currentIndex];
            currentIndex++;
            
            // Trigger scroll update
            ScrollManager.onNewContent();
            
            setTimeout(writeChar, speed);
          } else {
            resolve();
          }
        };
        
        writeChar();
      });
    },
    
    async writeMarkdownText(element, text, speed, animationId) {
      // Pre-process markdown to HTML
      const htmlContent = this.parseMarkdownToHTML(text);
      
      // Create a temporary element to parse HTML
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = htmlContent;
      
      // Stream the content progressively
      await this.streamHTMLContent(element, tempDiv, speed, animationId);
    },
    
    async streamHTMLContent(targetElement, sourceElement, speed, animationId) {
      const textNodes = this.getTextNodes(sourceElement);
      
      // Clone the structure but with empty text content
      targetElement.innerHTML = sourceElement.innerHTML;
      const targetTextNodes = this.getTextNodes(targetElement);
      
      // Clear all text content initially
      targetTextNodes.forEach(node => node.textContent = '');
      
      // Stream text into each node
      for (let i = 0; i < textNodes.length && this.activeAnimations.has(animationId); i++) {
        const sourceText = textNodes[i].textContent;
        const targetNode = targetTextNodes[i];
        
        if (sourceText && targetNode) {
          await this.animateTextNode(targetNode, sourceText, speed, animationId);
        }
      }
    },
    
    async animateTextNode(targetNode, text, speed, animationId) {
      return new Promise((resolve) => {
        let currentIndex = 0;
        
        const writeChar = () => {
          if (!this.activeAnimations.has(animationId) || currentIndex >= text.length) {
            resolve();
            return;
          }
          
          targetNode.textContent += text[currentIndex];
          currentIndex++;
          
          // Trigger scroll update periodically
          if (currentIndex % 10 === 0) {
            ScrollManager.onNewContent();
          }
          
          setTimeout(writeChar, speed);
        };
        
        writeChar();
      });
    },
    
    getTextNodes(element) {
      const textNodes = [];
      const walker = document.createTreeWalker(
        element,
        NodeFilter.SHOW_TEXT,
        null,
        false
      );
      
      let node;
      while (node = walker.nextNode()) {
        if (node.textContent.trim()) {
          textNodes.push(node);
        }
      }
      
      return textNodes;
    },
    
    parseMarkdownToHTML(text) {
      // Basic markdown parsing - you can enhance this or use a library like marked.js
      return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        .replace(/^(.*)$/gm, '<p>$1</p>')
        .replace(/<p><\/p>/g, '');
    },
    
    stopAll() {
      this.activeAnimations.clear();
    }
  };

  // ===== ENHANCED BOT RESPONSE RENDERING =====
  const EnhancedRender = {
    async renderBotResponse(data, messageId) {
      const messageElement = document.getElementById(messageId);
      if (!messageElement) return;
      
      const contentElement = messageElement.querySelector('.message-content');
      if (!contentElement) return;
      
      // Show typing indicator first
      this.showTypingIndicator(contentElement);
      
      // Small delay for better UX
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Start streaming the response
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
      
      // Add CSS for typing animation if not exists
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
          .typing-dot:nth-child(2) {
            animation-delay: 0.2s;
          }
          .typing-dot:nth-child(3) {
            animation-delay: 0.4s;
          }
          @keyframes typing {
            0%, 60%, 100% {
              transform: translateY(0);
              opacity: 0.5;
            }
            30% {
              transform: translateY(-10px);
              opacity: 1;
            }
          }
        `;
        document.head.appendChild(style);
      }
    },
    
    async streamResponseContent(element, data) {
      let fullHTML = '';
      
      // Build the response HTML
      if (data.best_book?.title) {
        fullHTML += `
          <div class="concept-title">${data.best_book.title}</div>
        `;
      }
      
      if (data.summary) {
        fullHTML += `
          <div class="concept-explanation">
            <h4>📝 Summary</h4>
            <p>${data.summary}</p>
          </div>
        `;
      }
      
      if (data.best_book?.content) {
        fullHTML += `
          <div class="concept-explanation">
            <h4>📚 Detailed Content</h4>
            <div>${this.formatContent(data.best_book.content)}</div>
          </div>
        `;
      }
      
      if (data.top_dsa?.length) {
        fullHTML += `
          <div class="related-qa">
            <h4>🎯 Related Questions</h4>
            ${data.top_dsa.map((qa, i) => `
              <div class="qa-item">
                <div class="question">${qa.question || 'Practice Question'}</div>
                ${qa.article_link && qa.article_link !== '#' ? 
                  `<a href="${qa.article_link}" target="_blank" class="qa-link">📖 Read Article</a>` : ''
                }
                ${qa.practice_link && qa.practice_link !== '#' ? 
                  `<a href="${qa.practice_link}" target="_blank" class="qa-link">💻 Practice</a>` : ''
                }
              </div>
            `).join('')}
          </div>
        `;
      }
      
      if (data.video_suggestions?.length) {
        fullHTML += `
          <div class="video-suggestions">
            <h4>🎥 Video Recommendations</h4>
            <div class="video-grid">
              ${data.video_suggestions.map(video => `
                <div class="video-card" onclick="openVideoModal('${video.embed_url}', '${video.title}')">
                  <img src="${video.thumbnail_url}" alt="${video.title}" class="video-thumbnail">
                  <div class="video-info">
                    <div class="video-title">${video.title}</div>
                    <div class="video-meta">${video.difficulty} • ${video.duration}</div>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }
      
      // Stream the content with typing effect
      await StreamingWriter.writeText(element, fullHTML, {
        speed: 15, // Faster for better UX
        enableMarkdown: true,
        onComplete: () => {
          // Scroll to show new content if auto-scroll is enabled
          ScrollManager.onNewContent();
        }
      });
    },
    
    formatContent(content) {
      if (!content) return '';
      
      return content
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>');
    }
  };

  // ===== ENHANCED SEND MESSAGE FUNCTION =====
  window.sendMessage = async function() {
    const query = chatInput?.value?.trim();
    if (!query || sendButton?.disabled) return;

    // Disable input during processing
    if (sendButton) sendButton.disabled = true;
    if (chatInput) {
      chatInput.disabled = true;
      chatInput.style.opacity = '0.7';
    }

    try {
      // Hide welcome screen
      const welcomeScreen = $('welcomeScreen');
      if (welcomeScreen) welcomeScreen.style.display = 'none';

      // Add user message
      render.addMessage('user', query);
      if (chatInput) chatInput.value = '';

      // Scroll to show user message
      ScrollManager.onNewContent();

      // Add bot message placeholder
      const messageId = `msg-${Date.now()}`;
      render.addBotMessage('', messageId);

      // Send request
      const response = await fetch('/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query, 
          thread_id: state.currentThreadId 
        })
      });

      const data = await response.json();

      if (response.ok) {
        // Update thread ID if provided
        if (data.thread_id) {
          state.currentThreadId = data.thread_id;
          updateShareLink();
        }

        // Stream the response
        await EnhancedRender.renderBotResponse(data, messageId);
      } else {
        // Show error message
        const errorElement = document.getElementById(messageId);
        if (errorElement) {
          const contentElement = errorElement.querySelector('.message-content');
          if (contentElement) {
            contentElement.innerHTML = `
              <div class="error-message">
                <h4>❌ Error</h4>
                <p>${data.error || 'Something went wrong. Please try again.'}</p>
              </div>
            `;
          }
        }
        showToast('Error: ' + (data.error || 'Request failed'));
      }
    } catch (error) {
      console.error('Send message error:', error);
      showToast('Network error. Please check your connection.');
    } finally {
      // Re-enable input
      if (sendButton) sendButton.disabled = false;
      if (chatInput) {
        chatInput.disabled = false;
        chatInput.style.opacity = '1';
        chatInput.focus();
      }
    }
  };

  // ===== SHARED CHAT FUNCTIONALITY (Updated) =====
  const SharedChat = {
    isSharedView: false,
    sharedThreadId: null,
    
    init() {
      this.isSharedView = document.body.dataset.sharedView === 'true';
      this.sharedThreadId = document.body.dataset.sharedThreadId;
      
      if (this.isSharedView && this.sharedThreadId) {
        this.loadSharedChat(this.sharedThreadId);
      }
    },
    
    async loadSharedChat(threadId) {
      try {
        const response = await fetch(`/api/shared/thread/${threadId}`);
        const data = await response.json();
        
        if (response.ok) {
          console.log('Loading shared chat:', data);
          
          const welcomeScreen = $('welcomeScreen');
          if (welcomeScreen) welcomeScreen.style.display = 'none';
          
          // Load messages with streaming effect
          await this.displaySharedMessages(data.messages);
          this.showSharedBanner(threadId);
          
          if (window.app?.state) {
            window.app.state.currentThreadId = threadId;
          }
        } else {
          console.error('Failed to load shared chat:', data.error);
          showToast('Failed to load shared chat: ' + data.error);
        }
      } catch (error) {
        console.error('Error loading shared chat:', error);
        showToast('Error loading shared chat');
      }
    },
    
    async displaySharedMessages(messages) {
      const chatContent = $('chatContent');
      if (!chatContent) return;
      
      // Disable auto-scroll during bulk message loading
      ScrollManager.autoScrollEnabled = false;
      
      for (const message of messages) {
        if (message.sender === 'user') {
          render.addMessage('user', message.content);
        } else if (message.sender === 'assistant') {
          const messageId = `msg-${Date.now()}-${Math.random()}`;
          render.addBotMessage('', messageId);
          
          // Small delay between messages for better UX
          await new Promise(resolve => setTimeout(resolve, 200));
          
          // Stream each message
          await EnhancedRender.renderBotResponse(message.content, messageId);
          
          // Brief pause between messages
          await new Promise(resolve => setTimeout(resolve, 300));
        }
      }
      
      // Re-enable auto-scroll and scroll to bottom
      ScrollManager.autoScrollEnabled = true;
      ScrollManager.scrollToBottom(true);
    },
    
    showSharedBanner(threadId) {
      const chatContent = $('chatContent');
      if (!chatContent || document.querySelector('.shared-chat-banner')) return;
      
      const banner = document.createElement('div');
      banner.className = 'shared-chat-banner';
      banner.style.cssText = `
        background: #e3f2fd; border: 1px solid #2196f3; border-radius: 8px;
        padding: 12px 16px; margin-bottom: 16px; color: #1976d2; font-size: 14px;
        display: flex; align-items: center; gap: 8px;
      `;
      banner.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92-1.31-2.92-2.92-2.92z"/>
        </svg>
        <span>📤 You're viewing a shared conversation • You can continue chatting</span>
      `;
      chatContent.prepend(banner);
    }
  };

  // ===== EXISTING MESSAGE ACTIONS (Unchanged) =====
  window.copyMessage = function(messageId) {
    const el = document.getElementById(messageId);
    if (!el) return;
    const text = el.querySelector('.message-content')?.innerText;
    if (text && navigator.clipboard) {
      navigator.clipboard.writeText(text)
        .then(() => showToast('Message copied to clipboard!'))
        .catch(() => showToast('Failed to copy message'));
    }
  };

  window.saveMessage = function(messageId) {
    const el = document.getElementById(messageId);
    if (!el) return;
    const btn = el.querySelector('.action-btn[onclick*="saveMessage"]');
    const map = state.savedMessages;
    if (map.has(messageId)) {
      map.delete(messageId);
      if (btn) btn.classList.remove('saved');
      saved.saveSavedMessages();
      render.updateSavedMessagesList();
      showToast('Message removed from saved items');
      return;
    }
    const contentEl = el.querySelector('.message-content');
    if (!contentEl) return;
    const title = contentEl.querySelector('.concept-title')?.textContent || 'DSA Response';
    const preview = (contentEl.innerText || '').substring(0, 100) + '...';
    const fullContent = contentEl.innerHTML;
    map.set(messageId, {
      id: messageId,
      title,
      preview,
      fullContent,
      threadId: state.currentThreadId,
      timestamp: new Date().toISOString()
    });
    if (btn) btn.classList.add('saved');
    saved.saveSavedMessages();
    render.updateSavedMessagesList();
    showToast('Message saved for later!');
  };

  window.shareMessage = function(messageId) {
    updateShareLink();
    const modal = $('shareModal');
    if (modal) modal.classList.add('active');
  };

  // ===== SHARE FUNCTIONALITY (Unchanged) =====
  async function shareCurrentChat() {
    if (SharedChat.isSharedView) {
      const shareLink = $('shareLink');
      if (shareLink) shareLink.value = window.location.href;
      $('shareModal')?.classList.add('active');
      return;
    }

    const currentThreadId = state.currentThreadId;
    if (!currentThreadId) {
      showToast('No active chat to share');
      return;
    }

    try {
      const response = await fetch(`/api/thread/${currentThreadId}/share`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      const data = await response.json();
      
      if (response.ok) {
        const shareLink = $('shareLink');
        if (shareLink) shareLink.value = data.share_url;
        
        $('shareModal')?.classList.add('active');
        
        try {
          await navigator.clipboard.writeText(data.share_url);
          showToast('Share link copied to clipboard!');
        } catch (err) {
          console.log('Clipboard copy failed');
        }
      } else {
        showToast('Failed to create share link: ' + data.error);
      }
    } catch (error) {
      console.error('Error creating share link:', error);
      showToast('Error creating share link');
    }
  }

  // ===== DOWNLOAD FUNCTIONALITY (Unchanged) =====
  function downloadChat() {
    const nodes = document.querySelectorAll('.message');
    if (!nodes.length) { showToast('No messages to download!'); return; }
    if (!downloadBtn) return;

    const original = downloadBtn.innerHTML;
    downloadBtn.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
        <path d="M14 8l-4 4-2-2" stroke="currentColor" stroke-width="2"/>
      </svg>
    `;
    downloadBtn.disabled = true;

    let html = `
      <div class="pdf-container">
        <div class="pdf-header">
          <h1>DSA Mentor Chat Export</h1>
          <p>Generated on ${new Date().toLocaleDateString()}</p>
          <p>Thread ID: ${state.currentThreadId}</p>
        </div>
        <div class="pdf-content">
    `;
    nodes.forEach(n => {
      if (n.id?.startsWith('loading-')) return;
      const content = n.querySelector('.message-content')?.innerHTML;
      if (!content) return;
      if (n.classList.contains('user-message')) html += `<div class="message user-message">${content}</div>`;
      else if (n.classList.contains('bot-message')) html += `<div class="message bot-message">${content}</div>`;
    });
    html += `</div></div>`;

    fetch('/generate-pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        html,
        thread_id: state.currentThreadId
      })
    })
      .then(r => { if (!r.ok) return r.json().then(e => Promise.reject(e)); return r.blob(); })
      .then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dsa-mentor-chat-${state.currentThreadId}-${new Date().toISOString().split('T')[0]}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast('📄 PDF downloaded successfully!');
      })
      .catch(() => showToast('❌ Error generating PDF. Please try again.'))
      .finally(() => {
        downloadBtn.innerHTML = original;
        downloadBtn.disabled = false;
      });
  }

  // ===== MODAL FUNCTIONS (Unchanged) =====
  window.closeModal = function(id) {
    const m = $(id);
    if (m) m.classList.remove('active');
  };
  
  window.copyShareLink = function() {
    const input = $('shareLink');
    if (input && navigator.clipboard) {
      input.select?.();
      navigator.clipboard.writeText(input.value)
        .then(() => { 
          showToast('Share link copied to clipboard!'); 
          window.closeModal('shareModal'); 
        })
        .catch(() => showToast('Failed to copy share link'));
    }
  };

  // ===== EVENT LISTENERS =====
  document.addEventListener('click', (e) => {
    if (e.target.classList?.contains('modal-overlay')) e.target.classList.remove('active');
    if (e.target.classList?.contains('video-modal')) window.closeVideoModal?.();
  });

  sendButton?.addEventListener('click', () => window.sendMessage());
  chatInput?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      window.sendMessage();
    }
  });
  
  shareBtn?.addEventListener('click', shareCurrentChat);
  downloadBtn?.addEventListener('click', downloadChat);
  clearSavedBtn?.addEventListener('click', () => {
    state.savedMessages.clear();
    saved.saveSavedMessages();
    render.updateSavedMessagesList();
    showToast('All saved messages cleared!');
  });

  // ===== INITIALIZATION =====
  saved.loadSavedMessages?.();
  if (state.serverUser?.is_authenticated) chatInput?.focus();

  // Initialize scroll management
  ScrollManager.init();
  
  // Initialize shared chat functionality
  SharedChat.init();

  // ===== CLEANUP =====
  window.addEventListener('beforeunload', () => {
    stopPeriodicAuthCheck?.();
    StreamingWriter.stopAll(); // Stop any ongoing animations
  });

  // Add keyboard shortcut to toggle auto-scroll
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'b') {
      e.preventDefault();
      ScrollManager.scrollToBottom(true);
      showToast('Scrolled to bottom');
    }
  });
})();
