// ===== app-auth.js =====
(() => {
  'use strict';

  // ===== UTILITIES =====
  const $ = (id) => document.getElementById(id);

  const Utils = {
    escapeHtml(text) {
      return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#x27;');
    },

    generateThreadId() {
      const timestamp = Date.now();
      const random = Math.random().toString(36).slice(2, 11);
      return `thread_${timestamp}_${random}`;
    },

    scrollToBottom() {
      const chatArea = $('chatArea');
      if (chatArea) {
        chatArea.scrollTop = chatArea.scrollHeight;
      }
    },

    showToast(message) {
      const toast = $('toast');
      if (!toast) return;
      
      toast.textContent = message;
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 3000);
    },

    updateShareLink(threadId) {
      const shareLink = $('shareLink');
      if (shareLink && threadId) {
        const currentDomain = window.location.origin;
        shareLink.value = `${currentDomain}/chat/${threadId}`;
      }
    }
  };

  // ===== APPLICATION STATE =====
  const AppState = {
    isFirstMessage: true,
    savedMessages: new Map(),
    currentThreadId: Utils.generateThreadId(),
    authCheckInterval: null,
    serverUser: window.SERVER_USER || { is_authenticated: false }
  };

  // ===== AUTHENTICATION MANAGER =====
  const AuthManager = {
    checkAuthentication() {
      const user = AppState.serverUser;
      
      if (user?.is_authenticated && user.name && user.email) {
        this.hideAuthOverlay();
        this.updateUserProfile(user);
        this.enableChatInterface();
        this.startPeriodicAuthCheck();
        return true;
      }
      
      this.showAuthOverlay();
      this.disableChatInterface();
      this.stopPeriodicAuthCheck();
      return false;
    },

    showAuthOverlay() {
      $('authOverlay')?.classList.add('active');
    },

    hideAuthOverlay() {
      $('authOverlay')?.classList.remove('active');
    },

    updateUserProfile(user) {
      const avatar = document.querySelector('.profile-avatar');
      const name = document.querySelector('.profile-name');
      const status = document.querySelector('.profile-status');
      
      if (avatar && user.name) {
        avatar.textContent = user.name.charAt(0).toUpperCase();
      }
      if (name && user.name) {
        name.textContent = user.name;
      }
      if (status && user.email) {
        status.textContent = user.email;
      }
    },

    enableChatInterface() {
      const chatInput = $('chatInput');
      const sendButton = $('sendButton');
      
      if (chatInput) chatInput.disabled = false;
      if (sendButton) sendButton.disabled = false;
    },

    disableChatInterface() {
      const chatInput = $('chatInput');
      const sendButton = $('sendButton');
      
      if (chatInput) chatInput.disabled = true;
      if (sendButton) sendButton.disabled = true;
    },

    startPeriodicAuthCheck() {
      if (AppState.authCheckInterval) {
        clearInterval(AppState.authCheckInterval);
      }
      
      AppState.authCheckInterval = setInterval(() => {
        this.performAuthCheck();
      }, 30000);
    },

    stopPeriodicAuthCheck() {
      if (AppState.authCheckInterval) {
        clearInterval(AppState.authCheckInterval);
        AppState.authCheckInterval = null;
      }
    },

    async performAuthCheck() {
      try {
        const response = await fetch('/auth-status');
        if (!response.ok) return;
        
        const data = await response.json();
        const wasAuthenticated = AppState.serverUser?.is_authenticated;
        const nowAuthenticated = data.is_authenticated;
        
        if (wasAuthenticated !== nowAuthenticated) {
          this.notifyAuthChange();
          location.reload();
          return;
        }
        
        if (nowAuthenticated && 
            AppState.serverUser?.id && 
            data.user_id && 
            AppState.serverUser.id !== data.user_id) {
          this.notifyAuthChange();
          location.reload();
        }
      } catch (error) {
        console.error('Auth check failed:', error);
      }
    },

    notifyAuthChange() {
      try {
        localStorage.setItem('auth_change', String(Date.now()));
        localStorage.removeItem('auth_change');
      } catch (error) {
        console.error('Failed to notify auth change:', error);
      }
    }
  };

  // ===== THEME MANAGER =====
  const ThemeManager = {
    THEME_KEY: 'dsa_theme',

    init() {
      const preferredTheme = localStorage.getItem(this.THEME_KEY) || 'dark';
      this.applyTheme(preferredTheme);
      
      const themeToggle = $('themeToggle');
      themeToggle?.addEventListener('click', () => {
        const currentTheme = document.body.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(newTheme);
      });
    },

    applyTheme(theme) {
      document.body.setAttribute('data-theme', theme);
      localStorage.setItem(this.THEME_KEY, theme);
      
      const themeToggle = $('themeToggle');
      const sunIcon = themeToggle?.querySelector('.sun-icon');
      const moonIcon = themeToggle?.querySelector('.moon-icon');
      
      if (sunIcon && moonIcon) {
        if (theme === 'dark') {
          sunIcon.style.display = 'none';
          moonIcon.style.display = 'block';
        } else {
          sunIcon.style.display = 'block';
          moonIcon.style.display = 'none';
        }
      }
    }
  };

  // ===== MESSAGE RENDERER =====
  const MessageRenderer = {
    addMessage(sender, content) {
      const chatContent = $('chatContent');
      if (!chatContent) return;

      const messageId = `message-${AppState.currentThreadId}-${Date.now()}`;
      const messageDiv = document.createElement('div');
      messageDiv.className = `message ${sender}-message`;
      messageDiv.id = messageId;

      if (sender === 'user') {
        messageDiv.innerHTML = `
          <div class="message-content">
            <p>${Utils.escapeHtml(content)}</p>
          </div>
        `;
      } else {
        messageDiv.innerHTML = this.getBotMessageHTML(messageId, content);
      }

      chatContent.appendChild(messageDiv);
      Utils.scrollToBottom();
      return messageId;
    },

    addBotMessage(content, messageId) {
      const chatContent = $('chatContent');
      if (!chatContent) return;

      const messageDiv = document.createElement('div');
      messageDiv.className = 'message bot-message';
      messageDiv.id = messageId || `msg-${Date.now()}`;
      messageDiv.innerHTML = this.getBotMessageHTML(messageDiv.id, content);

      chatContent.appendChild(messageDiv);
      Utils.scrollToBottom();
      return messageDiv.id;
    },

    getBotMessageHTML(messageId, content = '') {
      return `
        <div class="message-header">
          <div class="avatar bot-avatar">AI</div>
          <span class="sender-name">DSA Mentor</span>
        </div>
        <div class="message-content">${content}</div>
        <div class="message-actions">
          <button class="action-btn" onclick="copyMessage('${messageId}')" title="Copy">📋</button>
          <button class="action-btn" onclick="saveMessage('${messageId}')" title="Save for later">💾</button>
          <button class="action-btn" onclick="shareMessage('${messageId}')" title="Share">🔗</button>
        </div>
      `;
    },

    addBotResponse(data) {
      const chatContent = $('chatContent');
      if (!chatContent) return;

      const messageId = `message-${AppState.currentThreadId}-${Date.now()}`;
      const messageDiv = document.createElement('div');
      messageDiv.className = 'message bot-message';
      messageDiv.id = messageId;

      let html = `
        <div class="message-header">
          <div class="avatar bot-avatar">AI</div>
          <span class="sender-name">DSA Mentor</span>
        </div>
        <div class="message-content">
      `;

      // Build response content
      if (data.best_book?.title) {
        html += `<div class="concept-title">${Utils.escapeHtml(data.best_book.title)}</div>`;
      }

      if (data.summary) {
        html += `<div class="concept-explanation">${Utils.escapeHtml(data.summary)}</div>`;
      }

      if (data.best_book?.content) {
        const formattedContent = this.formatContent(data.best_book.content);
        html += `<div class="concept-explanation">${formattedContent}</div>`;
      }

      // Add complexity badges if relevant
      if (data.best_book?.content && /complexity|time|space/i.test(data.best_book.content)) {
        html += `
          <div class="complexity-badges">
            <span class="complexity-badge">Time Complexity Analysis</span>
            <span class="complexity-badge">Space Complexity Analysis</span>
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

      html += `
        </div>
        <div class="message-actions">
          <button class="action-btn" onclick="copyMessage('${messageId}')" title="Copy">📋</button>
          <button class="action-btn" onclick="saveMessage('${messageId}')" title="Save for later">💾</button>
          <button class="action-btn" onclick="shareMessage('${messageId}')" title="Share">🔗</button>
        </div>
      `;

      messageDiv.innerHTML = html;
      chatContent.appendChild(messageDiv);
      Utils.scrollToBottom();
    },

    buildPracticeProblemsHTML(problems) {
      let html = `
        <div class="practice-problems">
          <div class="section-header">📝 Related Practice Problems</div>
      `;

      problems.forEach(problem => {
        const title = `${problem.section || 'DSA'}: ${problem.question || ''}`;
        const description = problem.description || 'Practice this fundamental concept to strengthen your understanding.';
        
        html += `
          <div class="problem-card">
            <div class="problem-title">
              <span class="problem-section">${Utils.escapeHtml(title)}</span>
            </div>
            <div class="problem-description">${Utils.escapeHtml(description)}</div>
            <div class="problem-links">
              ${problem.article_link ? `<a href="${problem.article_link}" target="_blank" class="problem-link">Article</a>` : ''}
              ${problem.practice_link ? `<a href="${problem.practice_link}" target="_blank" class="problem-link">Practice</a>` : ''}
            </div>
          </div>
        `;
      });

      html += '</div>';
      return html;
    },

    buildVideoSuggestionsHTML(videos) {
      let html = `
        <div class="video-suggestions">
          <div class="section-header">🎥 Recommended Video Tutorials</div>
      `;

      videos.forEach(video => {
        const title = video.title || 'Video Tutorial';
        const topic = video.topic || 'DSA';
        const description = video.description || video.subtopic || 'Learn this concept through video tutorial';
        const difficulty = video.difficulty ? `<span class="video-difficulty">${Utils.escapeHtml(video.difficulty)}</span>` : '';
        const duration = video.duration ? `<span>⏱️ ${Utils.escapeHtml(video.duration)}</span>` : '';

        html += `
          <div class="video-card">
            <div class="video-header">
              <div class="video-thumbnail">▶</div>
              <div class="video-info">
                <div class="video-title">${Utils.escapeHtml(title)}</div>
                <div class="video-meta">
                  <span>${Utils.escapeHtml(topic)}</span>
                  ${difficulty}
                  ${duration}
                </div>
                <div class="video-description">${Utils.escapeHtml(description)}</div>
              </div>
            </div>
            <div class="video-actions">
              ${video.video_url ? `<button class="video-btn" onclick="openVideoModal('${encodeURI(video.video_url)}','${Utils.escapeHtml(title)}')">Watch</button>` : ''}
              ${video.video_url ? `<a href="${video.video_url}" target="_blank" class="video-btn video-btn-secondary">Open</a>` : ''}
            </div>
          </div>
        `;
      });

      html += '</div>';
      return html;
    },

    formatContent(content) {
      if (!content) return '';
      
      return content
        .replace(/\n/g, '<br>')
        .replace(/\*\*([\s\S]*?)\*\*/g, '<strong>$1</strong>')
        .replace(/```python\n([\s\S]*?)\n```/g, '<pre><code class="language-python">$1</code></pre>')
        .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/^# (.*)$/gm, '<h2>$1</h2>')
        .replace(/^## (.*)$/gm, '<h3>$1</h3>')
        .replace(/^### (.*)$/gm, '<h4>$1</h4>')
        .replace(/^- (.*)$/gm, '<li>$1</li>')
        .replace(/^\* (.*)$/gm, '<li>$1</li>')
        .replace(/---/g, '<hr>')
        .replace(/💡 \*\*Tips:\*\*/g, '<div class="tip-box">💡 <strong>Tips:</strong>')
        .replace(/(\d+)\. /g, '<strong>$1.</strong> ')
        .replace(/(?:^(?:<li>.*<\/li>\s*){1,})/gm, (match) => `<ul>${match}</ul>`);
    },

    addLoadingMessage() {
      const chatContent = $('chatContent');
      if (!chatContent) return null;

      const messageId = `loading-${Date.now()}`;
      const messageDiv = document.createElement('div');
      messageDiv.className = 'message bot-message';
      messageDiv.id = messageId;
      
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
      Utils.scrollToBottom();
      return messageId;
    },

    removeLoadingMessage(messageId) {
      if (!messageId) return;
      const element = $(messageId);
      if (element) element.remove();
    }
  };

  // ===== SAVED MESSAGES MANAGER =====
  const SavedMessagesManager = {
    STORAGE_KEY: 'dsa_saved_messages',

    loadSavedMessages() {
      try {
        const rawData = localStorage.getItem(this.STORAGE_KEY);
        const savedData = rawData ? JSON.parse(rawData) : {};
        AppState.savedMessages = new Map(Object.entries(savedData));
      } catch (error) {
        console.error('Failed to load saved messages:', error);
        AppState.savedMessages = new Map();
      }
      this.updateSavedMessagesList();
    },

    saveSavedMessages() {
      try {
        const dataObject = Object.fromEntries(AppState.savedMessages);
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(dataObject));
      } catch (error) {
        console.error('Failed to save messages:', error);
      }
    },

    saveMessage(messageId, title, content) {
      const timestamp = new Date().toISOString();
      const preview = this.createPreview(content);
      
      AppState.savedMessages.set(messageId, {
        id: messageId,
        title: title || 'Saved Message',
        preview,
        fullContent: content,
        timestamp
      });
      
      this.saveSavedMessages();
      this.updateSavedMessagesList();
      Utils.showToast('💾 Message saved successfully!');
    },

    removeMessage(messageId) {
      if (AppState.savedMessages.has(messageId)) {
        AppState.savedMessages.delete(messageId);
        this.saveSavedMessages();
        this.updateSavedMessagesList();
        Utils.showToast('Message removed from saved items!');
      }
    },

    clearAll() {
      AppState.savedMessages.clear();
      this.saveSavedMessages();
      this.updateSavedMessagesList();
      Utils.showToast('All saved messages cleared!');
    },

    createPreview(content, maxLength = 150) {
      const textContent = content.replace(/<[^>]*>/g, '').trim();
      return textContent.length > maxLength 
        ? textContent.substring(0, maxLength) + '...'
        : textContent;
    },

    updateSavedMessagesList() {
      const savedList = $('savedList');
      const emptySaved = $('emptySaved');
      const clearSavedBtn = $('clearSavedBtn');
      
      if (!savedList) return;

      const messages = Array.from(AppState.savedMessages.values());
      
      if (messages.length === 0) {
        if (emptySaved) emptySaved.style.display = 'block';
        if (clearSavedBtn) clearSavedBtn.style.display = 'none';
        savedList.innerHTML = '';
        if (emptySaved) savedList.appendChild(emptySaved);
        return;
      }

      if (emptySaved) emptySaved.style.display = 'none';
      if (clearSavedBtn) clearSavedBtn.style.display = 'block';

      messages.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
      savedList.innerHTML = '';
      
      messages.forEach(message => {
        const listItem = this.createSavedMessageListItem(message);
        savedList.appendChild(listItem);
      });
    },

    createSavedMessageListItem(message) {
      const li = document.createElement('li');
      li.className = 'saved-item';
      
      li.innerHTML = `
        <div class="saved-item-content">
          <div class="saved-item-title">${Utils.escapeHtml(message.title)}</div>
          <div class="saved-item-preview">${Utils.escapeHtml(message.preview)}</div>
        </div>
        <button class="saved-item-delete" title="Remove">✖</button>
      `;

      li.addEventListener('click', (e) => {
        if (e.target.closest('.saved-item-delete')) {
          this.removeMessage(message.id);
        } else {
          this.showSavedMessage(message);
        }
      });

      return li;
    },

    showSavedMessage(message) {
      const welcomeScreen = $('welcomeScreen') || document.querySelector('.welcome-screen');
      if (welcomeScreen && welcomeScreen.style.display !== 'none') {
        welcomeScreen.style.display = 'none';
        AppState.isFirstMessage = false;
      }
      this.addSavedMessageToChat(message);
    },

    addSavedMessageToChat(message) {
      const chatContent = $('chatContent');
      if (!chatContent) return;

      const messageId = `restored-${message.id}`;
      const messageDiv = document.createElement('div');
      messageDiv.className = 'message bot-message';
      messageDiv.id = messageId;
      
      const formattedDate = new Date(message.timestamp).toLocaleDateString();
      
      messageDiv.innerHTML = `
        <div class="message-header">
          <div class="avatar bot-avatar" style="background:#9333EA;">📌</div>
          <span class="sender-name">Saved Message</span>
          <span style="font-size:12px;color:var(--text-muted);margin-left:auto;">
            Saved ${formattedDate}
          </span>
        </div>
        <div class="message-content">${message.fullContent || message.preview}</div>
        <div class="message-actions">
          <button class="action-btn" onclick="copyMessage('${messageId}')" title="Copy">📋</button>
          <button class="action-btn" onclick="shareMessage('${messageId}')" title="Share">🔗</button>
        </div>
      `;

      chatContent.appendChild(messageDiv);
      Utils.scrollToBottom();
      Utils.showToast('💾 Saved message restored to chat!');
    }
  };

  // ===== VIDEO MODAL HANDLER =====
  const VideoModalHandler = {
    extractYouTubeID(url) {
      if (!url) return null;
      
      const patterns = [
        /(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]+)/,
        /(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]+)/,
        /(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]+)/,
        /(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([a-zA-Z0-9_-]+)/
      ];

      for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match && match[1]) return match[1];
      }
      return null;
    },

    openVideoModal(videoUrl, title) {
      const youtubeId = this.extractYouTubeID(videoUrl);
      const videoEmbed = $('videoEmbed');
      const videoModalTitle = $('videoModalTitle');
      const videoModal = $('videoModal');

      if (youtubeId) {
        const embedUrl = `https://www.youtube.com/embed/${youtubeId}`;
        if (videoEmbed) videoEmbed.src = embedUrl;
        if (videoModalTitle) videoModalTitle.textContent = title || 'Video Tutorial';
        if (videoModal) videoModal.classList.add('active');
      } else {
        window.open(videoUrl, '_blank');
      }
    },

    closeVideoModal() {
      const videoModal = $('videoModal');
      const videoEmbed = $('videoEmbed');
      
      if (videoModal) videoModal.classList.remove('active');
      if (videoEmbed) videoEmbed.src = '';
    }
  };

  // ===== THREAD MANAGEMENT =====
  const ThreadManager = {
    startNewThread() {
      AppState.currentThreadId = Utils.generateThreadId();
      AppState.isFirstMessage = true;

      const chatContent = $('chatContent');
      if (chatContent) {
        chatContent.innerHTML = this.getWelcomeScreenHTML();
      }

      Utils.updateShareLink(AppState.currentThreadId);
      Utils.showToast('🆕 New thread started!');
      
      const chatInput = $('chatInput');
      if (chatInput) chatInput.focus();
    },

    getWelcomeScreenHTML() {
      return `
        <div class="welcome-screen" id="welcomeScreen">
          <h1 class="welcome-title">Welcome to DSA Mentor</h1>
          <p class="welcome-subtitle">Your AI-powered companion for mastering Data Structures and Algorithms</p>
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
  };

  // ===== NETWORK MANAGER =====
  const NetworkManager = {
    async sendMessage() {
      const chatInput = $('chatInput');
      const sendButton = $('sendButton');
      
      if (!AppState.serverUser?.is_authenticated) {
        AuthManager.showAuthOverlay();
        Utils.showToast('Please login to continue');
        return;
      }

      const query = chatInput?.value.trim();
      if (!query) return;

      if (AppState.isFirstMessage) {
        const welcomeScreen = $('welcomeScreen') || document.querySelector('.welcome-screen');
        if (welcomeScreen) {
          welcomeScreen.style.display = 'none';
          AppState.isFirstMessage = false;
        }
      }

      MessageRenderer.addMessage('user', query);
      const loadingId = MessageRenderer.addLoadingMessage();
      
      if (chatInput) chatInput.value = '';
      if (sendButton) sendButton.disabled = true;

      try {
        const response = await fetch('/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            query, 
            thread_id: AppState.currentThreadId 
          })
        });

        if (response.status === 401 || response.status === 403) {
          MessageRenderer.removeLoadingMessage(loadingId);
          AuthManager.showAuthOverlay();
          Utils.showToast('Session expired. Please login again.');
          return;
        }

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        MessageRenderer.removeLoadingMessage(loadingId);
        
        if (data.thread_id) {
          AppState.currentThreadId = data.thread_id;
          Utils.updateShareLink(AppState.currentThreadId);
        }
        
        MessageRenderer.addBotResponse(data);
        
      } catch (error) {
        MessageRenderer.removeLoadingMessage(loadingId);
        let errorMessage = 'Sorry, I encountered an error. Please try again.';
        
        if (String(error.message).includes('Failed to fetch')) {
          errorMessage = 'Network error. Please check your connection and try again.';
        }
        
        MessageRenderer.addMessage('bot', errorMessage);
        console.error('Send message error:', error);
      } finally {
        if (sendButton) sendButton.disabled = false;
        if (chatInput) chatInput.focus();
      }
    }
  };

  // ===== GLOBAL FUNCTIONS =====
  window.askQuestion = function(question) {
    if (!AppState.serverUser?.is_authenticated) {
      AuthManager.showAuthOverlay();
      Utils.showToast('Please login to ask questions');
      return;
    }
    
    const chatInput = $('chatInput');
    if (chatInput) {
      chatInput.value = question;
      NetworkManager.sendMessage();
    }
  };

  window.sendMessage = NetworkManager.sendMessage;
  window.openVideoModal = VideoModalHandler.openVideoModal.bind(VideoModalHandler);
  window.closeVideoModal = VideoModalHandler.closeVideoModal.bind(VideoModalHandler);
  window.removeSavedMessage = SavedMessagesManager.removeMessage.bind(SavedMessagesManager);

  // ===== EVENT LISTENERS =====
  function setupEventListeners() {
    // Send message events
    const sendButton = $('sendButton');
    const chatInput = $('chatInput');
    
    sendButton?.addEventListener('click', NetworkManager.sendMessage);
    chatInput?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        NetworkManager.sendMessage();
      }
    });

    // New thread
    const newThreadBtn = $('newThreadBtn');
    newThreadBtn?.addEventListener('click', ThreadManager.startNewThread);

    // Clear saved messages
    const clearSavedBtn = $('clearSavedBtn');
    clearSavedBtn?.addEventListener('click', SavedMessagesManager.clearAll);

    // Global keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        $('videoModal')?.classList.remove('active');
        $('shareModal')?.classList.remove('active');
      }
    });

    // Modal close events
    document.addEventListener('click', (e) => {
      if (e.target.classList?.contains('modal-overlay')) {
        e.target.classList.remove('active');
      }
    });

    // Storage change listener for auth sync
    window.addEventListener('storage', (e) => {
      if (e.key === 'auth_change') {
        setTimeout(() => location.reload(), 1000);
      }
    });

    // Before unload cleanup
    window.addEventListener('beforeunload', () => {
      AuthManager.stopPeriodicAuthCheck();
    });
  }

  // ===== PUBLIC API =====
  window.app = window.app || {};
  window.app.state = AppState;
  window.app.util = Utils;
  window.app.auth = AuthManager;
  window.app.render = MessageRenderer;
  window.app.saved = SavedMessagesManager;
  window.app.video = VideoModalHandler;

  // ===== INITIALIZATION =====
  function initialize() {
    try {
      ThemeManager.init();
      setupEventListeners();
      AuthManager.checkAuthentication();
      SavedMessagesManager.loadSavedMessages();
      Utils.updateShareLink(AppState.currentThreadId);
      
      if ($('chatInput') && AppState.serverUser?.is_authenticated) {
        $('chatInput').focus();
      }
      
      console.log('DSA Mentor Auth module loaded successfully');
    } catch (error) {
      console.error('Failed to initialize app-auth:', error);
      Utils.showToast('Initialization failed');
    }
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
  } else {
    initialize();
  }

})();
