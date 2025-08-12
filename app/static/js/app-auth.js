(() => {
  'use strict';

  // Public API and shared state
  window.app = window.app || {};
  const $ = (id) => document.getElementById(id);

  // DOM cache used here
  const chatContent   = $('chatContent');
  const chatInput     = $('chatInput');
  const sendButton    = $('sendButton');
  const savedList     = $('savedList');
  const emptySaved    = $('emptySaved');
  const clearSavedBtn = $('clearSavedBtn');
  const themeToggle   = $('themeToggle');
  const newThreadBtn  = $('newThreadBtn'); // ADDED: New thread button

  // State
  const state = window.app.state = {
    isFirstMessage: true,
    savedMessages: new Map(),
    currentThreadId: genThreadId(),
    authCheckInterval: null,
    serverUser: window.SERVER_USER || { is_authenticated: false }
  };

  // Utilities
  function escapeHtml(s) {
    return String(s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;')
      .replace(/'/g,'&#039;');
  }
  function genThreadId() {
    return 'thread_' + Date.now() + '_' + Math.random().toString(36).slice(2,11);
  }
  function scrollToBottom() {
    const chatArea = $('chatArea');
    if (chatArea) chatArea.scrollTop = chatArea.scrollHeight;
  }
  function showToast(message) {
    const toast = $('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
  }
  // ADDED: Update share link with current thread ID
  function updateShareLink() {
    const shareLink = $('shareLink');
    if (shareLink) {
      // Use current domain and thread ID
      const currentDomain = window.location.origin;
      shareLink.value = `${currentDomain}/chat/${state.currentThreadId}`;
    }
  }
  window.app.util = { escapeHtml, scrollToBottom, showToast, updateShareLink };

  // ADDED: New Thread functionality
  function startNewThread() {
    // Generate new thread ID
    state.currentThreadId = genThreadId();
    state.isFirstMessage = true;
    
    // Clear chat content
    if (chatContent) {
      chatContent.innerHTML = `
        <div class="welcome-screen" id="welcomeScreen">
          <h1 class="welcome-title">Welcome to DSA Mentor</h1>
          <p class="welcome-subtitle">
            Your AI-powered companion for mastering Data Structures and Algorithms
          </p>

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
    
    // Update share link
    updateShareLink();
    
    // Show toast notification
    showToast('🆕 New thread started!');
    
    // Focus input
    if (chatInput) chatInput.focus();
  }

  // Auth overlay - FIXED: Use .active class only
  function showAuthOverlay() {
    $('authOverlay')?.classList.add('active');
  }
  function hideAuthOverlay() {
    $('authOverlay')?.classList.remove('active');
  }

  // Cross-tab auth sync
  function notifyAuthChange() {
    try {
      localStorage.setItem('auth_change', String(Date.now()));
      localStorage.removeItem('auth_change');
    } catch {}
  }
  window.addEventListener('storage', (e) => {
    if (e.key === 'auth_change') setTimeout(() => location.reload(), 1000);
  });

  function periodicAuthCheck() {
    fetch('/auth-status')
      .then(r => { if (!r.ok) throw new Error('net'); return r.json(); })
      .then(d => {
        const was = state.serverUser?.is_authenticated;
        const now = d.is_authenticated;
        if (was !== now) { notifyAuthChange(); location.reload(); return; }
        if (now && state.serverUser?.id && d.user_id && state.serverUser.id !== d.user_id) {
          notifyAuthChange(); location.reload();
        }
      })
      .catch(() => {});
  }
  function startPeriodicAuthCheck() {
    if (state.authCheckInterval) clearInterval(state.authCheckInterval);
    state.authCheckInterval = setInterval(periodicAuthCheck, 30000);
  }
  function stopPeriodicAuthCheck() {
    if (state.authCheckInterval) {
      clearInterval(state.authCheckInterval);
      state.authCheckInterval = null;
    }
  }
  function updateUserProfile(u) {
    if (!u?.is_authenticated) return;
    const avatar = document.querySelector('.profile-avatar');
    const name   = document.querySelector('.profile-name');
    const status = document.querySelector('.profile-status');
    if (avatar && u.name) avatar.textContent = u.name.charAt(0).toUpperCase();
    if (name && u.name) name.textContent = u.name;
    if (status && u.email) status.textContent = u.email;
  }
  function checkAuthentication() {
    const u = state.serverUser;
    if (u && u.is_authenticated === true && u.name && u.email) {
      hideAuthOverlay();
      updateUserProfile(u);
      if (chatInput) chatInput.disabled = false;
      if (sendButton) sendButton.disabled = false;
      startPeriodicAuthCheck();
      return true;
    }
    showAuthOverlay();
    if (chatInput) chatInput.disabled = true;
    if (sendButton) sendButton.disabled = true;
    stopPeriodicAuthCheck();
    return false;
  }
  window.app.auth = { 
    checkAuthentication, 
    startPeriodicAuthCheck, 
    stopPeriodicAuthCheck, 
    showAuthOverlay, 
    hideAuthOverlay,
    startNewThread // ADDED: Expose new thread function
  };

  // Theme - FIXED: Start in dark theme with localStorage persistence
  const THEME_KEY = 'dsa_theme';
  function applyTheme(next) {
    document.body.setAttribute('data-theme', next);
    localStorage.setItem(THEME_KEY, next);
    const sun = themeToggle?.querySelector('.sun-icon');
    const moon = themeToggle?.querySelector('.moon-icon');
    if (sun && moon) {
      if (next === 'dark') { sun.style.display = 'none'; moon.style.display = 'block'; }
      else { sun.style.display = 'block'; moon.style.display = 'none'; }
    }
  }
  // Init theme
  const preferred = localStorage.getItem(THEME_KEY) || 'dark';
  applyTheme(preferred);
  themeToggle?.addEventListener('click', () => {
    const cur = document.body.getAttribute('data-theme') || 'light';
    applyTheme(cur === 'light' ? 'dark' : 'light');
  });

  // ADDED: New Thread Button Event Listener
  newThreadBtn?.addEventListener('click', startNewThread);

  // Message rendering
  function addMessage(sender, content) {
    if (!chatContent) return;
    const id = `message-${state.currentThreadId}-${Date.now()}`;
    const div = document.createElement('div');
    div.className = `message ${sender}-message`;
    div.id = id;
    if (sender === 'user') {
      div.innerHTML = `<div class="message-content"><p>${escapeHtml(content)}</p></div>`;
    } else {
      div.innerHTML = `
        <div class="message-header">
          <div class="avatar bot-avatar">AI</div>
          <span class="sender-name">DSA Mentor</span>
        </div>
        <div class="message-content"><p>${escapeHtml(content)}</p></div>
        <div class="message-actions">
          <button class="action-btn" onclick="copyMessage('${id}')" title="Copy">📋</button>
          <button class="action-btn" onclick="saveMessage('${id}')" title="Save for later">💾</button>
          <button class="action-btn" onclick="shareMessage('${id}')" title="Share">🔗</button>
        </div>
      `;
    }
    chatContent.appendChild(div);
    scrollToBottom();
  }

 function addBotResponse(data) {
    if (!chatContent) return;
    const id = `message-${state.currentThreadId}-${Date.now()}`;
    const div = document.createElement('div');
    div.className = 'message bot-message';
    div.id = id;

    let html = `
      <div class="message-header">
        <div class="avatar bot-avatar">AI</div>
        <span class="sender-name">DSA Mentor</span>
      </div>
      <div class="message-content">
    `;

    if (data.best_book?.title) {
      html += `<div class="concept-title">${escapeHtml(data.best_book.title)}</div>`;
    }
    if (data.summary) {
      html += `<div class="concept-explanation">${escapeHtml(data.summary)}</div>`;
    } 
    
    // FIXED: Properly display question content
    if (data.best_book?.content) {
      let c = data.best_book.content;
      
      // Enhanced markdown-like rendering for better display
      c = c.replace(/\n/g, '<br>')                    
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  
        .replace(/```python\n([\s\S]*?)\n```/g, '<pre><code class="language-python">$1</code></pre>')  
        .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')  // Generic code blocks
        .replace(/`([^`]+)`/g, '<code>$1</code>')  
        .replace(/^# (.*$)/gm, '<h2>$1</h2>')      
        .replace(/^## (.*$)/gm, '<h3>$1</h3>')     
        .replace(/^### (.*$)/gm, '<h4>$1</h4>')    
        .replace(/^- (.*$)/gm, '<li>$1</li>')      
        .replace(/^\* (.*$)/gm, '<li>$1</li>')     // Handle asterisk bullets too
        .replace(/---/g, '<hr>')                   // Horizontal rules
        .replace(/💡 \*\*Tips:\*\*/g, '<div class="tip-box">💡 <strong>Tips:</strong>')
        .replace(/(\d+)\. /g, '<strong>$1.</strong> '); // Number lists

      // Wrap consecutive <li> elements in <ul>
      c = c.replace(/(<li>.*?<\/li>)(\s*<li>.*?<\/li>)*/g, '<ul>$&</ul>');
      
      // Close tip box if it was opened
      if (c.includes('<div class="tip-box">')) {
        c = c.replace(/(<div class="tip-box">.*?)(<br>|$)/g, '$1</div>$2');
      }
      
      html += `<div class="concept-explanation">${c}</div>`;
    }
    
    if (data.best_book?.content && /complexity|time|space/i.test(data.best_book.content)) {
      html += `
        <div class="complexity-badges">
          <span class="complexity-badge">Time Complexity Analysis</span>
          <span class="complexity-badge">Space Complexity Analysis</span>
        </div>
      `;
    }
    if (Array.isArray(data.top_dsa) && data.top_dsa.length) {
      html += `<div class="practice-problems"><div class="section-header">📝 Related Practice Problems</div>`;
      data.top_dsa.forEach(p => {
        const title = (p.section || 'DSA') + ': ' + (p.question || '');
        const desc = p.description || 'Practice this fundamental concept to strengthen your understanding.';
        html += `
          <div class="problem-card">
            <div class="problem-title"><span class="problem-section">${escapeHtml(title)}</span></div>
            <div class="problem-description">${escapeHtml(desc)}</div>
            <div class="problem-links">
              ${p.article_link ? `<a href="${p.article_link}" target="_blank" class="problem-link">Article</a>` : ''}
              ${p.practice_link ? `<a href="${p.practice_link}" target="_blank" class="problem-link">Practice</a>` : ''}
            </div>
          </div>
        `;
      });
      html += `</div>`;
    }
    if (Array.isArray(data.video_suggestions) && data.video_suggestions.length) {
      html += `<div class="video-suggestions"><div class="section-header">🎥 Recommended Video Tutorials</div>`;
      data.video_suggestions.forEach(v => {
        const title = v.title || 'Video Tutorial';
        const topic = v.topic || 'DSA';
        const desc = v.description || v.subtopic || 'Learn this concept through video tutorial';
        const difficulty = v.difficulty ? `<span class="video-difficulty">${escapeHtml(v.difficulty)}</span>` : '';
        const duration = v.duration ? `<span>⏱️ ${escapeHtml(v.duration)}</span>` : '';
        html += `
          <div class="video-card">
            <div class="video-header">
              <div class="video-thumbnail">▶</div>
              <div class="video-info">
                <div class="video-title">${escapeHtml(title)}</div>
                <div class="video-meta"><span>${escapeHtml(topic)}</span>${difficulty}${duration}</div>
                <div class="video-description">${escapeHtml(desc)}</div>
              </div>
            </div>
            <div class="video-actions">
              ${v.video_url ? `<button class="video-btn" onclick="openVideoModal('${encodeURI(v.video_url)}','${escapeHtml(title)}')">Watch</button>` : ''}
              ${v.video_url ? `<a href="${v.video_url}" target="_blank" class="video-btn video-btn-secondary">Open</a>` : ''}
            </div>
          </div>
        `;
      });
      html += `</div>`;
    }

    html += `
      </div>
      <div class="message-actions">
        <button class="action-btn" onclick="copyMessage('${id}')" title="Copy">📋</button>
        <button class="action-btn" onclick="saveMessage('${id}')" title="Save for later">💾</button>
        <button class="action-btn" onclick="shareMessage('${id}')" title="Share">🔗</button>
      </div>
    `;

    div.innerHTML = html;
    chatContent.appendChild(div);
    scrollToBottom();
  }

  // Video helpers
  function extractYouTubeID(url) {
    if (!url) return null;
    const pats = [
      /(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]+)/,
      /(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]+)/,
      /(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]+)/,
      /(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([a-zA-Z0-9_-]+)/
    ];
    for (const p of pats) {
      const m = url.match(p);
      if (m && m[1]) return m[1];
    }
    return null;
  }
  function openVideoModal(videoUrl, title) {
    const id = extractYouTubeID(videoUrl);
    const videoEmbed = $('videoEmbed');
    const videoModalTitle = $('videoModalTitle');
    const videoModal = $('videoModal');
    if (id) {
      const embedUrl = `https://www.youtube.com/embed/${id}`;
      if (videoEmbed) videoEmbed.src = embedUrl;
      if (videoModalTitle) videoModalTitle.textContent = title || 'Video Tutorial';
      if (videoModal) videoModal.classList.add('active');
    } else {
      window.open(videoUrl, '_blank');
    }
  }
  function closeVideoModal() {
    const videoModal = $('videoModal');
    const videoEmbed = $('videoEmbed');
    if (videoModal) videoModal.classList.remove('active');
    if (videoEmbed) videoEmbed.src = '';
  }

  // Saved list rendering used by second file
  function updateSavedMessagesList() {
    if (!savedList) return;
    const arr = Array.from(state.savedMessages.values());
    if (!arr.length) {
      if (emptySaved) emptySaved.style.display = 'block';
      if (clearSavedBtn) clearSavedBtn.style.display = 'none';
      savedList.innerHTML = '';
      if (emptySaved) savedList.appendChild(emptySaved);
      return;
    }
    if (emptySaved) emptySaved.style.display = 'none';
    if (clearSavedBtn) clearSavedBtn.style.display = 'block';
    savedList.innerHTML = '';
    arr.sort((a,b) => new Date(b.timestamp) - new Date(a.timestamp));
    arr.forEach(item => {
      const li = document.createElement('li');
      li.className = 'saved-item';
      li.innerHTML = `
        <div class="saved-item-content">
          <div class="saved-item-title">${escapeHtml(item.title)}</div>
          <div class="saved-item-preview">${escapeHtml(item.preview)}</div>
        </div>
        <button class="saved-item-delete" title="Remove">✖</button>
      `;
      li.addEventListener('click', (e) => {
        if (e.target.closest('.saved-item-delete')) {
          window.removeSavedMessage(item.id);
        } else {
          showSavedMessageContent(item);
        }
      });
      savedList.appendChild(li);
    });
  }
  function showSavedMessageContent(item) {
    const welcome = $('welcomeScreen') || document.querySelector('.welcome-screen');
    if (welcome && welcome.style.display !== 'none') {
      welcome.style.display = 'none';
      state.isFirstMessage = false;
    }
    addSavedMessageToChat(item);
  }
  function addSavedMessageToChat(item) {
    if (!chatContent) return;
    const id = `restored-${item.id}`;
    const div = document.createElement('div');
    div.className = 'message bot-message';
    div.id = id;
    div.innerHTML = `
      <div class="message-header">
        <div class="avatar bot-avatar" style="background:#9333EA;">📌</div>
        <span class="sender-name">Saved Message</span>
        <span style="font-size:12px;color:var(--text-muted);margin-left:auto;">
          Saved ${new Date(item.timestamp).toLocaleDateString()}
        </span>
      </div>
      <div class="message-content">${item.fullContent || item.preview}</div>
      <div class="message-actions">
        <button class="action-btn" onclick="copyMessage('${id}')" title="Copy">📋</button>
        <button class="action-btn" onclick="shareMessage('${id}')" title="Share">🔗</button>
      </div>
    `;
    chatContent.appendChild(div);
    scrollToBottom();
    showToast('💾 Saved message restored to chat!');
  }

  // FIXED: Saved messages with localStorage persistence
  const SAVED_KEY = 'dsa_saved_messages';
  function loadSavedMessages() {
    try {
      const raw = localStorage.getItem(SAVED_KEY);
      const obj = raw ? JSON.parse(raw) : {};
      state.savedMessages = new Map(Object.entries(obj).map(([k,v]) => [k,v]));
    } catch { state.savedMessages = new Map(); }
    updateSavedMessagesList();
  }
  function saveSavedMessages() {
    try {
      const obj = Object.fromEntries(state.savedMessages);
      localStorage.setItem(SAVED_KEY, JSON.stringify(obj));
    } catch {}
  }

  window.removeSavedMessage = function(messageId) {
    if (state.savedMessages.has(messageId)) {
      state.savedMessages.delete(messageId);
      saveSavedMessages();
      updateSavedMessagesList();
      showToast('Message removed from saved items!');
    }
  };

  // Network: send message
  async function sendMessage() {
    if (!state.serverUser?.is_authenticated) {
      showAuthOverlay();
      showToast('Please login to continue');
      return;
    }
    const q = chatInput?.value.trim();
    if (!q) return;

    if (state.isFirstMessage) {
      const welcome = $('welcomeScreen') || document.querySelector('.welcome-screen');
      if (welcome) welcome.style.display = 'none';
      state.isFirstMessage = false;
    }

    addMessage('user', q);
    const loadingId = addLoadingMessage();
    if (chatInput) chatInput.value = '';
    if (sendButton) sendButton.disabled = true;

    try {
      const r = await fetch('/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: q,
          thread_id: state.currentThreadId // ADDED: Send thread ID to backend
        })
      });
      if (r.status === 401 || r.status === 403) {
        removeLoadingMessage(loadingId);
        showAuthOverlay();
        showToast('Session expired. Please login again.');
        if (sendButton) sendButton.disabled = false;
        return;
      }
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      removeLoadingMessage(loadingId);
      addBotResponse(data);
    } catch (e) {
      removeLoadingMessage(loadingId);
      let msg = 'Sorry, I encountered an error. Please try again.';
      if (String(e.message).includes('Failed to fetch')) {
        msg = 'Network error. Please check your connection and try again.';
      }
      addMessage('bot', msg);
      console.error('Send message error:', e);
    } finally {
      if (sendButton) sendButton.disabled = false;
      if (chatInput) chatInput.focus();
    }
  }

  // Loading indicators
  function addLoadingMessage() {
    if (!chatContent) return null;
    const id = `loading-${Date.now()}`;
    const div = document.createElement('div');
    div.className = 'message bot-message';
    div.id = id;
    div.innerHTML = `
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
    chatContent.appendChild(div);
    scrollToBottom();
    return id;
  }
  function removeLoadingMessage(id) {
    if (!id) return;
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  // ADDED: Global function for suggestion cards
  window.askQuestion = function(question) {
    if (!state.serverUser?.is_authenticated) {
      showAuthOverlay();
      showToast('Please login to ask questions');
      return;
    }
    
    if (chatInput) {
      chatInput.value = question;
      window.sendMessage();
    }
  };

  // ADDED: Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      $('videoModal')?.classList.remove('active');
      $('shareModal')?.classList.remove('active');
    }
  });

  // Expose public APIs needed by second file/HTML
  window.app.render = { addMessage, addBotResponse, addLoadingMessage, removeLoadingMessage, updateSavedMessagesList, showSavedMessageContent, addSavedMessageToChat };
  window.app.saved  = { loadSavedMessages, saveSavedMessages };
  window.app.video  = { extractYouTubeID, openVideoModal, closeVideoModal };
  window.sendMessage = sendMessage;
  window.openVideoModal = openVideoModal;
  window.closeVideoModal = closeVideoModal;

  // Init on load
  checkAuthentication();
  loadSavedMessages();
  
  // ADDED: Initialize share link on load
  updateShareLink();
})();
