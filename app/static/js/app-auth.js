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
                .replace(/'/g, '&#x27;');
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

        // NEW: Retry function with exponential backoff
        async retryFunction(fn, maxRetries = 3, baseDelay = 1000) {
            for (let attempt = 0; attempt < maxRetries; attempt++) {
                try {
                    return await fn();
                } catch (error) {
                    if (attempt === maxRetries - 1) throw error;
                    const delay = baseDelay * Math.pow(2, attempt);
                    console.log(`Retry attempt ${attempt + 1}/${maxRetries} in ${delay}ms`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
            }
        }
    };

    // ===== ENHANCED APPLICATION STATE =====
    const AppState = {
        isFirstMessage: true,
        savedMessages: new Map(),
        currentThreadId: Utils.generateThreadId(),
        authCheckInterval: null,
        serverUser: window.SERVER_USER || { is_authenticated: false },
        isInitialized: false,
        authCheckInProgress: false,
        config: window.APP_CONFIG || {},
        
        // NEW: Enhanced state tracking
        sessionMetrics: {
            authChecks: 0,
            authFailures: 0,
            lastAuthCheck: null,
            connectionStatus: 'online',
            recoveryAttempts: 0
        },
        
        // NEW: Connection monitoring
        isOnline: navigator.onLine,
        lastOnlineCheck: Date.now(),
        
        // NEW: Tab visibility tracking
        isTabVisible: !document.hidden,
        lastVisibilityChange: Date.now(),
        
        // NEW: Session backup
        sessionBackup: null
    };

    // ===== ENHANCED STORAGE MANAGER =====
    const StorageManager = {
        keys: {
            USER_DATA: 'dsa_user_data',
            THEME: 'dsa_theme',
            SAVED_MESSAGES: 'dsa_saved_messages',
            AUTH_TIMESTAMP: 'dsa_auth_check',
            SESSION_BACKUP: 'dsa_session_backup', // NEW
            APP_STATE: 'dsa_app_state' // NEW
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

        // NEW: Backup and restore app state
        backupState() {
            try {
                const backup = {
                    timestamp: Date.now(),
                    userData: this.get(this.keys.USER_DATA),
                    threadId: AppState.currentThreadId,
                    metrics: AppState.sessionMetrics
                };
                this.set(this.keys.SESSION_BACKUP, backup);
                return true;
            } catch (error) {
                console.warn('State backup error:', error);
                return false;
            }
        },

        restoreState() {
            try {
                const backup = this.get(this.keys.SESSION_BACKUP);
                if (!backup) return false;

                // Only restore if backup is recent (less than 1 hour)
                if (Date.now() - backup.timestamp < 3600000) {
                    if (backup.userData) {
                        AppState.serverUser = backup.userData;
                    }
                    if (backup.threadId) {
                        AppState.currentThreadId = backup.threadId;
                    }
                    if (backup.metrics) {
                        AppState.sessionMetrics = { ...AppState.sessionMetrics, ...backup.metrics };
                    }
                    console.log('✅ App state restored from backup');
                    return true;
                }
                return false;
            } catch (error) {
                console.warn('State restore error:', error);
                return false;
            }
        }
    };

    // ===== ENHANCED CONNECTION MANAGER =====
    const ConnectionManager = {
        init() {
            this.setupConnectionListeners();
            this.checkConnection();
        },

        setupConnectionListeners() {
            window.addEventListener('online', () => {
                console.log('🌐 Connection restored');
                AppState.isOnline = true;
                AppState.lastOnlineCheck = Date.now();
                Utils.showToast('Connection restored', 'success');
                
                // Perform auth check when connection is restored
                if (AppState.serverUser?.is_authenticated) {
                    setTimeout(() => AuthManager.performAuthCheck(true), 1000);
                }
            });

            window.addEventListener('offline', () => {
                console.log('🌐 Connection lost');
                AppState.isOnline = false;
                Utils.showToast('Connection lost', 'warning');
            });

            // Check connection periodically
            setInterval(() => {
                this.checkConnection();
            }, 30000); // Every 30 seconds
        },

        checkConnection() {
            AppState.isOnline = navigator.onLine;
            AppState.lastOnlineCheck = Date.now();
        },

        isConnected() {
            return AppState.isOnline && navigator.onLine;
        }
    };

    // ===== ENHANCED AUTHENTICATION MANAGER =====
    const AuthManager = {
        init() {
            console.log('🔐 Initializing authentication system...');
            
            // Try to restore state from backup
            StorageManager.restoreState();
            
            this.loadStoredUser();
            this.setupEventListeners();
            this.setupVisibilityHandling();
            
            // Initial auth check
            setTimeout(() => {
                this.checkAuthentication();
            }, 100);
        },

        loadStoredUser() {
            const storedUser = StorageManager.get(StorageManager.keys.USER_DATA);
            console.log('📱 Loading stored user:', storedUser);
            
            if (storedUser && storedUser.is_authenticated && storedUser.name && storedUser.email) {
                if (!AppState.serverUser.is_authenticated) {
                    AppState.serverUser = {
                        is_authenticated: true,
                        id: storedUser.id || storedUser.user_id,
                        name: storedUser.name,
                        email: storedUser.email,
                        picture: storedUser.picture
                    };
                    console.log('✅ Restored user from storage:', AppState.serverUser.email);
                }
            }
        },

        setupEventListeners() {
            // Cross-tab communication
            window.addEventListener('storage', (e) => {
                if (e.key === StorageManager.keys.USER_DATA) {
                    console.log('🔄 Auth change detected across tabs');
                    this.handleAuthChange();
                }
            });

            // Page unload backup
            window.addEventListener('beforeunload', () => {
                StorageManager.backupState();
            });

            // Error boundary
            window.addEventListener('error', (event) => {
                console.error('🚨 Global error caught:', event.error);
                AppState.sessionMetrics.authFailures++;
            });

            window.addEventListener('unhandledrejection', (event) => {
                console.error('🚨 Unhandled rejection:', event.reason);
                AppState.sessionMetrics.authFailures++;
            });
        },

        setupVisibilityHandling() {
            document.addEventListener('visibilitychange', () => {
                AppState.isTabVisible = !document.hidden;
                AppState.lastVisibilityChange = Date.now();
                
                if (!document.hidden && AppState.serverUser?.is_authenticated) {
                    console.log('👁️ Tab became visible, checking auth status');
                    this.performAuthCheck(true);
                }
            });
        },

        checkAuthentication() {
            console.log('🔍 Checking authentication state...');
            const user = AppState.serverUser;
            
            if (user?.is_authenticated && user.name && user.email) {
                console.log('✅ User is authenticated:', user.email);
                this.authenticatedState();
                return true;
            }

            // Check for shared view
            const isSharedView = document.body.getAttribute('data-shared-view') === 'true';
            const sharedThreadId = document.body.getAttribute('data-shared-thread-id');

            if (isSharedView && sharedThreadId && sharedThreadId !== 'null') {
                console.log('👥 Shared view mode detected');
                this.sharedViewState();
            } else {
                console.log('🔒 User not authenticated');
                this.unauthenticatedState();
            }
            return false;
        },

        authenticatedState() {
            console.log('🎯 Setting authenticated state...');
            this.hideAuthOverlay();
            this.hideSharedThreadBanner();
            this.updateUserProfile(AppState.serverUser);
            this.enableChatInterface();
            this.startPeriodicAuthCheck();
            StorageManager.set(StorageManager.keys.USER_DATA, AppState.serverUser);
            console.log('✅ User authenticated state set for:', AppState.serverUser.email);
        },

        unauthenticatedState() {
            console.log('🔒 Setting unauthenticated state...');
            this.showAuthOverlay();
            this.hideSharedThreadBanner();
            this.disableChatInterface();
            this.stopPeriodicAuthCheck();
            StorageManager.remove(StorageManager.keys.USER_DATA);
            console.log('🔒 Unauthenticated state set');
        },

        sharedViewState() {
            console.log('👥 Setting shared view state...');
            this.hideAuthOverlay();
            this.showSharedThreadBanner();
            this.disableChatInterface();
            this.stopPeriodicAuthCheck();
            console.log('👥 Shared view state set');
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
            console.log('👤 Updating user profile for:', user?.email);
            
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
                status.textContent = user.email || 'Authenticated';
            }
        },

        enableChatInterface() {
            console.log('💬 Enabling chat interface...');
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
            console.log('❌ Disabling chat interface...');
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

        startPeriodicAuthCheck() {
            if (AppState.authCheckInterval) {
                clearInterval(AppState.authCheckInterval);
            }

            // Adaptive auth check intervals based on connection and visibility
            const getCheckInterval = () => {
                if (!ConnectionManager.isConnected()) return 300000; // 5 minutes if offline
                if (!AppState.isTabVisible) return 300000; // 5 minutes if tab hidden
                return 120000; // 2 minutes if online and visible
            };

            AppState.authCheckInterval = setInterval(() => {
                this.performAuthCheck();
            }, getCheckInterval());

            console.log('⏰ Started periodic auth checks');
        },

        stopPeriodicAuthCheck() {
            if (AppState.authCheckInterval) {
                clearInterval(AppState.authCheckInterval);
                AppState.authCheckInterval = null;
                console.log('⏰ Stopped periodic auth checks');
            }
        },

        // ✅ ENHANCED: Better auth check with comprehensive error handling
        async performAuthCheck(force = false) {
            if (AppState.authCheckInProgress && !force) {
                console.log('🔄 Auth check already in progress, skipping...');
                return;
            }

            // Skip if offline
            if (!ConnectionManager.isConnected()) {
                console.log('🌐 Offline, skipping auth check');
                return;
            }

            AppState.authCheckInProgress = true;
            AppState.sessionMetrics.authChecks++;
            AppState.sessionMetrics.lastAuthCheck = Date.now();

            try {
                console.log('🔍 Performing auth check...');

                const response = await Utils.retryFunction(async () => {
                    const controller = new AbortController();
                    const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout

                    try {
                        const response = await fetch('/auth/auth-status', {
                            method: 'GET',
                            credentials: 'same-origin', // Essential for session cookies
                            cache: 'no-cache',
                            signal: controller.signal,
                            headers: {
                                'Accept': 'application/json',
                                'Content-Type': 'application/json',
                                'X-Requested-With': 'XMLHttpRequest'
                            }
                        });
                        
                        clearTimeout(timeoutId);
                        return response;
                    } catch (error) {
                        clearTimeout(timeoutId);
                        throw error;
                    }
                }, 3, 2000);

                if (!response.ok) {
                    console.warn('❌ Auth check failed:', response.status);
                    AppState.sessionMetrics.authFailures++;
                    
                    if (response.status === 401) {
                        // Session expired or invalid
                        if (AppState.serverUser?.is_authenticated) {
                            console.log('⚠️ Session expired, logging out...');
                            AppState.serverUser = { is_authenticated: false };
                            this.checkAuthentication();
                            Utils.showToast('Session expired. Please log in again.', 'warning');
                        }
                    } else if (response.status === 503) {
                        Utils.showToast('Service temporarily unavailable', 'warning');
                    }
                    return;
                }

                const data = await response.json();
                console.log('📊 Auth check response:', {
                    authenticated: data.is_authenticated,
                    email: data.email,
                    timestamp: new Date().toISOString()
                });

                const wasAuthenticated = AppState.serverUser?.is_authenticated;
                const nowAuthenticated = data.is_authenticated;

                // Handle authentication state changes
                if (wasAuthenticated !== nowAuthenticated) {
                    console.log('🔄 Authentication status changed:', {
                        was: wasAuthenticated,
                        now: nowAuthenticated
                    });

                    if (!nowAuthenticated) {
                        console.log('👋 User logged out, updating state...');
                        AppState.serverUser = { is_authenticated: false };
                        this.checkAuthentication();
                        Utils.showToast('You have been logged out', 'warning');
                    } else {
                        console.log('👋 User logged in, updating state...');
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
                    console.log('🔄 Different user logged in, updating state...');
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

                // Update stored user data if authenticated
                if (nowAuthenticated && data.email) {
                    StorageManager.set(StorageManager.keys.USER_DATA, {
                        is_authenticated: true,
                        id: data.user_id,
                        name: data.name,
                        email: data.email,
                        picture: data.picture
                    });
                }

                // Reset failure count on success
                AppState.sessionMetrics.authFailures = 0;

            } catch (error) {
                AppState.sessionMetrics.authFailures++;
                
                if (error.name === 'AbortError') {
                    console.warn('⏰ Auth check timed out');
                } else {
                    console.error('❌ Auth check failed:', error);
                    
                    // Show error only if multiple consecutive failures
                    if (AppState.sessionMetrics.authFailures >= 3) {
                        Utils.showToast('Authentication check failed', 'error');
                    }
                }
            } finally {
                AppState.authCheckInProgress = false;
            }
        },

        async logout() {
            console.log('🚪 Initiating logout...');
            
            try {
                const response = await fetch('/auth/logout', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json'
                    }
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
                console.error('❌ Logout error:', error);
                Utils.showToast('Logout failed', 'error');
            }
        },

        handleAuthChange() {
            console.log('🔄 Auth change detected across tabs');
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
                    const data = await response.json();
                    console.log('🔍 Session Debug:', data);
                    console.log('📊 App State:', {
                        serverUser: AppState.serverUser,
                        metrics: AppState.sessionMetrics,
                        isOnline: AppState.isOnline,
                        isTabVisible: AppState.isTabVisible
                    });
                    return data;
                } else {
                    console.error('❌ Session debug failed:', response.status);
                }
            } catch (error) {
                console.error('❌ Session debug error:', error);
            }
        },

        // NEW: Manual session recovery
        async recoverSession() {
            console.log('🔧 Attempting session recovery...');
            AppState.sessionMetrics.recoveryAttempts++;
            
            try {
                // Try to restore from backup
                if (StorageManager.restoreState()) {
                    Utils.showToast('Session restored from backup', 'success');
                }

                // Force auth check
                await this.performAuthCheck(true);
                
                // If still not authenticated, clear everything and restart
                if (!this.isAuthenticated()) {
                    console.log('🔄 Full reset required');
                    StorageManager.clear();
                    AppState.serverUser = { is_authenticated: false };
                    this.checkAuthentication();
                    Utils.showToast('Session reset complete', 'info');
                }
            } catch (error) {
                console.error('❌ Session recovery failed:', error);
                Utils.showToast('Session recovery failed', 'error');
            }
        }
    };

    // ===== ENHANCED THEME MANAGER =====
    const ThemeManager = {
        init() {
            console.log('🎨 Initializing theme system...');
            
            // Check system theme preference
            const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
            const savedTheme = StorageManager.get(StorageManager.keys.THEME, systemTheme);
            
            this.applyTheme(savedTheme);
            this.setupThemeToggle();
            this.setupSystemThemeListener();
        },

        setupSystemThemeListener() {
            // Listen for system theme changes
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                const currentTheme = this.getCurrentTheme();
                if (!StorageManager.get(StorageManager.keys.THEME)) {
                    // Only auto-change if user hasn't manually set a theme
                    this.applyTheme(e.matches ? 'dark' : 'light');
                }
            });
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
            const currentTheme = this.getCurrentTheme();
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            this.applyTheme(newTheme);
        },

        applyTheme(theme) {
            console.log('🎨 Applying theme:', theme);
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

            const themeColorMeta = document.querySelector('meta[name="theme-color"]');
            if (themeColorMeta) {
                themeColorMeta.content = theme === 'dark' ? '#111827' : '#1B7EFE';
            }
        },

        getCurrentTheme() {
            return document.body.getAttribute('data-theme') || 'light';
        }
    };

    // ===== ENHANCED SIDEBAR MANAGER WITH TOUCH SUPPORT =====
    const SidebarManager = {
        touchStartX: 0,
        touchStartY: 0,
        
        init() {
            console.log('📱 Initializing sidebar system...');
            this.setupMobileMenuToggle();
            this.setupSidebarInteractions();
            this.setupNewThreadButton();
            this.setupTouchGestures();
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

        // NEW: Touch gesture support for mobile
        setupTouchGestures() {
            if (!('ontouchstart' in window)) return;

            document.addEventListener('touchstart', (e) => {
                this.touchStartX = e.touches[0].clientX;
                this.touchStartY = e.touches[0].clientY;
            }, { passive: true });

            document.addEventListener('touchmove', (e) => {
                const touchX = e.touches[0].clientX;
                const touchY = e.touches[0].clientY;
                const diffX = touchX - this.touchStartX;
                const diffY = touchY - this.touchStartY;

                // Swipe right from left edge to open sidebar
                if (this.touchStartX < 20 && diffX > 50 && Math.abs(diffY) < 100) {
                    this.openSidebar();
                }
                
                // Swipe left to close sidebar
                if (diffX < -50 && Math.abs(diffY) < 100) {
                    const sidebar = $('sidebar');
                    if (sidebar && sidebar.classList.contains('open')) {
                        this.closeSidebar();
                    }
                }
            }, { passive: true });
        },

        toggleSidebar() {
            const sidebar = $('sidebar');
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
            console.log('🆕 Starting new thread...');
            AppState.currentThreadId = Utils.generateThreadId();
            
            const chatContent = $('chatContent');
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
        }
    };

    // ===== ENHANCED SAVED MESSAGES MANAGER =====
    const SavedMessagesManager = {
        init() {
            console.log('💾 Initializing saved messages system...');
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
                        <div class="empty-saved-icon">💾</div>
                        <p>No saved messages yet</p>
                        <p>Save important conversations for later</p>
                    </div>
                `;
                if (clearBtn) clearBtn.style.display = 'none';
                return;
            }

            savedList.innerHTML = messages.map(msg => `
                <div class="saved-item" onclick="loadSavedMessage('${msg.id}')">
                    <div class="saved-item-content">
                        <div class="saved-item-title">${Utils.escapeHtml(msg.title)}</div>
                        <div class="saved-item-preview">${Utils.escapeHtml(msg.content.substring(0, 80))}...</div>
                    </div>
                    <button class="saved-item-delete" onclick="event.stopPropagation(); removeSavedMessage('${msg.id}')" 
                            title="Delete saved message">×</button>
                </div>
            `).join('');

            if (clearBtn) clearBtn.style.display = 'block';
        },

        setupClearButton() {
            const clearBtn = $('clearSavedBtn');
            if (clearBtn) {
                clearBtn.addEventListener('click', () => {
                    this.clearAllSaved();
                });
            }
        },

        // NEW: Export saved messages
        exportSavedMessages() {
            const messages = Array.from(AppState.savedMessages.values());
            const data = {
                export_date: new Date().toISOString(),
                total_messages: messages.length,
                messages: messages
            };

            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `dsa_saved_messages_${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            Utils.showToast('Saved messages exported', 'success');
        }
    };

    // ===== GLOBAL APP OBJECT =====
    window.app = {
        state: AppState,
        auth: AuthManager,
        theme: ThemeManager,
        sidebar: SidebarManager,
        savedMessages: SavedMessagesManager,
        storage: StorageManager,
        connection: ConnectionManager,
        util: Utils
    };

    // ===== GLOBAL DEBUG FUNCTIONS =====
    window.debugAuth = function() {
        console.group('🔍 Authentication Debug');
        console.log('App State:', AppState);
        console.log('Server User:', AppState.serverUser);
        console.log('Session Metrics:', AppState.sessionMetrics);
        console.log('Is Authenticated:', AuthManager.isAuthenticated());
        console.log('Connection Status:', ConnectionManager.isConnected());
        console.groupEnd();
        
        return AuthManager.debugSession();
    };

    window.debugApp = function() {
        return {
            appState: AppState,
            localStorage: {
                userData: StorageManager.get(StorageManager.keys.USER_DATA),
                theme: StorageManager.get(StorageManager.keys.THEME),
                savedMessages: StorageManager.get(StorageManager.keys.SAVED_MESSAGES),
                sessionBackup: StorageManager.get(StorageManager.keys.SESSION_BACKUP)
            },
            browserInfo: {
                userAgent: navigator.userAgent,
                cookieEnabled: navigator.cookieEnabled,
                onLine: navigator.onLine,
                language: navigator.language
            }
        };
    };

    window.recoverSession = function() {
        return AuthManager.recoverSession();
    };

    window.checkAuth = function() {
        return AuthManager.performAuthCheck(true);
    };

    // ===== INITIALIZATION SEQUENCE =====
    function initializeApp() {
        try {
            console.log('🚀 Starting DSA Mentor initialization...');

            // Initialize connection monitoring first
            ConnectionManager.init();
            
            // Initialize theme system
            ThemeManager.init();
            
            // Initialize authentication system
            AuthManager.init();
            
            // Initialize sidebar system
            SidebarManager.init();
            
            // Initialize saved messages
            SavedMessagesManager.init();

            // Mark app as initialized
            AppState.isInitialized = true;

            console.log('✅ DSA Mentor authentication system fully initialized');
            Utils.showToast('App ready!', 'success', 2000);

        } catch (error) {
            console.error('❌ Initialization failed:', error);
            Utils.showToast('Initialization failed. Please refresh.', 'error', 5000);
        }
    }

    // ===== GLOBAL FUNCTIONS FOR SAVED MESSAGES =====
    window.loadSavedMessage = function(messageId) {
        const message = AppState.savedMessages.get(messageId);
        if (message) {
            const chatInput = $('chatInput');
            if (chatInput) {
                chatInput.value = message.content;
                chatInput.focus();
                Utils.showToast('Message loaded', 'info');
            }
        }
    };

    window.removeSavedMessage = function(messageId) {
        SavedMessagesManager.removeSavedMessage(messageId);
    };

    window.exportSavedMessages = function() {
        SavedMessagesManager.exportSavedMessages();
    };

    // ===== START INITIALIZATION =====
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeApp);
    } else {
        // DOM is already ready
        setTimeout(initializeApp, 100);
    }

    console.log('🎯 DSA Mentor authentication system loaded');
})();
