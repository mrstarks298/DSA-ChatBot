(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);

  const { state, util, auth, render, saved } = window.app;
  const { showToast, updateShareLink } = util; // ADDED: Import updateShareLink
  const { stopPeriodicAuthCheck } = auth;

  const chatInput     = $('chatInput');
  const sendButton    = $('sendButton');
  const downloadBtn   = $('downloadBtn');
  const shareBtn      = $('shareBtn');
  const clearSavedBtn = $('clearSavedBtn');

  // Actions
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
    // FIXED: Update share link before showing modal
    updateShareLink();
    const modal = $('shareModal');
    if (modal) modal.classList.add('active');
  };

  // Download chat via server-rendered PDF
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
        thread_id: state.currentThreadId // ADDED: Include thread ID in PDF request
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

  // Modals
  window.closeModal = function(id) {
    const m = $(id);
    if (m) m.classList.remove('active');
  };
  window.copyShareLink = function() {
    const input = $('shareLink');
    if (input && navigator.clipboard) {
      input.select?.();
      navigator.clipboard.writeText(input.value)
        .then(() => { showToast('Share link copied to clipboard!'); window.closeModal('shareModal'); })
        .catch(() => showToast('Failed to copy share link'));
    }
  };

  // Global click to close overlays and video modal backdrop
  document.addEventListener('click', (e) => {
    if (e.target.classList?.contains('modal-overlay')) e.target.classList.remove('active');
    if (e.target.classList?.contains('video-modal')) window.closeVideoModal?.();
  });

  // Event bindings
  sendButton?.addEventListener('click', () => window.sendMessage());
  chatInput?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      window.sendMessage();
    }
  });
  
  // FIXED: Share button now updates link before opening modal
  shareBtn?.addEventListener('click', () => {
    updateShareLink();
    $('shareModal')?.classList.add('active');
  });
  
  downloadBtn?.addEventListener('click', downloadChat);
  clearSavedBtn?.addEventListener('click', () => {
    state.savedMessages.clear();
    saved.saveSavedMessages();
    render.updateSavedMessagesList();
    showToast('All saved messages cleared!');
  });

  // Init
  saved.loadSavedMessages?.();
  if (state.serverUser?.is_authenticated) chatInput?.focus();

  // Cleanup
  window.addEventListener('beforeunload', () => {
    stopPeriodicAuthCheck?.();
  });
})();