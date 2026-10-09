const AUTH_KEY = 'campus_nexus_token';
const state = {
    user: null,
    activeTab: 'chat-view',
    retryQuery: '',
};

document.addEventListener('DOMContentLoaded', () => {
    bindEvents();
    syncLanguageSelector('English');
    checkAuth();
    checkHealth();
});

function bindEvents() {
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    document.getElementById('togglePasswordBtn').addEventListener('click', () => {
        const passwordInput = document.getElementById('loginPassword');
        const isHidden = passwordInput.type === 'password';
        passwordInput.type = isHidden ? 'text' : 'password';
        document.getElementById('togglePasswordBtn').textContent = isHidden ? 'Hide' : 'Show';
        document.getElementById('togglePasswordBtn').setAttribute('aria-label', isHidden ? 'Hide password' : 'Show password');
    });
    document.getElementById('logoutBtn').addEventListener('click', logout);
    document.getElementById('sendBtn').addEventListener('click', submitQuery);
    document.getElementById('queryInput').addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            submitQuery();
        }
    });

    document.getElementById('languageSelect').addEventListener('change', (event) => {
        syncLanguageSelector(event.target.value);
    });

    document.querySelectorAll('.nav-btn').forEach((btn) => {
        btn.addEventListener('click', () => setActiveTab(btn.dataset.tab));
    });

    document.querySelectorAll('[data-prompt]').forEach((button) => {
        button.addEventListener('click', () => {
            const input = document.getElementById('queryInput');
            input.value = button.dataset.prompt;
            submitQuery();
        });
    });

    document.getElementById('refreshAnalyticsBtn').addEventListener('click', loadAnalytics);
    document.getElementById('seedDocsBtn').addEventListener('click', seedDefaultDocs);
    document.getElementById('pdfFileInput').addEventListener('change', handleFileSelect);
}

function getAuthHeaders(extra = {}) {
    const token = sessionStorage.getItem(AUTH_KEY);
    return {
        ...extra,
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
}

function syncLanguageSelector(value) {
    const select = document.getElementById('languageSelect');
    if (!select) return;
    if (value && [...select.options].some((option) => option.value === value)) {
        select.value = value;
    } else {
        select.value = 'English';
    }
}

async function checkAuth() {
    const token = sessionStorage.getItem(AUTH_KEY);
    if (!token) {
        showLogin();
        return;
    }

    try {
        const response = await fetch('/api/me', {
            headers: { Authorization: `Bearer ${token}` },
        });

        if (!response.ok) {
            throw new Error('Unauthorized');
        }

        const data = await response.json();
        state.user = data.user;
        renderAuthenticatedView();
        await loadDocuments();
        if (state.user.role === 'admin') {
            await loadAnalytics();
        }
    } catch (error) {
        sessionStorage.removeItem(AUTH_KEY);
        showLogin();
    }
}

function showLogin() {
    document.getElementById('loginScreen').classList.remove('hidden');
    document.getElementById('appShell').classList.add('hidden');
    state.user = null;
}

function renderAuthenticatedView() {
    document.getElementById('loginScreen').classList.add('hidden');
    document.getElementById('appShell').classList.remove('hidden');

    const isAdmin = state.user && state.user.role === 'admin';
    document.getElementById('userName').textContent = state.user.name || state.user.username;
    document.getElementById('userRole').textContent = state.user.role;
    document.getElementById('userBadge').textContent = (state.user.name || state.user.username).slice(0, 2).toUpperCase();
    const otherWorkspaceLink = document.getElementById('otherWorkspaceBtn');
    otherWorkspaceLink.href = '/';
    otherWorkspaceLink.textContent = isAdmin ? 'Open Student Workspace ↗' : 'Open Workspace ↗';

    document.getElementById('adminAnalyticsNav').classList.toggle('hidden', !isAdmin);
    document.getElementById('seedDocsBtn').classList.toggle('hidden', !isAdmin);
    document.getElementById('uploadDocsBtn').classList.toggle('hidden', !isAdmin);

    if (!isAdmin) {
        document.getElementById('analytics-view').classList.remove('active');
        if (state.activeTab === 'analytics-view') {
            setActiveTab('chat-view');
        }
    }

    setActiveTab(state.activeTab || 'chat-view');
}

function logout() {
    sessionStorage.removeItem(AUTH_KEY);
    state.user = null;
    state.activeTab = 'chat-view';
    showLogin();
    document.getElementById('loginUsername').value = '';
    document.getElementById('loginPassword').value = '';
    document.getElementById('loginMessage').classList.add('hidden');
    document.getElementById('togglePasswordBtn').textContent = 'Show';
    document.getElementById('togglePasswordBtn').setAttribute('aria-label', 'Show password');
    document.getElementById('loginPassword').type = 'password';
}

async function handleLogin(event) {
    event.preventDefault();
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value.trim();
    const submitButton = document.getElementById('loginSubmitBtn');
    const loadingIndicator = document.getElementById('loginLoading');
    const messageBox = document.getElementById('loginMessage');

    if (!username || !password) {
        showLoginMessage('Please enter both username and password.', true);
        return;
    }

    submitButton.disabled = true;
    submitButton.querySelector('.btn-label').textContent = 'Signing in...';
    loadingIndicator.classList.remove('hidden');

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Login failed');
        }

        sessionStorage.setItem(AUTH_KEY, data.token);
        state.user = data.user;
        renderAuthenticatedView();
        await loadDocuments();
        if (state.user.role === 'admin') {
            await loadAnalytics();
        }
    } catch (error) {
        showLoginMessage(error.message || 'Unable to login right now. Please try again.', true);
    } finally {
        submitButton.disabled = false;
        submitButton.querySelector('.btn-label').textContent = 'Sign in';
        loadingIndicator.classList.add('hidden');
    }
}

function showLoginMessage(message, isError = false) {
    const box = document.getElementById('loginMessage');
    box.textContent = message;
    box.classList.toggle('error', isError);
    box.classList.remove('hidden');
}

function setActiveTab(tabName) {
    const allowedTabs = ['chat-view', 'documents-view'];
    if (state.user?.role === 'admin') allowedTabs.push('analytics-view');
    if (!allowedTabs.includes(tabName)) tabName = 'chat-view';

    state.activeTab = tabName;
    document.querySelectorAll('.nav-btn').forEach((button) => {
        button.classList.toggle('active', button.dataset.tab === tabName);
    });
    document.querySelectorAll('.view-panel').forEach((panel) => {
        panel.classList.toggle('active', panel.id === tabName);
    });

    const titles = {
        'chat-view': 'AI Chatbot',
        'documents-view': 'Document Library',
        'analytics-view': 'Analytics & Knowledge Gaps',
    };
    document.getElementById('viewTitle').textContent = titles[tabName] || 'Campus Nexus AI';

    if (tabName === 'analytics-view' && state.user && state.user.role === 'admin') {
        loadAnalytics();
    }
}

async function checkHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        const badge = document.getElementById('dbStatus');
        if (!badge) return;

        if (data.status === 'healthy') {
            badge.innerHTML = `<span class="dot ${data.mongodb_connected ? 'green' : 'amber'}"></span><span>${data.mongodb_connected ? 'MongoDB Connected' : 'Local Storage'}</span>`;
        }
    } catch (error) {
        const badge = document.getElementById('dbStatus');
        if (badge) {
            badge.innerHTML = '<span class="dot amber"></span><span>Database Offline</span>';
        }
    }
}

async function submitQuery() {
    const input = document.getElementById('queryInput');
    const query = input.value.trim();
    if (!query) return;

    const language = document.getElementById('languageSelect').value;
    state.retryQuery = query;
    input.value = '';
    appendMessage('user', query);
    const loaderId = appendLoadingMessage();

    try {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ query, language }),
        });

        const data = await response.json();
        removeMessage(loaderId);

        if (!response.ok) {
            throw new Error(data.detail || 'Unable to process this request.');
        }

        if (data.status === 'error') {
            showFriendlyError(data.answer || 'AI service is temporarily unavailable.', () => submitQuery());
            return;
        }

        appendMessage('ai', data.answer, data.status === 'i_dont_know', data.latency_ms, data.language || language, data.status);
        renderCitations(data.citations || []);
        renderAgentLogs(data.agent_logs || []);
    } catch (error) {
        removeMessage(loaderId);
        if (error.message && error.message.includes('Authentication')) {
            logout();
            return;
        }
        showFriendlyError('Unable to connect to the knowledge database.', () => submitQuery());
    }
}

function appendMessage(sender, text, isIdk = false, latencyMs = null, lang = null, status = 'answered') {
    const container = document.getElementById('chatMessages');
    const message = document.createElement('div');
    message.className = `message ${sender}-message${isIdk ? ' idk-message' : ''}`;

    let meta = '';
    if (sender === 'ai') {
        const label = status === 'conversation' ? '💬 Here to help' : isIdk ? '⚠️ Information not found' : '✅ Verified document points';
        meta = `<div class="msg-meta">${label}${latencyMs ? ` • ${latencyMs} ms` : ''}${lang ? ` • ${escapeHtml(lang)}` : ''}</div>`;
    }
    const assistantIntro = sender === 'ai' && !isIdk && status !== 'conversation'
        ? '<div class="assistant-intro">Here\'s what I found in the campus documents:</div>'
        : '';

    message.innerHTML = `
        ${sender === 'ai' ? '<div class="assistant-name">Campus Nexus</div>' : ''}
        ${assistantIntro}
        <div class="msg-bubble">${renderFormattedText(text)}</div>
        ${meta}
    `;

    container.appendChild(message);
    container.scrollTop = container.scrollHeight;
}

function appendLoadingMessage() {
    const container = document.getElementById('chatMessages');
    const id = `loading-${Date.now()}`;
    const message = document.createElement('div');
    message.id = id;
    message.className = 'message ai-message';
    message.innerHTML = '<div class="assistant-name">Campus Nexus</div><div class="msg-bubble loading-bubble">I’m checking the campus documents for you...</div>';
    container.appendChild(message);
    container.scrollTop = container.scrollHeight;
    return id;
}

function removeMessage(id) {
    const element = document.getElementById(id);
    if (element) element.remove();
}

function renderFormattedText(text) {
    if (!text) return '';
    return escapeHtml(text)
        .replace(/\n/g, '<br />')
        .replace(/\[Doc: ([^\]]+)\]/g, '<span class="doc-tag">[Doc: $1]</span>');
}

function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
    })[character]);
}

function showFriendlyError(message, retryHandler) {
    const container = document.getElementById('chatMessages');
    const card = document.createElement('div');
    card.className = 'message ai-message idk-message';
    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    const text = document.createElement('div');
    text.textContent = message;
    bubble.appendChild(text);
    if (retryHandler) {
        const retryButton = document.createElement('button');
        retryButton.className = 'retry-btn';
        retryButton.type = 'button';
        retryButton.textContent = 'Retry';
        bubble.appendChild(retryButton);
    }
    card.appendChild(bubble);
    if (retryHandler) {
        card.querySelector('.retry-btn').addEventListener('click', () => {
            card.remove();
            if (state.retryQuery) {
                document.getElementById('queryInput').value = state.retryQuery;
                submitQuery();
            }
        });
    }
    container.appendChild(card);
    container.scrollTop = container.scrollHeight;
}

function renderCitations(citations) {
    const container = document.getElementById('citationsContainer');
    if (!citations || citations.length === 0) {
        container.innerHTML = '<div class="empty-state">No citations were found for this answer.</div>';
        return;
    }

    container.innerHTML = citations
        .map(
            (citation) => `
                <div class="citation-item">
                    <div class="citation-file">📄 ${escapeHtml(citation.file_name || 'Campus Document')}</div>
                    <div class="citation-meta">Page ${escapeHtml(citation.page_number || 1)} • ${escapeHtml(citation.section || 'General')}</div>
                    <div class="citation-snippet">${escapeHtml(citation.snippet || 'Source excerpt unavailable.')}</div>
                </div>
            `,
        )
        .join('');
}

function renderAgentLogs(logs) {
    const container = document.getElementById('agentLogsContainer');
    if (!logs || logs.length === 0) {
        container.innerHTML = '<div class="empty-state">No agent logs available yet.</div>';
        return;
    }

    container.innerHTML = logs
        .map(
            (log, index) => `
                <div class="agent-row"><span>${index + 1}</span><div><strong>${escapeHtml(log.agent)}</strong><small>${escapeHtml(log.result)}</small></div></div>
            `,
        )
        .join('');
}

async function loadDocuments() {
    try {
        const response = await fetch('/api/documents', { headers: getAuthHeaders() });
        if (!response.ok) {
            throw new Error('Could not load documents');
        }
        const data = await response.json();
        const documents = data.documents || [];
        const grid = document.getElementById('documentsGrid');

        if (!documents.length) {
            grid.innerHTML = '<div class="empty-state">No documents are indexed yet. Upload campus PDFs to begin.</div>';
            return;
        }

        grid.innerHTML = documents
            .map(
                (doc) => `
                    <div class="doc-card">
                        <div class="doc-icon">📄</div>
                        <div class="doc-title">${escapeHtml(doc.file_name || 'Campus Document')}</div>
                        <div class="doc-meta">Pages: ${doc.page_count || 0}</div>
                        <div class="doc-meta">Chunks: ${doc.total_chunks || 0}</div>
                        <div class="doc-status">Indexed</div>
                    </div>
                `,
            )
            .join('');
    } catch (error) {
        const grid = document.getElementById('documentsGrid');
        if (grid) {
            grid.innerHTML = '<div class="empty-state">Unable to load documents right now.</div>';
        }
    }
}

async function seedDefaultDocs() {
    try {
        const response = await fetch('/api/seed', {
            method: 'POST',
            headers: getAuthHeaders(),
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Could not seed documents.');
        }
        await loadDocuments();
        if (state.user && state.user.role === 'admin') {
            await loadAnalytics();
        }
        showFriendlyError(`Seeded ${data.results?.length || 0} sample documents successfully.`, null);
    } catch (error) {
        showFriendlyError('We couldn\'t process this document. Please try again.', null);
    }
}

async function handleFileSelect(event) {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;

    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            headers: { Authorization: `Bearer ${sessionStorage.getItem(AUTH_KEY) || ''}` },
            body: formData,
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Unable to upload document.');
        }

        await loadDocuments();
        event.target.value = '';
        showFriendlyError(`Successfully processed ${data.processed_files || 0} document(s).`, null);
    } catch (error) {
        showFriendlyError('We couldn\'t process this document. Please try again.', null);
    }
}

async function loadAnalytics() {
    if (!state.user || state.user.role !== 'admin') {
        return;
    }

    try {
        const response = await fetch('/api/analytics', {
            headers: getAuthHeaders(),
        });
        if (!response.ok) {
            throw new Error('Admin access required.');
        }

        const data = await response.json();

        document.getElementById('totalQueriesVal').textContent = data.total_queries || 0;
        document.getElementById('answeredVal').textContent = data.answered_count || 0;
        document.getElementById('idkVal').textContent = data.idk_count || 0;
        document.getElementById('indexedDocsVal').textContent = data.total_documents || 0;

        const topQueries = data.top_queries || [];
        const unanswered = data.unanswered_queries || [];

        document.getElementById('topQueriesList').innerHTML = topQueries.length
            ? topQueries.map((entry) => `<li>“${entry.query}” <span>${entry.count}</span></li>`).join('')
            : '<li class="empty-list-item">No questions logged yet.</li>';

        document.getElementById('unansweredList').innerHTML = unanswered.length
            ? unanswered.map((entry) => `<li>“${entry}”</li>`).join('')
            : '<li class="empty-list-item">No knowledge gaps reported.</li>';
    } catch (error) {
        document.getElementById('topQueriesList').innerHTML = '<li class="empty-list-item">Unable to load analytics.</li>';
        document.getElementById('unansweredList').innerHTML = '<li class="empty-list-item">Unable to load analytics.</li>';
    }
}
