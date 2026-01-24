/**
 * CV 2.0 - Shared Application Module
 * Handles auth state, navigation, and API communication.
 *
 * Usage: Include this script before page-specific scripts.
 *   <script src="/js/app.js"></script>
 */

const APP = {
    // Configuration - set via environment or defaults
    API_URL: window.CV2_API_URL || '',
    SUPABASE_URL: window.CV2_SUPABASE_URL || '',
    SUPABASE_ANON_KEY: window.CV2_SUPABASE_ANON_KEY || '',

    // Auth state
    _user: null,
    _session: null,
    _supabase: null,

    /**
     * Initialize the app module. Call on every page load.
     */
    async init() {
        // Load config from meta tags if present
        const metaApi = document.querySelector('meta[name="api-url"]');
        const metaSupa = document.querySelector('meta[name="supabase-url"]');
        const metaKey = document.querySelector('meta[name="supabase-anon-key"]');
        if (metaApi) this.API_URL = metaApi.content;
        if (metaSupa) this.SUPABASE_URL = metaSupa.content;
        if (metaKey) this.SUPABASE_ANON_KEY = metaKey.content;

        // Try to restore session
        await this.restoreSession();

        // Render navigation
        this.renderNav();
    },

    /**
     * Initialize Supabase client (lazy, loaded from CDN).
     */
    getSupabase() {
        if (this._supabase) return this._supabase;
        if (!window.supabase || !this.SUPABASE_URL || !this.SUPABASE_ANON_KEY) {
            return null;
        }
        this._supabase = window.supabase.createClient(
            this.SUPABASE_URL,
            this.SUPABASE_ANON_KEY
        );
        return this._supabase;
    },

    /**
     * Restore session from Supabase or localStorage fallback.
     */
    async restoreSession() {
        const sb = this.getSupabase();
        if (sb) {
            try {
                const { data } = await sb.auth.getSession();
                if (data.session) {
                    this._session = data.session;
                    this._user = data.session.user;
                    return;
                }
            } catch (e) {
                console.debug('Supabase session restore failed:', e);
            }
        }

        // Fallback: check localStorage for dev/demo mode
        const stored = localStorage.getItem('cv2_user');
        if (stored) {
            try {
                this._user = JSON.parse(stored);
            } catch (e) {
                localStorage.removeItem('cv2_user');
            }
        }
    },

    /**
     * Sign up with email/password.
     */
    async signUp(email, password) {
        const sb = this.getSupabase();
        if (!sb) {
            // Fallback: demo mode - create local user
            const user = { id: crypto.randomUUID(), email, role: 'user' };
            this._user = user;
            localStorage.setItem('cv2_user', JSON.stringify(user));
            return { user, error: null };
        }

        const { data, error } = await sb.auth.signUp({ email, password });
        if (!error && data.user) {
            this._user = data.user;
            this._session = data.session;
        }
        return { user: data?.user, error };
    },

    /**
     * Sign in with email/password.
     */
    async signIn(email, password) {
        const sb = this.getSupabase();
        if (!sb) {
            // Fallback: demo mode
            const user = { id: email, email, role: 'user' };
            this._user = user;
            localStorage.setItem('cv2_user', JSON.stringify(user));
            return { user, error: null };
        }

        const { data, error } = await sb.auth.signInWithPassword({ email, password });
        if (!error && data.user) {
            this._user = data.user;
            this._session = data.session;
        }
        return { user: data?.user, error };
    },

    /**
     * Sign out.
     */
    async signOut() {
        const sb = this.getSupabase();
        if (sb) {
            await sb.auth.signOut();
        }
        this._user = null;
        this._session = null;
        localStorage.removeItem('cv2_user');
        window.location.href = '/';
    },

    /**
     * Get the current authenticated user.
     */
    getUser() {
        return this._user;
    },

    /**
     * Get the user ID (works with both Supabase and demo mode).
     */
    getUserId() {
        return this._user?.id || null;
    },

    /**
     * Check if user is authenticated.
     */
    isAuthenticated() {
        return this._user !== null;
    },

    /**
     * Get auth token for API calls.
     */
    getToken() {
        return this._session?.access_token || null;
    },

    /**
     * Make an authenticated API call.
     */
    async api(path, options = {}) {
        const url = `${this.API_URL}${path}`;
        const headers = {
            'Content-Type': 'application/json',
            ...(options.headers || {}),
        };

        const token = this.getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(url, {
            ...options,
            headers,
            body: options.body ? JSON.stringify(options.body) : undefined,
        });

        if (response.status === 401) {
            // Token expired - try refresh
            await this.restoreSession();
            if (!this.isAuthenticated()) {
                window.location.href = '/auth.html';
                return null;
            }
        }

        return response.json();
    },

    /**
     * Require authentication - redirect to login if not authenticated.
     */
    requireAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = '/auth.html?redirect=' + encodeURIComponent(window.location.pathname);
            return false;
        }
        return true;
    },

    /**
     * Render the navigation bar.
     */
    renderNav() {
        const navEl = document.getElementById('cv2-nav');
        if (!navEl) return;

        const isAuthed = this.isAuthenticated();
        const currentPath = window.location.pathname;

        const navLink = (href, label) => {
            const active = currentPath === href || currentPath === href.replace('.html', '');
            return `<a href="${href}" class="text-sm ${
                active ? 'text-[#4F46E5] font-medium' : 'text-gray-500 hover:text-gray-900'
            } transition">${label}</a>`;
        };

        navEl.className = 'fixed top-0 left-0 right-0 bg-white/80 backdrop-blur-lg border-b border-gray-100 z-50';
        navEl.innerHTML = `
            <div class="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
                <a href="/" class="text-xl font-bold tracking-tight text-gray-900">CV<span style="color:#4F46E5">2.0</span></a>
                <div class="hidden md:flex items-center gap-6">
                    ${isAuthed ? `
                        ${navLink('/dashboard.html', 'Dashboard')}
                        ${navLink('/talent-app.html', 'Talent')}
                        ${navLink('/hm-onboarding.html', 'Hiring')}
                        ${navLink('/job-command-center.html', 'Matches')}
                    ` : `
                        ${navLink('/talent-app.html', 'For Talent')}
                        ${navLink('/hm-onboarding.html', 'For Hiring')}
                    `}
                </div>
                <div class="flex items-center gap-4">
                    ${isAuthed ? `
                        <span class="text-xs text-gray-400 hidden sm:block">${this._user.email || this._user.id}</span>
                        <button onclick="APP.signOut()" class="text-sm text-red-500 hover:text-red-700 font-medium transition">Sign Out</button>
                    ` : `
                        <a href="/auth.html" class="text-sm text-gray-600 hover:text-gray-900 font-medium transition">Sign In</a>
                        <a href="/auth.html?mode=signup" class="bg-[#4F46E5] text-white px-4 py-2 rounded-lg text-sm hover:bg-[#3730A3] transition">Get Started</a>
                    `}
                </div>
            </div>
        `;
    }
    /**
     * Register service worker for PWA + push notifications.
     */
    async registerServiceWorker() {
        if (!('serviceWorker' in navigator)) return null;
        try {
            const reg = await navigator.serviceWorker.register('/sw.js');
            this._swRegistration = reg;
            return reg;
        } catch (e) {
            console.warn('SW registration failed:', e);
            return null;
        }
    },

    /**
     * Request push notification permission and subscribe.
     * Returns the subscription object or null.
     */
    async subscribePush() {
        if (!('Notification' in window)) return null;

        const permission = await Notification.requestPermission();
        if (permission !== 'granted') return null;

        const reg = this._swRegistration || await this.registerServiceWorker();
        if (!reg) return null;

        try {
            // For demo/testing, use a placeholder VAPID key
            // In production, replace with your actual VAPID public key
            const vapidKey = window.CV2_VAPID_PUBLIC_KEY || 'BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkCs7q_4aG9l7oy5m_MnEbRM7g0ChCVJFoFmg5xBWo';
            const subscription = await reg.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this._urlBase64ToUint8Array(vapidKey),
            });

            // Send subscription to backend
            await this.api('/user/push-subscribe', {
                method: 'POST',
                body: { subscription: subscription.toJSON() },
            });

            return subscription;
        } catch (e) {
            console.warn('Push subscription failed:', e);
            return null;
        }
    },

    /**
     * Show a local notification (for testing without push server).
     */
    async showLocalNotification(title, body, url) {
        if (Notification.permission !== 'granted') {
            await Notification.requestPermission();
        }
        if (Notification.permission !== 'granted') return;

        const reg = this._swRegistration || await this.registerServiceWorker();
        if (!reg) return;

        reg.showNotification(title, {
            body,
            icon: '/icons/icon-192.svg',
            tag: 'cv2-local-' + Date.now(),
            data: { url: url || '/dashboard.html' },
            vibrate: [100, 50, 100],
        });
    },

    _urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
        const rawData = atob(base64);
        return Uint8Array.from([...rawData].map(c => c.charCodeAt(0)));
    },
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    APP.init();
    APP.registerServiceWorker();
});
