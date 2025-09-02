// ===== DSA MENTOR - UPDATED AUTH SYSTEM =====
(() => {
  'use strict';

  // ===== CORE UTILITIES =====
  const $ = (id) => document.getElementById(id);
  const $$ = (selector) => document.querySelectorAll(selector);

  const Utils = {
    escapeHtml(text) {
      if (!text) return '';
      return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    },

    generateThreadId() {
      const timestamp = Date.now();
      const random = Math.random().toString(36).substring(2, 11);
      return `thread_${timestamp}_${random}`;
    },

    scrollToBottom(smooth = true) {
      const behavior = smooth ? 'smooth' : 'auto';
      window.scrollTo({
        top: document.documentElement.scrollHeight,
        behavior: behavior
      });
    },

    showToast(message, type = 'info', duration = 3000) {
      const toast = $('toast');
      if (!toast) return;

      toast.textContent = message;
      toast.className = `toast show ${type}`;
      
      setTimeout(() => {
        toast.classList.remove('show');
      }, duration);
    },

    updateShareLink(threadId) {
      const shareLink = $('shareLink');
      if (shareLink && threadId) {
        const currentDomain = window.location.origin;
        shareLink.value = `${currentDomain}/chat/${threadId}`;
      }
    },

    formatError(error) {
      if (typeof error === 'string') return error;
      if (error?.message) return error.message;
      return 'An unexpected error occurred';
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

  // ===== APPLICATION STATE =====
  const AppState = {
    isFirstMessage: true,
    savedMessages: new Map(),
    currentThreadId: Utils.generateThreadId(),
    authCheckInterval: null,
    serverUser: window.SERVER_USER || { is_authenticated: false },
    isInitialized: false,
    authCheckInProgress: false,
    config: window.APP_CONFIG || {}
  };

  // ===== STORAGE MANAGER =====
  const StorageManager = {
    keys: {
      USER_DATA: 'dsa_user_data',
      THEME: 'dsa_theme',
      SAVED_MESSAGES: 'dsa_saved_messages',
      AUTH_TIMESTAMP: 'dsa_auth_check'
    },

    get(key, defaultValue = null) {
      try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
      } catch (error) {
        console.warn('Storage get error:', error);
        return defaultValue;
      }
    },

    set(key, value) {
      try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
      } catch (error) {
        console.warn('Storage set error:', error);
        return false;
      }
    },

    remove(key) {
      try {
        localStorage.removeItem(key);
        return true;
      } catch (error) {
        console.warn('Storage remove error:', error);
        return false;
      }
    },

    clear() {
      try {
        Object.values(this.keys).forEach(key => {
          localStorage.removeItem(key);
        });
        return true;
      } catch (error) {
        console.warn('Storage clear error:', error);
        return false;
      }
    }
  };

  // ===== AUTHENTICATION MANAGER =====
  const AuthManager = {
    init() {
      this.loadStoredUser();
      this.checkAuthentication();
      this.setupEventListeners();
    },

    loadStoredUser() {
      const storedUser = StorageManager.get(StorageManager.keys.USER_DATA);
      if (storedUser && storedUser.is_authenticated && storedUser.name && storedUser.email) {
        // Update server user data if not already set
        if (!AppState.serverUser.is_authenticated) {
          AppState.serverUser = {
            is_authenticated: true,
            id: storedUser.id || storedUser.user_id,
            name: storedUser.name,
            email: storedUser.email,
            picture: storedUser.picture
          };
        }
      }
    },

    setupEventListeners() {
      // Listen for auth changes across tabs
      window.addEventListener('storage', (e) => {
        if (e.key === StorageManager.keys.USER_DATA) {
          this.handleAuthChange();
        }
      });

      // Visibility change - recheck auth when tab becomes visible
      document.addEventListener('visibilitychange', () => {
        if (!document.hidden && AppState.serverUser?.is_authenticated) {
          this.performAuthCheck(true);
        }
      });
    },

    checkAuthentication() {
      const user = AppState.serverUser;
      
      if (user?.is_authenticated && user.name && user.email) {
        this.authenticatedState();
        return true;
      }

      const isSharedView = document.body.getAttribute('data-shared-view') === 'true';
      const sharedThreadId = document.body.getAttribute('data-shared-thread-id');

      if (isSharedView && sharedThreadId && sharedThreadId !== 'null') {
        this.sharedViewState();
      } else {
        this.unauthenticatedState();
      }

      return false;
    },

    authenticatedState() {
      this.hideAuthOverlay();
      this.hideSharedThreadBanner();
      this.updateUserProfile(AppState.serverUser);
      this.enableChatInterface();
      this.startPeriodicAuthCheck();
      
      // Store user data
      StorageManager.set(StorageManager.keys.USER_DATA, AppState.serverUser);
      
      console.log('✅ User authenticated:', AppState.serverUser.email);
    },

    unauthenticatedState() {
      this.showAuthOverlay();
      this.hideSharedThreadBanner();
      this.disableChatInterface();
      this.stopPeriodicAuthCheck();
      
      // Clear stored data
      StorageManager.remove(StorageManager.keys.USER_DATA);
      
      console.log('🔒 User not authenticated');
    },

    sharedViewState() {
      this.hideAuthOverlay();
      this.showSharedThreadBanner();
      this.disableChatInterface();
      this.stopPeriodicAuthCheck();
      
      console.log('👥 Shared view mode');
    },

    showAuthOverlay() {
      const overlay = $('authOverlay');
      if (overlay) {
        overlay.classList.add('active');
        // Focus management for accessibility
        setTimeout(() => {
          const loginBtn = overlay.querySelector('.login-btn');
          if (loginBtn) loginBtn.focus();
        }, 100);
      }
    },

    hideAuthOverlay() {
      const overlay = $('authOverlay');
      if (overlay) {
        overlay.classList.remove('active');
      }
    },

    showSharedThreadBanner() {
      const banner = $('sharedThreadBanner');
      if (banner) {
        banner.style.display = 'block';
        // Adjust main content margin
        const mainContent = document.querySelector('.main-content');
        if (mainContent) {
          mainContent.style.marginTop = '80px';
        }
      }
    },

    hideSharedThreadBanner() {
      const banner = $('sharedThreadBanner');
      if (banner) {
        banner.style.display = 'none';
        // Reset main content margin
        const mainContent = document.querySelector('.main-content');
        if (mainContent) {
          mainContent.style.marginTop = '0';
        }
      }
    },

    updateUserProfile(user) {
      const avatar = document.querySelector('.profile-avatar');
      const name = document.querySelector('.profile-name');
      const status = document.querySelector('.profile-status');

      if (avatar && user.name) {
        avatar.textContent = user.name.charAt(0).toUpperCase();
        avatar.style.background = 'var(--primary-gradient)';
      }

      if (name && user.name) {
        name.textContent = user.name;
      }

      if (status) {
        if (user.email) {
          status.textContent = user.email;
        } else {
          status.textContent = 'Authenticated';
        }
      }
    },

    enableChatInterface() {
      const chatInput = $('chatInput');
      const sendButton = $('sendButton');
      const suggestionCards = $$('.suggestion-card');

      if (chatInput) {
        chatInput.disabled = false;
        chatInput.placeholder = 'Ask me anything about Data Structures and Algorithms...';
      }

      if (sendButton) {
        sendButton.disabled = false;
      }

      // Enable suggestion cards
      suggestionCards.forEach(card => {
        card.style.pointerEvents = 'auto';
        card.style.opacity = '1';
      });
    },

    disableChatInterface() {
      const chatInput = $('chatInput');
      const sendButton = $('sendButton');
      const suggestionCards = $$('.suggestion-card');

      if (chatInput) {
        chatInput.disabled = true;
        chatInput.placeholder = 'Sign in to start learning...';
      }

      if (sendButton) {
        sendButton.disabled = true;
      }

      // Disable suggestion cards
      suggestionCards.forEach(card => {
        card.style.pointerEvents = 'none';
        card.style.opacity = '0.6';
      });
    },

    startPeriodicAuthCheck() {
      if (AppState.authCheckInterval) {
        clearInterval(AppState.authCheckInterval);
      }

      // Check auth every 5 minutes
      AppState.authCheckInterval = setInterval(() => {
        this.performAuthCheck();
      }, 300000); // 5 minutes
    },

    stopPeriodicAuthCheck() {
      if (AppState.authCheckInterval) {
        clearInterval(AppState.authCheckInterval);
        AppState.authCheckInterval = null;
      }
    },

    async performAuthCheck(force = false) {
      // Prevent concurrent auth checks
      if (AppState.authCheckInProgress && !force) {
        console.log('Auth check already in progress, skipping...');
        return;
      }

      AppState.authCheckInProgress = true;

      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout

        const response = await fetch('/auth-status', {
          method: 'GET',
          credentials: 'same-origin',
          signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          console.warn('Auth check failed:', response.status);
          return;
        }

        const data = await response.json();
        const wasAuthenticated = AppState.serverUser?.is_authenticated;
        const nowAuthenticated = data.is_authenticated;

        // Handle authentication state changes
        if (wasAuthenticated !== nowAuthenticated) {
          console.log('Authentication status changed:', { 
            was: wasAuthenticated, 
            now: nowAuthenticated 
          });

          if (!nowAuthenticated) {
            console.log('User logged out, updating state...');
            AppState.serverUser = { is_authenticated: false };
            this.checkAuthentication();
            Utils.showToast('You have been logged out', 'warning');
          } else {
            console.log('User logged in, updating state...');
            AppState.serverUser = {
              is_authenticated: true,
              id: data.user_id,
              name: data.name,
              email: data.email,
              picture: data.picture
            };
            this.checkAuthentication();
            Utils.showToast('Welcome back!', 'success');
          }
          return;
        }

        // Handle user ID changes (different user logged in)
        if (nowAuthenticated && AppState.serverUser?.id && data.user_id && 
            AppState.serverUser.id !== data.user_id) {
          console.log('Different user logged in, updating state...');
          AppState.serverUser = {
            is_authenticated: true,
            id: data.user_id,
            name: data.name,
            email: data.email,
            picture: data.picture
          };
          this.updateUserProfile(AppState.serverUser);
          StorageManager.set(StorageManager.keys.USER_DATA, AppState.serverUser);
        }

      } catch (error) {
        if (error.name === 'AbortError') {
          console.warn('Auth check timed out');
        } else {
          console.error('Auth check failed:', error);
        }
      } finally {
        AppState.authCheckInProgress = false;
      }
    },

    async forceAuthCheck() {
      try {
        const response = await fetch('/auth-status', {
          method: 'GET',
          credentials: 'same-origin'
        });

        if (response.ok) {
          const data = await response.json();
          if (data.is_authenticated) {
            AppState.serverUser = {
              is_authenticated: true,
              id: data.user_id,
              name: data.name,
              email: data.email,
              picture: data.picture
            };
            this.checkAuthentication();
          }
        }
      } catch (error) {
        console.error('Force auth check failed:', error);
      }
    },

    handleAuthChange() {
      console.log('Auth change detected across tabs');
      this.loadStoredUser();
      this.checkAuthentication();
    },

    async logout() {
      try {
        const response = await fetch('/logout', {
          method: 'POST',
          credentials: 'same-origin'
        });

        if (response.ok) {
          AppState.serverUser = { is_authenticated: false };
          this.checkAuthentication();
          StorageManager.clear();
          Utils.showToast('Logged out successfully', 'info');
        } else {
          throw new Error('Logout failed');
        }
      } catch (error) {
        console.error('Logout error:', error);
        Utils.showToast('Logout failed', 'error');
      }
    },

    isAuthenticated() {
      return AppState.serverUser?.is_authenticated === true;
    }
  };

  // ===== THEME MANAGER =====
  const ThemeManager = {
    init() {
      const savedTheme = StorageManager.get(StorageManager.keys.THEME, 'light');
      this.applyTheme(savedTheme);
      this.setupThemeToggle();
    },

    setupThemeToggle() {
      const themeToggle = $('themeToggle');
      if (themeToggle) {
        themeToggle.addEventListener('click', () => {
          this.toggleTheme();
        });
      }
    },

    toggleTheme() {
      const currentTheme = document.body.getAttribute('data-theme') || 'light';
      const newTheme = currentTheme === 'light' ? 'dark' : 'light';
      this.applyTheme(newTheme);
    },

    applyTheme(theme) {
      document.body.setAttribute('data-theme', theme);
      StorageManager.set(StorageManager.keys.THEME, theme);

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

      // Update theme color meta tag
      const themeColorMeta = document.querySelector('meta[name="theme-color"]');
      if (themeColorMeta) {
        themeColorMeta.content = theme === 'dark' ? '#111827' : '#1B7EFE';
      }
    },

    getCurrentTheme() {
      return document.body.getAttribute('data-theme') || 'light';
    }
  };

  // ===== SIDEBAR MANAGER =====
  const SidebarManager = {
    init() {
      this.setupMobileMenuToggle();
      this.setupSidebarInteractions();
      this.setupNewThreadButton();
    },

    setupMobileMenuToggle() {
      const mobileMenuBtn = $('mobileMenuBtn');
      const sidebar = $('sidebar');
      const overlay = $('sidebarOverlay');

      if (mobileMenuBtn && sidebar && overlay) {
        mobileMenuBtn.addEventListener('click', () => {
          this.toggleSidebar();
        });

        overlay.addEventListener('click', () => {
          this.closeSidebar();
        });
      }
    },

    setupSidebarInteractions() {
      // Handle escape key to close sidebar
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          this.closeSidebar();
        }
      });
    },

    setupNewThreadButton() {
      const newThreadBtn = $('newThreadBtn');
      if (newThreadBtn) {
        newThreadBtn.addEventListener('click', () => {
          this.startNewThread();
        });
      }
    },

    toggleSidebar() {
      const sidebar = $('sidebar');
      const overlay = $('sidebarOverlay');
      const isOpen = sidebar?.classList.contains('open');

      if (isOpen) {
        this.closeSidebar();
      } else {
        this.openSidebar();
      }
    },

    openSidebar() {
      const sidebar = $('sidebar');
      const overlay = $('sidebarOverlay');

      sidebar?.classList.add('open');
      overlay?.classList.add('active');
      document.body.classList.add('sidebar-open');

      // Focus management
      setTimeout(() => {
        const firstFocusable = sidebar?.querySelector('button, [tabindex]:not([tabindex="-1"])');
        if (firstFocusable) {
          firstFocusable.focus();
        }
      }, 100);
    },

    closeSidebar() {
      const sidebar = $('sidebar');
      const overlay = $('sidebarOverlay');

      sidebar?.classList.remove('open');
      overlay?.classList.remove('active');
      document.body.classList.remove('sidebar-open');
    },

    startNewThread() {
      // Generate new thread ID
      AppState.currentThreadId = Utils.generateThreadId();
      
      // Clear chat content
      const chatContent = $('chatContent');
      if (chatContent) {
        chatContent.innerHTML = '';
      }

      // Show welcome screen
      const welcomeScreen = $('welcomeScreen');
      if (welcomeScreen) {
        welcomeScreen.style.display = 'block';
      }

      // Reset first message flag
      AppState.isFirstMessage = true;

      // Clear chat input
      const chatInput = $('chatInput');
      if (chatInput) {
        chatInput.value = '';
        chatInput.focus();
      }

      // Close sidebar on mobile
      this.closeSidebar();

      Utils.showToast('Started new conversation', 'success');
    }
  };

  // ===== SAVED MESSAGES MANAGER =====
  const SavedMessagesManager = {
    init() {
      this.loadSavedMessages();
      this.setupClearButton();
    },

    loadSavedMessages() {
      const saved = StorageManager.get(StorageManager.keys.SAVED_MESSAGES, []);
      AppState.savedMessages = new Map(saved.map(item => [item.id, item]));
      this.renderSavedMessages();
    },

    saveMessage(messageId, content, title) {
      const message = {
        id: messageId,
        title: title || content.substring(0, 50) + '...',
        content: content,
        timestamp: Date.now(),
        threadId: AppState.currentThreadId
      };

      AppState.savedMessages.set(messageId, message);
      this.persistSavedMessages();
      this.renderSavedMessages();
      Utils.showToast('Message saved', 'success');
    },

    removeSavedMessage(messageId) {
      if (AppState.savedMessages.delete(messageId)) {
        this.persistSavedMessages();
        this.renderSavedMessages();
        Utils.showToast('Message removed', 'info');
      }
    },

    clearAllSaved() {
      if (AppState.savedMessages.size === 0) return;

      if (confirm('Are you sure you want to clear all saved messages?')) {
        AppState.savedMessages.clear();
        this.persistSavedMessages();
        this.renderSavedMessages();
        Utils.showToast('All saved messages cleared', 'info');
      }
    },

    persistSavedMessages() {
      const messagesArray = Array.from(AppState.savedMessages.values());
      StorageManager.set(StorageManager.keys.SAVED_MESSAGES, messagesArray);
    },

    renderSavedMessages() {
      const savedList = $('savedList');
      const clearBtn = $('clearSavedBtn');
      
      if (!savedList) return;

      const messages = Array.from(AppState.savedMessages.values())
        .sort((a, b) => b.timestamp - a.timestamp);

      if (messages.length === 0) {
        savedList.innerHTML = `
          <div class="empty-saved">
            <div class="empty-saved-icon">📝</div>
            <p>No saved messages yet</p>
            <p>Save important conversations for later</p>
          </div>
        `;
        if (clearBtn) clearBtn.style.display = 'none';
        return;
      }

      savedList.innerHTML = messages.map(message => `
        <div class="saved-item" onclick="SavedMessagesManager.loadSavedMessage('${message.id}')">
          <div class="saved-item-content">
            <div class="saved-item-title">${Utils.escapeHtml(message.title)}</div>
            <div class="saved-item-preview">${Utils.escapeHtml(message.content.substring(0, 100))}</div>
          </div>
          <button class="saved-item-delete" onclick="event.stopPropagation(); SavedMessagesManager.removeSavedMessage('${message.id}')" title="Delete saved message">
            ✕
          </button>
        </div>
      `).join('');

      if (clearBtn) clearBtn.style.display = 'block';
    },

    loadSavedMessage(messageId) {
      const message = AppState.savedMessages.get(messageId);
      if (message) {
        // This would typically load the saved conversation
        // For now, just show the content
        Utils.showToast('Loading saved message...', 'info');
        console.log('Loading saved message:', message);
      }
    },

    setupClearButton() {
      const clearBtn = $('clearSavedBtn');
      if (clearBtn) {
        clearBtn.addEventListener('click', () => {
          this.clearAllSaved();
        });
      }
    }
  };

  // ===== MESSAGE RENDERER =====
  const MessageRenderer = {
    addMessage(sender, content, messageId = null) {
      const chatContent = $('chatContent');
      if (!chatContent) return null;

      const id = messageId || `message-${AppState.currentThreadId}-${Date.now()}`;
      const messageDiv = document.createElement('div');
      messageDiv.className = `message ${sender}-message`;
      messageDiv.id = id;

      if (sender === 'user') {
        messageDiv.innerHTML = `
          <div class="message-content">${Utils.escapeHtml(content)}</div>
        `;
      } else {
        messageDiv.innerHTML = this.getBotMessageHTML(id, content);
      }

      chatContent.appendChild(messageDiv);
      Utils.scrollToBottom();
      return id;
    },

    addBotMessage(content, messageId) {
      const chatContent = $('chatContent');
      if (!chatContent) return null;

      const id = messageId || `msg-${Date.now()}`;
      const messageDiv = document.createElement('div');
      messageDiv.className = 'message bot-message';
      messageDiv.id = id;
      messageDiv.innerHTML = this.getBotMessageHTML(id, content);

      chatContent.appendChild(messageDiv);
      Utils.scrollToBottom();
      return id;
    },

    getBotMessageHTML(messageId, content = '') {
      return `
        <div class="message-content">${content}</div>
        <div class="message-actions">
          <button class="action-btn" onclick="MessageRenderer.copyMessage('${messageId}')" title="Copy message">
            📋
          </button>
          <button class="action-btn" onclick="MessageRenderer.saveMessage('${messageId}')" title="Save message">
            💾
          </button>
          <button class="action-btn" onclick="MessageRenderer.shareMessage('${messageId}')" title="Share message">
            🔗
          </button>
        </div>
      `;
    },

    copyMessage(messageId) {
      const messageElement = $(messageId);
      if (!messageElement) return;

      const content = messageElement.querySelector('.message-content');
      if (!content) return;

      const text = content.textContent || content.innerText;
      
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
          Utils.showToast('Message copied to clipboard', 'success');
        }).catch(err => {
          console.error('Copy failed:', err);
          this.fallbackCopy(text);
        });
      } else {
        this.fallbackCopy(text);
      }
    },

    fallbackCopy(text) {
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      textArea.style.top = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      
      try {
        document.execCommand('copy');
        Utils.showToast('Message copied to clipboard', 'success');
      } catch (err) {
        console.error('Fallback copy failed:', err);
        Utils.showToast('Copy failed', 'error');
      }
      
      document.body.removeChild(textArea);
    },

    saveMessage(messageId) {
      const messageElement = $(messageId);
      if (!messageElement) return;

      const content = messageElement.querySelector('.message-content');
      if (!content) return;

      const text = content.textContent || content.innerText;
      const title = text.substring(0, 50) + (text.length > 50 ? '...' : '');

      SavedMessagesManager.saveMessage(messageId, text, title);
    },

    shareMessage(messageId) {
      // This would implement message sharing functionality
      Utils.showToast('Share functionality coming soon', 'info');
    }
  };

  // ===== GLOBAL APP OBJECT =====
  window.app = {
    state: AppState,
    util: Utils,
    auth: AuthManager,
    theme: ThemeManager,
    sidebar: SidebarManager,
    saved: SavedMessagesManager,
    render: MessageRenderer,
    storage: StorageManager
  };

  // ===== INITIALIZATION =====
  document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 DSA Mentor initializing...');
    
    try {
      // Initialize all managers
      ThemeManager.init();
      AuthManager.init();
      SidebarManager.init();
      SavedMessagesManager.init();

      // Force initial auth check
      setTimeout(() => {
        AuthManager.forceAuthCheck();
      }, 500);

      AppState.isInitialized = true;
      console.log('✅ DSA Mentor initialized successfully');
      
    } catch (error) {
      console.error('❌ DSA Mentor initialization failed:', error);
      Utils.showToast('Initialization failed', 'error');
    }
  });

  // ===== ERROR HANDLING =====
  window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
  });

  window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
  });

})();
