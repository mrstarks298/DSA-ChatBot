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

  // ===== SHARED CHAT FUNCTIONALITY =====
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
          
          this.displaySharedMessages(data.messages);
          this.showSharedBanner(threadId);
          this.makeReadOnly();
          
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
    
    displaySharedMessages(messages) {
      const chatContent = $('chatContent');
      if (!chatContent) return;
      
      messages.forEach(message => {
        if (message.sender === 'user') {
          render.addMessage('user', message.content);
        } else if (message.sender === 'assistant') {
          render.addBotResponse(message.content);
        }
      });
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
        <span>📤 You're viewing a shared conversation • Read-only mode</span>
      `;
      chatContent.prepend(banner);
    },
    
    makeReadOnly() {
      if (chatInput) {
        chatInput.disabled = true;
        chatInput.placeholder = 'This is a shared chat (read-only)';
        chatInput.style.background = '#f5f5f5';
      }
      if (sendButton) {
        sendButton.disabled = true;
        sendButton.style.opacity = '0.5';
      }
      const newThreadBtn = $('newThreadBtn');
      if (newThreadBtn) {
        newThreadBtn.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 4V20M4 12H20" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
          </svg>
          Start Your Own Chat
        `;
      }
    }
  };

  // ===== EXISTING MESSAGE ACTIONS =====
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

  // ===== SHARE FUNCTIONALITY =====
  async function shareCurrentChat() {
    // If in shared view, just show current URL
    if (SharedChat.isSharedView) {
      const shareLink = $('shareLink');
      if (shareLink) shareLink.value = window.location.href;
      $('shareModal')?.classList.add('active');
      return;
    }

    // Normal share functionality
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

  // ===== DOWNLOAD FUNCTIONALITY =====
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

  // ===== MODAL FUNCTIONS =====
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

  // Initialize shared chat functionality
  SharedChat.init();

  // ===== CLEANUP =====
  window.addEventListener('beforeunload', () => {
    stopPeriodicAuthCheck?.();
  });
})();
