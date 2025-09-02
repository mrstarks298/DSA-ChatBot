// ===== DSA MENTOR - INITIALIZATION SCRIPT =====
// This script should be added at the end of the HTML body or as a separate file

document.addEventListener('DOMContentLoaded', function() {
  console.log('🚀 DSA Mentor starting up...');
  
  // ===== GLOBAL CONFIGURATION =====
  window.APP_CONFIG = {
    apiBaseUrl: window.location.origin,
    maxQueryLength: 2000,
    streamingEnabled: true,
    version: '2.0.0',
    authCheckInterval: 300000, // 5 minutes
    scrollThreshold: 100,
    typingSpeed: 15
  };

  // ===== SUGGESTION HANDLER =====
  window.sendSuggestion = function(text) {
    const chatInput = document.getElementById('chatInput');
    if (chatInput && !chatInput.disabled) {
      chatInput.value = text;
      chatInput.focus();
      
      // Auto-resize the textarea
      chatInput.style.height = 'auto';
      chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
      
      // Trigger send if user is authenticated
      if (window.app && window.app.auth && window.app.auth.isAuthenticated()) {
        setTimeout(() => {
          if (window.sendMessage) {
            window.sendMessage();
          }
        }, 100);
      }
    }
  };

  // ===== MODAL FUNCTIONS =====
  window.closeShareModal = function() {
    const modal = document.getElementById('shareModal');
    if (modal) {
      modal.classList.remove('active');
    }
  };

  window.copyShareLink = function() {
    const shareLink = document.getElementById('shareLink');
    if (shareLink) {
      shareLink.select();
      shareLink.setSelectionRange(0, 99999); // For mobile devices
      
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(shareLink.value).then(() => {
          showToast('Link copied to clipboard!');
          closeShareModal();
        }).catch(err => {
          console.error('Copy failed:', err);
          fallbackCopy(shareLink.value);
        });
      } else {
        fallbackCopy(shareLink.value);
      }
    }
  };

  function fallbackCopy(text) {
    try {
      document.execCommand('copy');
      showToast('Link copied to clipboard!');
      closeShareModal();
    } catch (err) {
      console.error('Fallback copy failed:', err);
      showToast('Copy failed. Please copy the link manually.');
    }
  }

  window.closeVideoModal = function() {
    const modal = document.getElementById('videoModal');
    const embed = document.getElementById('videoEmbed');
    
    if (modal) {
      modal.classList.remove('active');
    }
    if (embed) {
      embed.src = '';
    }
  };

  // ===== GLOBAL TOAST FUNCTION =====
  window.showToast = function(message, type = 'info', duration = 3000) {
    const toast = document.getElementById('toast');
    if (!toast) {
      console.warn('Toast element not found');
      return;
    }

    toast.textContent = message;
    toast.className = `toast show ${type}`;
    
    setTimeout(() => {
      toast.classList.remove('show');
    }, duration);
  };

  // ===== AUTO-RESIZE TEXTAREA =====
  function setupTextareaAutoResize() {
    const textarea = document.getElementById('chatInput');
    if (!textarea) return;

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

    // Initial resize
    autoResize();
  }

  // ===== KEYBOARD SHORTCUTS =====
  document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + Enter to send message
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      if (window.sendMessage) {
        window.sendMessage();
      }
    }
    
    // Escape to close modals
    if (e.key === 'Escape') {
      closeVideoModal();
      closeShareModal();
      
      // Close sidebar on mobile
      const sidebar = document.getElementById('sidebar');
      const overlay = document.getElementById('sidebarOverlay');
      if (sidebar && sidebar.classList.contains('open')) {
        sidebar.classList.remove('open');
        overlay?.classList.remove('active');
        document.body.classList.remove('sidebar-open');
      }
    }
  });

  // ===== MOBILE MENU TOGGLE =====
  function setupMobileMenu() {
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');

    if (mobileMenuBtn && sidebar && overlay) {
      mobileMenuBtn.addEventListener('click', function() {
        const isOpen = sidebar.classList.contains('open');
        
        if (isOpen) {
          sidebar.classList.remove('open');
          overlay.classList.remove('active');
          document.body.classList.remove('sidebar-open');
        } else {
          sidebar.classList.add('open');
          overlay.classList.add('active');
          document.body.classList.add('sidebar-open');
        }
      });

      overlay.addEventListener('click', function() {
        sidebar.classList.remove('open');
        overlay.classList.remove('active');
        document.body.classList.remove('sidebar-open');
      });
    }
  }

  // ===== LOADING STATE MANAGEMENT =====
  function hideLoadingScreen() {
    const loadingScreen = document.getElementById('loadingScreen');
    if (loadingScreen) {
      loadingScreen.style.display = 'none';
    }
  }

  // ===== ERROR HANDLING =====
  window.addEventListener('error', function(event) {
    console.error('Global error caught:', event.error);
    showToast('An unexpected error occurred', 'error');
  });

  window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    showToast('An unexpected error occurred', 'error');
  });

  // ===== INITIALIZATION SEQUENCE =====
  function initialize() {
    try {
      // Setup basic functionality
      setupTextareaAutoResize();
      setupMobileMenu();
      
      // Hide loading screen
      hideLoadingScreen();
      
      // Wait for app modules to be ready
      const checkAppReady = () => {
        if (window.app && window.app.state && window.app.state.isInitialized) {
          console.log('✅ DSA Mentor fully initialized');
          
          // Show success message
          setTimeout(() => {
            showToast('DSA Mentor ready!', 'success');
          }, 1000);
          
        } else {
          setTimeout(checkAppReady, 100);
        }
      };
      
      checkAppReady();
      
    } catch (error) {
      console.error('❌ Initialization error:', error);
      showToast('Initialization failed', 'error');
    }
  }

  // Start initialization
  initialize();
});

// ===== SERVICE WORKER REGISTRATION (PWA) =====
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function() {
    navigator.serviceWorker.register('/static/sw.js')
      .then(function(registration) {
        console.log('✅ Service Worker registered:', registration);
      })
      .catch(function(registrationError) {
        console.log('❌ Service Worker registration failed:', registrationError);
      });
  });
}

// ===== VIEWPORT HEIGHT FIX FOR MOBILE =====
function setVHProperty() {
  const vh = window.innerHeight * 0.01;
  document.documentElement.style.setProperty('--vh', `${vh}px`);
}

setVHProperty();
window.addEventListener('resize', setVHProperty);
window.addEventListener('orientationchange', setVHProperty);

// ===== PERFORMANCE MONITORING =====
window.addEventListener('load', function() {
  if (window.performance && window.performance.timing) {
    const loadTime = window.performance.timing.loadEventEnd - window.performance.timing.navigationStart;
    console.log(`📊 Page load time: ${loadTime}ms`);
  }
});

console.log('🎯 DSA Mentor initialization script loaded');
