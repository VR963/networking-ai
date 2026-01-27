/**
 * CV 2.0 - Frontend Configuration
 * Set your Supabase credentials here.
 * This file is loaded before app.js on all pages.
 */

// Supabase project URL (from Supabase dashboard → Settings → API)
window.CV2_SUPABASE_URL = 'https://tksllvfftstxyecfzwwj.supabase.co';

// Supabase anon/public key (from Supabase dashboard → Settings → API → anon public)
// Must start with 'eyJ...' — paste your key below:
window.CV2_SUPABASE_ANON_KEY = '';

// Backend API URL (set this if frontend is served separately from backend)
// Leave empty if served from same origin (recommended: use backend to serve frontend)
window.CV2_API_URL = window.location.port === '8080' ? 'http://localhost:8000' : '';
