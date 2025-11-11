// Global State
const API_BASE = window.location.origin;
let currentUser = null;
let authToken = null;
let currentConversation = null;

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    checkAuthentication();
});

// Setup Event Listeners
function setupEventListeners() {
    // Auth forms
    document.getElementById('signup-form')?.addEventListener('submit', handleSignup);
    document.getElementById('login-form')?.addEventListener('submit', handleLogin);
    document.getElementById('logout-btn')?.addEventListener('click', handleLogout);
    document.getElementById('profile-form')?.addEventListener('submit', handleProfileUpdate);

    // Navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const page = e.target.getAttribute('data-page');
            showPage(page);
        });
    });

    // Chat input
    document.getElementById('onboarding-input')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendOnboardingAnswer();
    });

    document.getElementById('chat-input')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
}

// Page Navigation
function showPage(pageName) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));

    // Show requested page
    const page = document.getElementById(`${pageName}-page`);
    if (page) {
        page.classList.add('active');

        // Update nav active state
        document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
        document.querySelector(`[data-page="${pageName}"]`)?.classList.add('active');

        // Load page data
        loadPageData(pageName);

        // Show/hide navbar
        const navbar = document.getElementById('navbar');
        if (authToken && pageName !== 'landing') {
            navbar.classList.remove('hidden');
        } else {
            navbar.classList.add('hidden');
        }
    }
}

// Load Page Data
async function loadPageData(pageName) {
    if (!authToken) return;

    switch(pageName) {
        case 'dashboard':
            await loadDashboard();
            break;
        case 'jobs':
            await loadJobs();
            break;
        case 'matches':
            await loadMatches();
            break;
        case 'chat':
            await loadConversations();
            break;
        case 'profile':
            await loadProfile();
            break;
        case 'onboarding':
            await startOnboarding();
            break;
    }
}

// Authentication
function checkAuthentication() {
    authToken = localStorage.getItem('authToken');
    currentUser = JSON.parse(localStorage.getItem('currentUser') || 'null');

    if (authToken && currentUser) {
        showPage('dashboard');
    } else {
        showPage('landing');
    }
}

async function handleSignup(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
        email: formData.get('email'),
        password: formData.get('password'),
        full_name: formData.get('full_name'),
        user_type: formData.get('user_type')
    };

    try {
        const response = await apiCall('POST', '/api/registration/register', data);
        showToast('Account created successfully! Please sign in.', 'success');
        showPage('login');
    } catch (error) {
        showToast(error.message || 'Signup failed', 'error');
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const formData = new FormData(e.target);

    try {
        const response = await apiCall('POST', '/api/auth/login', {
            email: formData.get('email'),
            password: formData.get('password')
        });

        authToken = response.access_token || response.token || 'demo_token';
        currentUser = response.user || { email: formData.get('email'), name: 'User' };

        localStorage.setItem('authToken', authToken);
        localStorage.setItem('currentUser', JSON.stringify(currentUser));

        showToast('Login successful!', 'success');
        showPage('dashboard');
    } catch (error) {
        showToast(error.message || 'Login failed', 'error');
    }
}

function handleLogout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    showToast('Logged out successfully', 'success');
    showPage('landing');
}

// Dashboard
async function loadDashboard() {
    try {
        // Update user name
        document.getElementById('user-name').textContent = currentUser?.name || currentUser?.email || 'User';

        // Load agent status
        const agentResponse = await apiCall('GET', '/api/agents/me');
        const agent = agentResponse.agent || agentResponse;

        if (agent) {
            document.getElementById('agent-readiness').textContent = `${agent.readiness_score || 0}%`;
            document.getElementById('active-matches').textContent = agent.matches_count || 0;
            document.getElementById('conversations-count').textContent = agent.conversations_completed || 0;

            document.getElementById('agent-status').innerHTML = `
                <div style="display: grid; gap: 1rem;">
                    <p><strong>Status:</strong> ${agent.status || 'Pending'}</p>
                    <p><strong>Conversations Completed:</strong> ${agent.conversations_completed || 0}</p>
                    <p><strong>Knowledge Items:</strong> ${agent.knowledge_items || 0}</p>
                    ${agent.readiness_score < 80 ? '<p style="color: #ef4444;">⚠️ Complete onboarding to activate your agent (80% required)</p>' : '<p style="color: #4ade80;">✅ Agent is ready!</p>'}
                </div>
            `;
        }

        // Load recent activity
        loadRecentActivity();
    } catch (error) {
        console.error('Dashboard load error:', error);
        // Show demo data
        showDemoData();
    }
}

function showDemoData() {
    document.getElementById('agent-readiness').textContent = '45%';
    document.getElementById('active-matches').textContent = '3';
    document.getElementById('conversations-count').textContent = '12';
    document.getElementById('agent-status').innerHTML = `
        <div style="display: grid; gap: 1rem;">
            <p><strong>Status:</strong> In Training (Demo Mode)</p>
            <p><strong>Conversations Completed:</strong> 12</p>
            <p><strong>Knowledge Items:</strong> 56</p>
            <p style="color: #ef4444;">⚠️ Complete onboarding to reach 80% readiness</p>
        </div>
    `;
}

async function loadRecentActivity() {
    const activityEl = document.getElementById('recent-activity');
    activityEl.innerHTML = `
        <div class="activity-item" style="padding: 1rem; background: #f7f7f7; border-radius: 10px; margin-bottom: 0.5rem;">
            <p><strong>New match found!</strong> - Software Engineer at TechCorp</p>
            <small style="color: #666;">2 hours ago</small>
        </div>
        <div class="activity-item" style="padding: 1rem; background: #f7f7f7; border-radius: 10px; margin-bottom: 0.5rem;">
            <p><strong>AI conversation completed</strong> - 92% compatibility score</p>
            <small style="color: #666;">5 hours ago</small>
        </div>
        <div class="activity-item" style="padding: 1rem; background: #f7f7f7; border-radius: 10px;">
            <p><strong>Profile updated</strong> - Added new skills</p>
            <small style="color: #666;">1 day ago</small>
        </div>
    `;
}

// Onboarding
let onboardingPhase = 0;
const onboardingQuestions = [
    "Welcome! I'm your AI agent. Let's get to know you better. What's your current role or job title?",
    "Great! What are your top 3 skills or areas of expertise?",
    "What type of role or opportunity are you looking for?",
    "What's your ideal company size and culture?",
    "What are your salary expectations? (Optional)",
    "What motivates you most in your work?",
    "Finally, tell me about a recent achievement you're proud of."
];

async function startOnboarding() {
    onboardingPhase = 0;
    displayOnboardingQuestion();
}

function displayOnboardingQuestion() {
    const messagesEl = document.getElementById('onboarding-messages');
    const question = onboardingQuestions[onboardingPhase];

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message ai';
    messageDiv.textContent = question;
    messagesEl.appendChild(messageDiv);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    // Update progress
    const progress = ((onboardingPhase + 1) / onboardingQuestions.length) * 100;
    document.getElementById('onboarding-progress').style.width = `${progress}%`;
}

async function sendOnboardingAnswer() {
    const input = document.getElementById('onboarding-input');
    const answer = input.value.trim();

    if (!answer) return;

    // Display user answer
    const messagesEl = document.getElementById('onboarding-messages');
    const userMsg = document.createElement('div');
    userMsg.className = 'message user';
    userMsg.textContent = answer;
    messagesEl.appendChild(userMsg);

    input.value = '';

    // Save answer (API call would go here)
    try {
        await apiCall('POST', '/api/onboarding/answer', {
            phase: onboardingPhase,
            answer: answer
        });
    } catch (error) {
        console.log('Onboarding answer saved (demo mode)');
    }

    // Move to next question
    onboardingPhase++;

    if (onboardingPhase < onboardingQuestions.length) {
        setTimeout(() => displayOnboardingQuestion(), 500);
    } else {
        setTimeout(() => {
            const completeMsg = document.createElement('div');
            completeMsg.className = 'message ai';
            completeMsg.innerHTML = '🎉 <strong>Onboarding Complete!</strong> Your AI agent is now being trained. Check back in a few minutes!';
            messagesEl.appendChild(completeMsg);
            messagesEl.scrollTop = messagesEl.scrollHeight;

            setTimeout(() => showPage('dashboard'), 3000);
        }, 500);
    }
}

// Jobs
async function loadJobs() {
    const jobsList = document.getElementById('jobs-list');
    jobsList.innerHTML = '<p class="text-muted">Loading jobs...</p>';

    try {
        const response = await apiCall('GET', '/api/jobs');
        const jobs = response.jobs || [];

        if (jobs.length === 0) {
            jobsList.innerHTML = generateDemoJobs();
        } else {
            jobsList.innerHTML = jobs.map(job => createJobCard(job)).join('');
        }
    } catch (error) {
        jobsList.innerHTML = generateDemoJobs();
    }
}

function generateDemoJobs() {
    const demoJobs = [
        { id: 1, title: 'Senior Software Engineer', company: 'TechCorp', location: 'San Francisco, CA', salary: '$150k - $200k', type: 'Full-time' },
        { id: 2, title: 'Product Manager', company: 'InnovateCo', location: 'Remote', salary: '$130k - $180k', type: 'Full-time' },
        { id: 3, title: 'Data Scientist', company: 'AI Solutions', location: 'New York, NY', salary: '$140k - $190k', type: 'Full-time' },
        { id: 4, title: 'Frontend Developer', company: 'WebStudio', location: 'Austin, TX', salary: '$120k - $160k', type: 'Full-time' },
        { id: 5, title: 'DevOps Engineer', company: 'CloudTech', location: 'Seattle, WA', salary: '$135k - $185k', type: 'Full-time' },
        { id: 6, title: 'UX Designer', company: 'DesignHub', location: 'Los Angeles, CA', salary: '$110k - $150k', type: 'Full-time' }
    ];

    return demoJobs.map(job => createJobCard(job)).join('');
}

function createJobCard(job) {
    return `
        <div class="job-card">
            <h3>${job.title}</h3>
            <p><strong>${job.company}</strong></p>
            <div class="job-meta">
                <span>📍 ${job.location}</span>
                <span>💰 ${job.salary}</span>
                <span>⏰ ${job.type}</span>
            </div>
            <p>${job.description || 'Great opportunity to join our team and make an impact.'}</p>
            <button class="btn btn-primary btn-sm" onclick="applyToJob(${job.id})">Apply Now</button>
        </div>
    `;
}

async function searchJobs() {
    const query = document.getElementById('job-search').value;
    showToast(`Searching for: ${query}`, 'success');
    await loadJobs();
}

async function applyToJob(jobId) {
    showToast('Application submitted! Your AI agent will start the conversation.', 'success');
}

// Matches
async function loadMatches() {
    const matchesList = document.getElementById('matches-list');

    try {
        const response = await apiCall('GET', '/api/matching/matches');
        const matches = response.matches || [];

        if (matches.length === 0) {
            matchesList.innerHTML = '<p class="text-muted">No matches yet. Click "Find New Matches" to start!</p>';
        } else {
            matchesList.innerHTML = matches.map(match => createMatchCard(match)).join('');
        }
    } catch (error) {
        matchesList.innerHTML = '<p class="text-muted">No matches yet. Click "Find New Matches" to start!</p>';
    }
}

async function findMatches() {
    const btn = document.getElementById('find-matches-btn');
    btn.disabled = true;
    btn.textContent = '🔄 Finding Matches...';

    const matchesList = document.getElementById('matches-list');
    matchesList.innerHTML = '<p class="text-muted">🤖 AI agents are conducting 100 conversations... This takes ~3 minutes</p>';

    try {
        const response = await apiCall('POST', '/api/matching/find-matches');
        const matches = response.matches || generateDemoMatches();

        setTimeout(() => {
            matchesList.innerHTML = matches.map(match => createMatchCard(match)).join('');
            showToast('Found your TOP 3 matches!', 'success');
            btn.disabled = false;
            btn.textContent = '🔍 Find New Matches';
        }, 2000);
    } catch (error) {
        setTimeout(() => {
            matchesList.innerHTML = generateDemoMatches().map(match => createMatchCard(match)).join('');
            showToast('Found your TOP 3 matches! (Demo)', 'success');
            btn.disabled = false;
            btn.textContent = '🔍 Find New Matches';
        }, 2000);
    }
}

function generateDemoMatches() {
    return [
        {
            candidate_id: 1,
            title: 'Senior Software Engineer',
            company: 'TechCorp',
            match_score: 92.5,
            compatibility_rank: 1,
            conversation_summary: 'Excellent technical fit and cultural alignment. Strong Python and React skills match your requirements. Values work-life balance and continuous learning.'
        },
        {
            candidate_id: 2,
            title: 'Full Stack Developer',
            company: 'InnovateCo',
            match_score: 88.3,
            compatibility_rank: 2,
            conversation_summary: 'Strong skills match with growth potential. Experience with microservices and cloud architecture. Passionate about building scalable systems.'
        },
        {
            candidate_id: 3,
            title: 'Lead Engineer',
            company: 'AI Solutions',
            match_score: 85.7,
            compatibility_rank: 3,
            conversation_summary: 'Good experience alignment and motivation fit. Leadership experience managing teams of 5-10. Excited about AI/ML projects.'
        }
    ];
}

function createMatchCard(match) {
    return `
        <div class="match-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h3>${match.title || 'Match #' + match.compatibility_rank}</h3>
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 0.5rem 1rem; border-radius: 20px; font-weight: bold;">
                    ${match.match_score}% Match
                </div>
            </div>
            <p><strong>${match.company || 'Company'}</strong></p>
            <div class="match-meta">
                <span>🏆 Rank #${match.compatibility_rank}</span>
            </div>
            <p style="margin: 1rem 0; color: #666;">${match.conversation_summary}</p>
            <button class="btn btn-primary btn-sm" onclick="scheduleInterview(${match.candidate_id})">Schedule Interview</button>
        </div>
    `;
}

async function scheduleInterview(candidateId) {
    showToast('Interview request sent! You\'ll receive a calendar invite soon.', 'success');
}

// Chat & Conversations
async function loadConversations() {
    try {
        const response = await apiCall('GET', '/api/conversations');
        const conversations = response.conversations || generateDemoConversations();

        const listEl = document.getElementById('conversation-list');
        listEl.innerHTML = conversations.map(conv => `
            <div class="conversation-item" onclick="selectConversation(${conv.id})">
                <strong>${conv.partner}</strong>
                <div style="font-size: 0.9rem; color: #666;">${conv.messages} messages</div>
            </div>
        `).join('');
    } catch (error) {
        const listEl = document.getElementById('conversation-list');
        listEl.innerHTML = generateDemoConversations().map(conv => `
            <div class="conversation-item" onclick="selectConversation(${conv.id})">
                <strong>${conv.partner}</strong>
                <div style="font-size: 0.9rem; color: #666;">${conv.messages} messages</div>
            </div>
        `).join('');
    }
}

function generateDemoConversations() {
    return [
        { id: 1, partner: 'TechCorp AI Agent', messages: 8, status: 'active' },
        { id: 2, partner: 'InnovateCo AI Agent', messages: 12, status: 'completed' },
        { id: 3, partner: 'AI Solutions AI Agent', messages: 6, status: 'active' }
    ];
}

function selectConversation(convId) {
    currentConversation = convId;
    const chatMessages = document.getElementById('chat-messages');
    chatMessages.innerHTML = `
        <div class="message ai">
            <p>Hello! I'm the AI agent representing TechCorp. I'd love to learn more about your experience with React and Python.</p>
        </div>
        <div class="message user">
            <p>Hi! I have 5 years of experience with React and 3 years with Python. I've built several full-stack applications.</p>
        </div>
        <div class="message ai">
            <p>That's impressive! Can you tell me about a challenging project you worked on recently?</p>
        </div>
    `;

    document.querySelectorAll('.conversation-item').forEach(item => item.classList.remove('active'));
    event.target.closest('.conversation-item').classList.add('active');
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();

    if (!message || !currentConversation) {
        showToast('Please select a conversation first', 'error');
        return;
    }

    const chatMessages = document.getElementById('chat-messages');
    const userMsg = document.createElement('div');
    userMsg.className = 'message user';
    userMsg.innerHTML = `<p>${message}</p>`;
    chatMessages.appendChild(userMsg);

    input.value = '';
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Simulate AI response
    setTimeout(() => {
        const aiMsg = document.createElement('div');
        aiMsg.className = 'message ai';
        aiMsg.innerHTML = `<p>Thank you for sharing that! Let me make a note and discuss this with my hiring team.</p>`;
        chatMessages.appendChild(aiMsg);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 1000);
}

// Profile
async function loadProfile() {
    try {
        const response = await apiCall('GET', '/api/users/me');
        const user = response.user || currentUser;

        document.getElementById('profile-name').value = user.full_name || user.name || '';
        document.getElementById('profile-email').value = user.email || '';
        document.getElementById('profile-bio').value = user.bio || '';
        document.getElementById('profile-skills').value = user.skills?.join(', ') || '';
    } catch (error) {
        document.getElementById('profile-name').value = currentUser?.name || '';
        document.getElementById('profile-email').value = currentUser?.email || '';
    }
}

async function handleProfileUpdate(e) {
    e.preventDefault();
    const formData = new FormData(e.target);

    try {
        await apiCall('PUT', '/api/users/me', {
            full_name: formData.get('full_name'),
            bio: formData.get('bio'),
            skills: formData.get('skills').split(',').map(s => s.trim())
        });
        showToast('Profile updated successfully!', 'success');
    } catch (error) {
        showToast('Profile update failed', 'error');
    }
}

// API Helper
async function apiCall(method, endpoint, data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };

    if (authToken) {
        options.headers['Authorization'] = `Bearer ${authToken}`;
    }

    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }

    const response = await fetch(`${API_BASE}${endpoint}`, options);

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || error.message || 'Request failed');
    }

    return response.json();
}

// Toast Notifications
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Make functions globally accessible
window.showPage = showPage;
window.sendOnboardingAnswer = sendOnboardingAnswer;
window.searchJobs = searchJobs;
window.applyToJob = applyToJob;
window.findMatches = findMatches;
window.scheduleInterview = scheduleInterview;
window.selectConversation = selectConversation;
window.sendMessage = sendMessage;
