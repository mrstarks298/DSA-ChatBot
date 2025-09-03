// ===== DSA MENTOR - ENHANCED AUTHENTICATION SYSTEM WITH SESSION PERSISTENCE =====
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
            if (!toast) {
                console.warn('Toast element not found');
                return;
            }
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
        },

        // ✅ NEW: Enhanced error logging with context
        logError(context, error, additionalInfo = {}) {
            const errorDetails = {
                context,
                error: this.formatError(error),
                timestamp: new Date().toISOString(),
                userAgent: navigator.userAgent,
                url: window.location.href,
                ...additionalInfo
            };
            console.error(`❌ [${context}]`, errorDetails);
            return errorDetails;
        },

        // ✅ NEW: Network status detection
        isOnline() {
            return navigator.onLine;
        },

        // ✅ NEW: Retry mechanism for failed requests
        async retryRequest(requestFn, maxRetries = 3, delay = 1000) {
            for (let attempt = 1; attempt <= maxRetries; attempt++) {
                try {
                    const result = await requestFn();
                    return result;
                } catch (error) {
                    if (attempt === maxRetries) {
                        throw error;
                    }
                    console.warn(`Request failed (attempt ${attempt}/${maxRetries}), retrying in ${delay}ms...`);
                    await new Promise(resolve => setTimeout(resolve, delay * attempt));
                }
            }
        }
    };

    // ===== APPLICATION STATE =====
    const AppState = {
        isFirstMessage: true,
        savedMessages: new Map(),
        currentThreadId: Utils.generateThreadId(),
        authCheckInterval: null,
        reconnectInterval: null,
        serverUser: window.SERVER_USER || { is_authenticated: false },
        isInitialized: false,
        authCheckInProgress: false,
        lastAuthCheck: 0,
        config: window.APP_CONFIG || {},
        connectionStatus: 'unknown', // 'online', 'offline', 'checking'
        sessionMetrics: {
            authChecks: 0,
            authFailures: 0,
            sessionRestored: 0,
            loginAttempts: 0
        }
    };

    // ===== ENHANCED STORAGE MANAGER =====
    const StorageManager = {
        keys: {
            USER_DATA: 'dsa_user_data',
            THEME: 'dsa_theme',
            SAVED_MESSAGES: 'dsa_saved_messages',
            AUTH_TIMESTAMP: 'dsa_auth_check',
            SESSION_BACKUP: 'dsa_session_backup',
            CONNECTION_STATUS: 'dsa_connection_status'
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
        },

        // ✅ NEW: Session backup and restore
        backupSession() {
            if (AppState.serverUser?.is_authenticated) {
                const backup = {
                    user: AppState.serverUser,
                    timestamp: Date.now(),
                    threadId: AppState.currentThreadId
                };
                return this.set(this.keys.SESSION_BACKUP, backup);
            }
            return false;
        },

        restoreSession() {
            const backup = this.get(this.keys.SESSION_BACKUP);
            if (backup && backup.user && backup.timestamp) {
                // Check if backup is not too old (24 hours)
                const isValid = (Date.now() - backup.timestamp) < 24 * 60 * 60 * 1000;
                if (isValid) {
                    AppState.serverUser = backup.user;
                    if (backup.threadId) {
                        AppState.currentThreadId = backup.threadId;
                    }
                    AppState.sessionMetrics.sessionRestored++;
                    return true;
                }
            }
            return false;
        }
    };

    // ===== ENHANCED AUTHENTICATION MANAGER =====
    const AuthManager = {
        init() {
            this.loadStoredUser();
            this.setupConnectionMonitoring();
            this.checkAuthentication();
            this.setupEventListeners();
        },

        loadStoredUser() {
            // Try to restore from session backup first
            if (StorageManager.restoreSession()) {
                console.log('✅ Session restored from backup');
            } else {
                // Fallback to regular stored user
                const storedUser = StorageManager.get(StorageManager.keys.USER_DATA);
                if (storedUser && storedUser.is_authenticated && storedUser.name && storedUser.email) {
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
            }
        },

        // ✅ NEW: Connection monitoring
        setupConnectionMonitoring() {
            window.addEventListener('online', () => {
                AppState.connectionStatus = 'online';
                console.log('🌐 Connection restored');
                Utils.showToast('Connection restored', 'success');
                // Perform auth check when coming back online
                if (AppState.serverUser?.is_authenticated) {
                    this.performAuthCheck(true);
                }
            });

            window.addEventListener('offline', () => {
                AppState.connectionStatus = 'offline';
                console.log('📡 Connection lost');
                Utils.showToast('Connection lost. Working offline...', 'warning', 5000);
                this.stopPeriodicAuthCheck();
            });

            // Initial connection status
            AppState.connectionStatus = navigator.onLine ? 'online' : 'offline';
        },

        setupEventListeners() {
            // Cross-tab communication
            window.addEventListener('storage', (e) => {
                if (e.key === StorageManager.keys.USER_DATA) {
                    this.handleAuthChange();
                }
            });

            // Page visibility changes
            document.addEventListener('visibilitychange', () => {
                if (!document.hidden && AppState.serverUser?.is_authenticated) {
                    // Throttle auth checks - only if last check was more than 30 seconds ago
                    const now = Date.now();
                    if (now - AppState.lastAuthCheck > 30000) {
                        this.performAuthCheck(true);
                    }
                }
            });

            // Window focus events
            window.addEventListener('focus', () => {
                if (AppState.serverUser?.is_authenticated && navigator.onLine) {
                    // Perform auth check when window gains focus
                    this.performAuthCheck(true);
                }
            });

            // ✅ NEW: Handle page unload - backup session
            window.addEventListener('beforeunload', () => {
                StorageManager.backupSession();
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
            
            // Store user data and create backup
            StorageManager.set(StorageManager.keys.USER_DATA, AppState.serverUser);
            StorageManager.backupSession();
            
            console.log('✅ User authenticated:', AppState.serverUser.email);
        },

        unauthenticatedState() {
            this.showAuthOverlay();
            this.hideSharedThreadBanner();
            this.disableChatInterface();
            this.stopPeriodicAuthCheck();

            StorageManager.remove(StorageManager.keys.USER_DATA);
            StorageManager.remove(StorageManager.keys.SESSION_BACKUP);
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
                avatar.title = user.name;
            }

            if (name && user.name) {
                name.textContent = user.name;
                name.title = user.email;
            }

            if (status) {
                status.textContent = user.email || 'Authenticated';
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

            suggestionCards.forEach(card => {
                card.style.pointerEvents = 'none';
                card.style.opacity = '0.6';
            });
        },

        // ✅ ENHANCED: Smart periodic auth checks
        startPeriodicAuthCheck() {
            if (AppState.authCheckInterval) {
                clearInterval(AppState.authCheckInterval);
            }
            
            // Variable intervals based on activity and connection status
            const getCheckInterval = () => {
                if (!navigator.onLine) return 300000; // 5 minutes when offline
                if (document.hidden) return 300000; // 5 minutes when tab is hidden
                return 120000; // 2 minutes when active
            };

            AppState.authCheckInterval = setInterval(() => {
                if (navigator.onLine && AppState.serverUser?.is_authenticated) {
                    this.performAuthCheck();
                }
            }, getCheckInterval());

            // Adjust interval based on visibility changes
            document.addEventListener('visibilitychange', () => {
                if (AppState.authCheckInterval) {
                    clearInterval(AppState.authCheckInterval);
                    AppState.authCheckInterval = setInterval(() => {
                        if (navigator.onLine && AppState.serverUser?.is_authenticated) {
                            this.performAuthCheck();
                        }
                    }, getCheckInterval());
                }
            });
        },

        stopPeriodicAuthCheck() {
            if (AppState.authCheckInterval) {
                clearInterval(AppState.authCheckInterval);
                AppState.authCheckInterval = null;
            }
        },

        // ✅ ENHANCED: Auth check with improved error handling and retry logic
        async performAuthCheck(force = false) {
            if (AppState.authCheckInProgress && !force) {
                console.log('Auth check already in progress, skipping...');
                return;
            }

            // Check if we're offline
            if (!navigator.onLine) {
                console.log('Offline, skipping auth check');
                return;
            }

            AppState.authCheckInProgress = true;
            AppState.sessionMetrics.authChecks++;
            
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 15000); // Increased timeout

                // ✅ CRITICAL: Include credentials and comprehensive headers for session cookies
                const response = await fetch('/auth/auth-status', {
                    method: 'GET',
                    credentials: 'same-origin',  // Essential for session cookies
                    cache: 'no-cache',           // Don't cache auth responses
                    signal: controller.signal,
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                clearTimeout(timeoutId);
                AppState.lastAuthCheck = Date.now();

                if (!response.ok) {
                    AppState.sessionMetrics.authFailures++;
                    console.warn('Auth check failed:', response.status);
                    
                    if (response.status === 401) {
                        // Session expired or invalid
                        if (AppState.serverUser?.is_authenticated) {
                            AppState.serverUser = { is_authenticated: false };
                            this.checkAuthentication();
                            Utils.showToast('Session expired. Please log in again.', 'warning');
                        }
                    } else if (response.status >= 500) {
                        // Server error - don't invalidate session, just log
                        console.warn('Server error during auth check, maintaining current state');
                    }
                    return;
                }

                const data = await response.json();
                const wasAuthenticated = AppState.serverUser?.is_authenticated;
                const nowAuthenticated = data.is_authenticated;

                console.log('Auth check result:', { 
                    wasAuthenticated, 
                    nowAuthenticated, 
                    email: data.email,
                    userId: data.user_id 
                });

                // Handle authentication state changes
                if (wasAuthenticated !== nowAuthenticated) {
                    console.log('Authentication status changed:', { was: wasAuthenticated, now: nowAuthenticated });
                    
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
                    StorageManager.backupSession();
                }

                // ✅ IMPORTANT: Update stored user data if authenticated
                if (nowAuthenticated && data.email) {
                    const userData = {
                        is_authenticated: true,
                        id: data.user_id,
                        name: data.name,
                        email: data.email,
                        picture: data.picture
                    };
                    StorageManager.set(StorageManager.keys.USER_DATA, userData);
                    StorageManager.backupSession();
                }

            } catch (error) {
                AppState.sessionMetrics.authFailures++;
                
                if (error.name === 'AbortError') {
                    console.warn('Auth check timed out');
                    Utils.showToast('Connection timeout, retrying...', 'warning', 2000);
                } else {
                    Utils.logError('Auth Check Failed', error, {
                        wasAuthenticated: AppState.serverUser?.is_authenticated,
                        connectionStatus: AppState.connectionStatus,
                        authChecks: AppState.sessionMetrics.authChecks
                    });
                    
                    // Only show error if we're online and this wasn't a network issue
                    if (navigator.onLine && !error.message.includes('fetch')) {
                        Utils.showToast('Authentication check failed', 'error', 2000);
                    }
                }
            } finally {
                AppState.authCheckInProgress = false;
            }
        },

        // ✅ ENHANCED: Logout with improved error handling
        async logout() {
            try {
                const wasAuthenticated = AppState.serverUser?.is_authenticated;
                const userEmail = AppState.serverUser?.email;
                
                // Clear state immediately for better UX
                AppState.serverUser = { is_authenticated: false };
                this.checkAuthentication();
                StorageManager.clear();
                
                // Attempt server-side logout
                const response = await fetch('/auth/logout', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                if (response.ok) {
                    console.log(`✅ Logout successful for user: ${userEmail}`);
                    Utils.showToast('Logged out successfully', 'info');
                } else {
                    console.warn('Server logout failed, but local state cleared');
                    Utils.showToast('Logged out (local)', 'info');
                }
            } catch (error) {
                console.error('Logout error:', error);
                // Even if server logout fails, we've cleared local state
                Utils.showToast('Logged out (connection error)', 'warning');
            }
        },

        handleAuthChange() {
            console.log('Auth change detected across tabs');
            this.loadStoredUser();
            this.checkAuthentication();
        },

        isAuthenticated() {
            return AppState.serverUser?.is_authenticated === true;
        },

        // ✅ ENHANCED: Debug function with comprehensive session info
        async debugSession() {
            try {
                const response = await fetch('/auth/session-debug', {
                    method: 'GET',
                    credentials: 'same-origin',
                    cache: 'no-cache'
                });
                
                if (response.ok) {
                    const serverData = await response.json();
                    const debugInfo = {
                        serverData,
                        clientState: {
                            serverUser: AppState.serverUser,
                            isAuthenticated: this.isAuthenticated(),
                            connectionStatus: AppState.connectionStatus,
                            sessionMetrics: AppState.sessionMetrics,
                            lastAuthCheck: new Date(AppState.lastAuthCheck).toISOString(),
                            authCheckInProgress: AppState.authCheckInProgress
                        },
                        localStorage: {
                            userData: StorageManager.get(StorageManager.keys.USER_DATA),
                            sessionBackup: StorageManager.get(StorageManager.keys.SESSION_BACKUP)
                        },
                        browser: {
                            onLine: navigator.onLine,
                            cookieEnabled: navigator.cookieEnabled,
                            userAgent: navigator.userAgent.substring(0, 100) + '...',
                            timestamp: new Date().toISOString()
                        }
                    };
                    
                    console.log('🔍 Comprehensive Session Debug:', debugInfo);
                    return debugInfo;
                } else {
                    console.error('Session debug failed:', response.status);
                }
            } catch (error) {
                Utils.logError('Session Debug', error);
            }
        },

        // ✅ NEW: Session recovery mechanism
        async attemptSessionRecovery() {
            console.log('🔄 Attempting session recovery...');
            
            try {
                // Try to restore from backup
                if (StorageManager.restoreSession()) {
                    // Validate the restored session
                    const isValid = await this.validateRestoredSession();
                    if (isValid) {
                        console.log('✅ Session recovered successfully');
                        this.checkAuthentication();
                        Utils.showToast('Session recovered', 'success');
                        return true;
                    }
                }
                
                console.log('❌ Session recovery failed');
                return false;
            } catch (error) {
                Utils.logError('Session Recovery', error);
                return false;
            }
        },

        async validateRestoredSession() {
            try {
                const response = await fetch('/auth/auth-status', {
                    method: 'GET',
                    credentials: 'same-origin',
                    cache: 'no-cache'
                });
                
                if (response.ok) {
                    const data = await response.json();
                    return data.is_authenticated && data.email === AppState.serverUser?.email;
                }
                return false;
            } catch (error) {
                console.warn('Session validation failed:', error);
                return false;
            }
        },

        // ✅ NEW: Get session metrics for debugging
        getSessionMetrics() {
            return {
                ...AppState.sessionMetrics,
                uptime: Date.now() - (window.performance?.timing?.loadEventEnd || 0),
                lastAuthCheck: new Date(AppState.lastAuthCheck).toISOString(),
                connectionStatus: AppState.connectionStatus
            };
        }
    };

    // ===== THEME MANAGER =====
    const ThemeManager = {
        init() {
            const savedTheme = StorageManager.get(StorageManager.keys.THEME, 'light');
            this.applyTheme(savedTheme);
            this.setupThemeToggle();
            this.setupSystemThemeDetection();
        },

        setupThemeToggle() {
            const themeToggle = $('themeToggle');
            if (themeToggle) {
                themeToggle.addEventListener('click', () => {
                    this.toggleTheme();
                });
            }
        },

        // ✅ NEW: System theme detection
        setupSystemThemeDetection() {
            if (window.matchMedia) {
                const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
                darkModeQuery.addEventListener('change', (e) => {
                    const storedTheme = StorageManager.get(StorageManager.keys.THEME);
                    // Only auto-switch if user hasn't manually set a theme
                    if (!storedTheme) {
                        this.applyTheme(e.matches ? 'dark' : 'light');
                    }
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
            document.body.setAttribute('data-color-scheme', theme);
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

            const themeColorMeta = document.querySelector('meta[name="theme-color"]');
            if (themeColorMeta) {
                themeColorMeta.content = theme === 'dark' ? '#111827' : '#1B7EFE';
            }

            // Update CSS custom properties if needed
            this.updateThemeProperties(theme);
        },

        updateThemeProperties(theme) {
            const root = document.documentElement;
            if (theme === 'dark') {
                root.style.setProperty('--surface-elevated', 'rgba(255, 255, 255, 0.05)');
            } else {
                root.style.setProperty('--surface-elevated', 'rgba(255, 255, 255, 0.8)');
            }
        },

        getCurrentTheme() {
            return document.body.getAttribute('data-theme') || 'light';
        }
    };

    // ===== ENHANCED SIDEBAR MANAGER =====
    const SidebarManager = {
        init() {
            this.setupMobileMenuToggle();
            this.setupSidebarInteractions();
            this.setupNewThreadButton();
            this.setupSessionInfo();
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

                // Swipe gestures for mobile
                this.setupSwipeGestures(sidebar);
            }
        },

        // ✅ NEW: Swipe gestures for mobile sidebar
        setupSwipeGestures(sidebar) {
            let startX = 0;
            let currentX = 0;

            const handleTouchStart = (e) => {
                startX = e.touches[0].clientX;
            };

            const handleTouchMove = (e) => {
                currentX = e.touches[0].clientX;
            };

            const handleTouchEnd = () => {
                const diffX = startX - currentX;
                if (diffX > 50 && sidebar.classList.contains('open')) {
                    this.closeSidebar();
                } else if (diffX < -50 && !sidebar.classList.contains('open') && startX < 50) {
                    this.openSidebar();
                }
            };

            document.addEventListener('touchstart', handleTouchStart, { passive: true });
            document.addEventListener('touchmove', handleTouchMove, { passive: true });
            document.addEventListener('touchend', handleTouchEnd, { passive: true });
        },

        setupSidebarInteractions() {
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    this.closeSidebar();
                }
            });

            // Click outside to close on desktop
            document.addEventListener('click', (e) => {
                const sidebar = $('sidebar');
                const mobileMenuBtn = $('mobileMenuBtn');
                
                if (sidebar && sidebar.classList.contains('open') && 
                    !sidebar.contains(e.target) && 
                    e.target !== mobileMenuBtn) {
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

        // ✅ NEW: Session information display
        setupSessionInfo() {
            const sessionInfo = $('sessionInfo');
            if (sessionInfo) {
                sessionInfo.addEventListener('click', () => {
                    this.showSessionDetails();
                });
            }
        },

        showSessionDetails() {
            const metrics = AuthManager.getSessionMetrics();
            const details = `Session Details:
• Auth Checks: ${metrics.authChecks}
• Failures: ${metrics.authFailures}
• Connection: ${AppState.connectionStatus}
• Last Check: ${new Date(AppState.lastAuthCheck).toLocaleTimeString()}`;
            
            alert(details);
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
            // Confirm if there's existing content
            const chatContent = $('chatContent');
            if (chatContent && chatContent.children.length > 0) {
                if (!confirm('Start a new conversation? Current chat will be cleared.')) {
                    return;
                }
            }

            AppState.currentThreadId = Utils.generateThreadId();

            if (chatContent) {
                chatContent.innerHTML = '';
            }

            const welcomeScreen = $('welcomeScreen');
            if (welcomeScreen) {
                welcomeScreen.style.display = 'block';
            }

            AppState.isFirstMessage = true;

            const chatInput = $('chatInput');
            if (chatInput) {
                chatInput.value = '';
                chatInput.focus();
            }

            this.closeSidebar();
            Utils.showToast('Started new conversation', 'success');

            // Update session backup
            StorageManager.backupSession();
        }
    };

    // ===== ENHANCED SAVED MESSAGES MANAGER =====
    const SavedMessagesManager = {
        init() {
            this.loadSavedMessages();
            this.setupClearButton();
            this.setupExportButton();
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
                threadId: AppState.currentThreadId,
                userEmail: AppState.serverUser?.email
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

            if (clearBtn) clearBtn.style.display = 'block';

            savedList.innerHTML = messages.map(msg => `
                <div class="saved-item" onclick="loadSavedMessage('${msg.id}')">
                    <div class="saved-item-content">
                        <div class="saved-item-title">${Utils.escapeHtml(msg.title)}</div>
                        <div class="saved-item-preview">${Utils.escapeHtml(msg.content.substring(0, 100))}...</div>
                        <div class="saved-item-meta">${new Date(msg.timestamp).toLocaleDateString()}</div>
                    </div>
                    <button class="saved-item-delete" onclick="event.stopPropagation(); removeSavedMessage('${msg.id}')" title="Delete">
                        ×
                    </button>
                </div>
            `).join('');
        },

        setupClearButton() {
            const clearBtn = $('clearSavedBtn');
            if (clearBtn) {
                clearBtn.addEventListener('click', () => {
                    this.clearAllSaved();
                });
            }
        },

        // ✅ NEW: Export saved messages
        setupExportButton() {
            const exportBtn = $('exportSavedBtn');
            if (exportBtn) {
                exportBtn.addEventListener('click', () => {
                    this.exportSavedMessages();
                });
            }
        },

        exportSavedMessages() {
            const messages = Array.from(AppState.savedMessages.values());
            if (messages.length === 0) {
                Utils.showToast('No messages to export', 'info');
                return;
            }

            const exportData = {
                exportDate: new Date().toISOString(),
                userEmail: AppState.serverUser?.email,
                messagesCount: messages.length,
                messages: messages.map(msg => ({
                    title: msg.title,
                    content: msg.content,
                    timestamp: new Date(msg.timestamp).toISOString()
                }))
            };

            const dataStr = JSON.stringify(exportData, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(dataBlob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `dsa-saved-messages-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            Utils.showToast('Messages exported successfully', 'success');
        }
    };

    // ===== CONNECTION MONITOR =====
    const ConnectionMonitor = {
        init() {
            this.setupNetworkListeners();
            this.startConnectionCheck();
        },

        setupNetworkListeners() {
            window.addEventListener('online', () => {
                AppState.connectionStatus = 'online';
                this.handleConnectionRestore();
            });

            window.addEventListener('offline', () => {
                AppState.connectionStatus = 'offline';
                this.handleConnectionLoss();
            });
        },

        handleConnectionRestore() {
            console.log('🌐 Connection restored');
            Utils.showToast('Connection restored', 'success', 2000);
            
            // Restart auth checks if user is authenticated
            if (AppState.serverUser?.is_authenticated) {
                AuthManager.startPeriodicAuthCheck();
                AuthManager.performAuthCheck(true);
            }
        },

        handleConnectionLoss() {
            console.log('📡 Connection lost');
            Utils.showToast('Connection lost. Some features may be limited.', 'warning', 5000);
            AuthManager.stopPeriodicAuthCheck();
        },

        startConnectionCheck() {
            // Periodic connection validation
            setInterval(() => {
                const wasOnline = AppState.connectionStatus === 'online';
                const isOnline = navigator.onLine;
                
                if (wasOnline !== isOnline) {
                    AppState.connectionStatus = isOnline ? 'online' : 'offline';
                    if (isOnline) {
                        this.handleConnectionRestore();
                    } else {
                        this.handleConnectionLoss();
                    }
                }
            }, 30000); // Check every 30 seconds
        }
    };

    // ===== INITIALIZATION =====
    function initializeApp() {
        try {
            console.log('🚀 Initializing DSA Mentor Enhanced Authentication System...');

            // Initialize core managers
            AuthManager.init();
            ThemeManager.init();
            SidebarManager.init();
            SavedMessagesManager.init();
            ConnectionMonitor.init();

            // Mark as initialized
            AppState.isInitialized = true;

            // Make app state globally available with enhanced API
            window.app = {
                state: AppState,
                util: Utils,
                auth: AuthManager,
                theme: ThemeManager,
                sidebar: SidebarManager,
                saved: SavedMessagesManager,
                storage: StorageManager,
                connection: ConnectionMonitor,
                
                // ✅ NEW: Helper methods
                helpers: {
                    getSessionMetrics: () => AuthManager.getSessionMetrics(),
                    attemptSessionRecovery: () => AuthManager.attemptSessionRecovery(),
                    exportSessionData: () => {
                        const data = {
                            user: AppState.serverUser,
                            metrics: AuthManager.getSessionMetrics(),
                            savedMessages: Array.from(AppState.savedMessages.values()),
                            theme: ThemeManager.getCurrentTheme(),
                            timestamp: new Date().toISOString()
                        };
                        console.log('Session Data Export:', data);
                        return data;
                    }
                }
            };

            console.log('✅ DSA Mentor Enhanced Authentication System initialized successfully');
            
            // Show initialization complete message
            setTimeout(() => {
                if (AppState.serverUser?.is_authenticated) {
                    Utils.showToast(`Welcome back, ${AppState.serverUser.name}!`, 'success');
                } else {
                    Utils.showToast('DSA Mentor ready! Sign in to get started.', 'info');
                }
            }, 500);

        } catch (error) {
            Utils.logError('App Initialization', error);
            Utils.showToast('Initialization failed. Please refresh the page.', 'error');
        }
    }

    // ===== ENHANCED INITIALIZATION WITH RETRY =====
    async function initializeWithRetry() {
        const maxRetries = 3;
        let attempt = 1;

        while (attempt <= maxRetries) {
            try {
                initializeApp();
                break;
            } catch (error) {
                console.error(`Initialization attempt ${attempt} failed:`, error);
                
                if (attempt === maxRetries) {
                    Utils.showToast('Failed to initialize. Please refresh the page.', 'error');
                    throw error;
                }
                
                console.log(`Retrying initialization in ${attempt * 1000}ms...`);
                await new Promise(resolve => setTimeout(resolve, attempt * 1000));
                attempt++;
            }
        }
    }

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeWithRetry);
    } else {
        initializeWithRetry();
    }

    // Global functions for backward compatibility
    window.removeSavedMessage = (messageId) => SavedMessagesManager.removeSavedMessage(messageId);
    
    window.loadSavedMessage = (messageId) => {
        const message = AppState.savedMessages.get(messageId);
        if (message) {
            Utils.showToast('Loading saved message...', 'info');
            // Add the saved message to current chat
            if (window.addMessageToChat) {
                window.addMessageToChat('assistant', message.content);
            }
        }
    };

    // ✅ ENHANCED: Global debug functions
    window.debugAuth = async function() {
        if (window.app && window.app.auth) {
            return await window.app.auth.debugSession();
        } else {
            console.error('Auth system not loaded');
            return null;
        }
    };

    window.debugApp = function() {
        if (window.app) {
            return window.app.helpers.exportSessionData();
        } else {
            console.error('App not loaded');
            return null;
        }
    };

    // ✅ NEW: Global session recovery function
    window.recoverSession = async function() {
        if (window.app && window.app.auth) {
            return await window.app.auth.attemptSessionRecovery();
        } else {
            console.error('Auth system not loaded');
            return false;
        }
    };

    // ✅ NEW: Manual auth check function
    window.checkAuth = async function() {
        if (window.app && window.app.auth) {
            return await window.app.auth.performAuthCheck(true);
        } else {
            console.error('Auth system not loaded');
        }
    };

    // ✅ NEW: Error boundary for unhandled errors
    window.addEventListener('error', (event) => {
        Utils.logError('Global Error', event.error, {
            filename: event.filename,
            lineno: event.lineno,
            colno: event.colno
        });
    });

    window.addEventListener('unhandledrejection', (event) => {
        Utils.logError('Unhandled Promise Rejection', event.reason);
    });

    console.log('🎯 DSA Mentor Enhanced Authentication System loaded');

})();
