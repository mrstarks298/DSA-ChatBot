// ===== DSA MENTOR - INITIALIZATION SCRIPT =====
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

            // Auto-send if user is authenticated
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
            shareLink.setSelectionRange(0, 99999);

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
    };

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

    // ===== DOWNLOAD AND SHARE FUNCTIONALITY =====
    function setupDownloadChat() {
        const downloadBtn = document.getElementById('downloadBtn');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', async function() {
                try {
                    if (!window.app || !window.app.auth || !window.app.auth.isAuthenticated()) {
                        showToast('Please sign in to download chat', 'warning');
                        return;
                    }

                    // Show loading state
                    const originalText = downloadBtn.textContent;
                    downloadBtn.textContent = 'Generating...';
                    downloadBtn.disabled = true;

                    // Get chat content
                    const chatContent = document.getElementById('chatContent');
                    if (!chatContent || !chatContent.innerHTML.trim()) {
                        showToast('No chat content to download', 'info');
                        return;
                    }

                    // Send to backend for PDF generation
                    const response = await fetch('/download-chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        credentials: 'same-origin',
                        body: JSON.stringify({
                            html_content: chatContent.innerHTML
                        })
                    });

                    if (!response.ok) {
                        throw new Error(`Download failed: ${response.statusText}`);
                    }

                    // Download the PDF
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `dsa_chat_${new Date().toISOString().split('T')[0]}.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);

                    showToast('Chat downloaded successfully!', 'success');

                } catch (error) {
                    console.error('Download error:', error);
                    showToast('Download failed. Please try again.', 'error');
                } finally {
                    // Restore button state
                    downloadBtn.textContent = originalText;
                    downloadBtn.disabled = false;
                }
            });
        }
    }

    function setupShareChat() {
        const shareBtn = document.getElementById('shareBtn');
        const shareModal = document.getElementById('shareModal');
        
        if (shareBtn && shareModal) {
            shareBtn.addEventListener('click', function() {
                if (!window.app || !window.app.auth || !window.app.auth.isAuthenticated()) {
                    showToast('Please sign in to share chat', 'warning');
                    return;
                }

                // Generate or update share link
                if (window.app && window.app.state) {
                    const threadId = window.app.state.currentThreadId;
                    if (window.app.util && window.app.util.updateShareLink) {
                        window.app.util.updateShareLink(threadId);
                    }
                }

                shareModal.classList.add('active');
            });
        }
    }

    // ===== FEEDBACK FUNCTIONALITY =====
    function setupFeedback() {
        const feedbackBtn = document.getElementById('feedbackBtn');
        if (feedbackBtn) {
            feedbackBtn.addEventListener('click', function() {
                // Simple feedback collection
                const rating = prompt('Rate your experience (1-5 stars):');
                const feedback = prompt('Any additional feedback? (optional):');
                
                if (rating && rating >= 1 && rating <= 5) {
                    // Send feedback to backend
                    fetch('/api/feedback', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        credentials: 'same-origin',
                        body: JSON.stringify({
                            rating: parseInt(rating),
                            feedback: feedback || ''
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.message) {
                            showToast(data.message, 'success');
                        }
                    })
                    .catch(error => {
                        console.error('Feedback error:', error);
                        showToast('Thank you for your feedback!', 'success');
                    });
                }
            });
        }
    }

    // ===== INITIALIZATION SEQUENCE =====
    function initialize() {
        try {
            // Setup additional functionality
            setupDownloadChat();
            setupShareChat();
            setupFeedback();

            // Hide loading screen
            hideLoadingScreen();

            // Wait for app modules to be ready
            const checkAppReady = () => {
                if (window.app && window.app.state && window.app.state.isInitialized) {
                    console.log('✅ DSA Mentor fully initialized');
                    
                    // Show success message after a delay
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