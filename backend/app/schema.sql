-- CV2 AI Networking Platform - Database Schema
-- Run this against your Supabase SQL editor to create all tables.
-- All tables use RLS (Row Level Security) policies defined at the bottom.

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================
-- CORE USER TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS cv2_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cv2_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES cv2_users(id) ON DELETE CASCADE,
    industry TEXT DEFAULT 'general',
    summary TEXT DEFAULT '',
    stage TEXT DEFAULT 'onboarding' CHECK (stage IN ('onboarding', 'calibration', 'certified', 'matchable')),
    social_links JSONB DEFAULT '{}',
    social_analysis JSONB,
    ai_profile JSONB,
    activation_score REAL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id)
);

CREATE TABLE IF NOT EXISTS cv2_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES cv2_users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    doc_type TEXT DEFAULT 'cv' CHECK (doc_type IN ('cv', 'certificate', 'portfolio', 'other')),
    content_text TEXT,
    analysis JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- ONBOARDING & CALIBRATION
-- ============================================================

CREATE TABLE IF NOT EXISTS cv2_interviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES cv2_users(id) ON DELETE CASCADE,
    agent_type TEXT NOT NULL CHECK (agent_type IN ('talent', 'hm')),
    context_id TEXT,
    questions JSONB DEFAULT '[]',
    answers JSONB DEFAULT '[]',
    current_index INT DEFAULT 0,
    status TEXT DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'abandoned')),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cv2_test_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES cv2_users(id) ON DELETE CASCADE,
    opportunities JSONB DEFAULT '[]',
    responses JSONB DEFAULT '[]',
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed')),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- CONVERSATIONS & LEARNING
-- ============================================================

CREATE TABLE IF NOT EXISTS cv2_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES cv2_users(id) ON DELETE CASCADE,
    messages JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    quality_score REAL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cv2_collective_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    pattern_type TEXT NOT NULL,
    patterns JSONB DEFAULT '{}',
    source_conversation_id UUID,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cv2_agent_learnings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    learning_type TEXT NOT NULL,
    content JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- AI AGENTS & NETWORKING
-- ============================================================

CREATE TABLE IF NOT EXISTS cv2_agents (
    id TEXT PRIMARY KEY,
    user_id UUID REFERENCES cv2_users(id) ON DELETE SET NULL,
    industry TEXT DEFAULT 'general',
    agent_type TEXT DEFAULT 'talent',
    reputation JSONB DEFAULT '{"score": 50, "matches": 0, "rejections": 0}',
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'probation')),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cv2_agent_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    memory_type TEXT NOT NULL,
    content JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cv2_a2a_candidates (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES cv2_users(id) ON DELETE CASCADE,
    industry TEXT DEFAULT 'general',
    profile JSONB DEFAULT '{}',
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cv2_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES cv2_users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    company TEXT,
    industry TEXT DEFAULT 'general',
    description TEXT DEFAULT '',
    requirements JSONB DEFAULT '[]',
    values JSONB DEFAULT '[]',
    culture JSONB DEFAULT '[]',
    salary_range TEXT,
    location TEXT,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'paused', 'closed')),
    ai_profile JSONB,
    activation_score REAL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cv2_a2a_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES cv2_jobs(id) ON DELETE CASCADE,
    industry TEXT DEFAULT 'general',
    hiring_manager_id UUID,
    profile JSONB DEFAULT '{}',
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cv2_a2a_matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL,
    job_id UUID NOT NULL,
    score REAL DEFAULT 0,
    negotiation_rounds JSONB DEFAULT '[]',
    status TEXT DEFAULT 'proposed' CHECK (status IN ('proposed', 'accepted', 'rejected', 'voided')),
    human_feedback JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- NETWORK EVENTS & INTELLIGENCE
-- ============================================================

CREATE TABLE IF NOT EXISTS cv2_network_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    agent_id TEXT,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cv2_network_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_type TEXT NOT NULL,
    industry TEXT,
    content JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cv2_market_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    industry TEXT NOT NULL,
    data_type TEXT NOT NULL,
    content JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS cv2_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES cv2_users(id) ON DELETE CASCADE,
    notification_type TEXT NOT NULL,
    title TEXT,
    body TEXT,
    read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- MARKETING & CAMPAIGNS
-- ============================================================

CREATE TABLE IF NOT EXISTS cv2_marketing_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    campaign_type TEXT NOT NULL,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'proposed', 'approved', 'active', 'paused', 'terminated', 'completed')),
    target_industry TEXT,
    budget JSONB DEFAULT '{}',
    content JSONB DEFAULT '{}',
    metrics JSONB DEFAULT '{}',
    approved_by TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cv2_landing_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES cv2_marketing_campaigns(id) ON DELETE SET NULL,
    industry TEXT,
    content JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- RAG & EMBEDDINGS
-- ============================================================

CREATE TABLE IF NOT EXISTS cv2_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_type TEXT NOT NULL,
    content_id TEXT NOT NULL,
    content_text TEXT,
    embedding VECTOR(128),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- COST TRACKING
-- ============================================================

CREATE TABLE IF NOT EXISTS cv2_cost_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service TEXT NOT NULL,
    model TEXT,
    tokens_in INT DEFAULT 0,
    tokens_out INT DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON cv2_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_profiles_industry ON cv2_profiles(industry);
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON cv2_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_interviews_user_id ON cv2_interviews(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON cv2_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created ON cv2_conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agents_industry ON cv2_agents(industry);
CREATE INDEX IF NOT EXISTS idx_agents_status ON cv2_agents(status);
CREATE INDEX IF NOT EXISTS idx_agent_memory_agent_id ON cv2_agent_memory(agent_id);
CREATE INDEX IF NOT EXISTS idx_candidates_industry ON cv2_a2a_candidates(industry);
CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON cv2_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_industry ON cv2_jobs(industry);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON cv2_jobs(status);
CREATE INDEX IF NOT EXISTS idx_matches_candidate ON cv2_a2a_matches(candidate_id);
CREATE INDEX IF NOT EXISTS idx_matches_job ON cv2_a2a_matches(job_id);
CREATE INDEX IF NOT EXISTS idx_matches_status ON cv2_a2a_matches(status);
CREATE INDEX IF NOT EXISTS idx_network_events_type ON cv2_network_events(event_type);
CREATE INDEX IF NOT EXISTS idx_network_events_created ON cv2_network_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON cv2_marketing_campaigns(status);
CREATE INDEX IF NOT EXISTS idx_embeddings_type_id ON cv2_embeddings(content_type, content_id);
CREATE INDEX IF NOT EXISTS idx_cost_tracking_service ON cv2_cost_tracking(service);
CREATE INDEX IF NOT EXISTS idx_cost_tracking_created ON cv2_cost_tracking(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_collective_patterns_user ON cv2_collective_patterns(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON cv2_notifications(user_id);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE cv2_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE cv2_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE cv2_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE cv2_interviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE cv2_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE cv2_notifications ENABLE ROW LEVEL SECURITY;

-- Users can only read/write their own data
DROP POLICY IF EXISTS "users_own_data" ON cv2_users;
CREATE POLICY "users_own_data" ON cv2_users
    FOR ALL USING (auth.uid() = id);

DROP POLICY IF EXISTS "profiles_own_data" ON cv2_profiles;
CREATE POLICY "profiles_own_data" ON cv2_profiles
    FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "documents_own_data" ON cv2_documents;
CREATE POLICY "documents_own_data" ON cv2_documents
    FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "interviews_own_data" ON cv2_interviews;
CREATE POLICY "interviews_own_data" ON cv2_interviews
    FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "conversations_own_data" ON cv2_conversations;
CREATE POLICY "conversations_own_data" ON cv2_conversations
    FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "notifications_own_data" ON cv2_notifications;
CREATE POLICY "notifications_own_data" ON cv2_notifications
    FOR ALL USING (auth.uid() = user_id);

-- Service role bypasses RLS (used by backend)
-- Supabase service_role key automatically bypasses RLS

-- ============================================================
-- HELPER FUNCTIONS (bypass RLS for backend operations)
-- ============================================================

-- Ensures a cv2_users record exists for the given auth user ID.
-- Called from backend when creating profiles or uploading documents.
-- SECURITY DEFINER runs with the function owner's privileges (bypasses RLS).
CREATE OR REPLACE FUNCTION ensure_cv2_user(uid UUID)
RETURNS void AS $$
BEGIN
    INSERT INTO cv2_users (id)
    VALUES (uid)
    ON CONFLICT (id) DO NOTHING;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Ensures both a cv2_users and cv2_profiles record exist.
CREATE OR REPLACE FUNCTION ensure_cv2_profile(uid UUID, p_industry TEXT DEFAULT 'general')
RETURNS void AS $$
BEGIN
    INSERT INTO cv2_users (id) VALUES (uid) ON CONFLICT (id) DO NOTHING;
    INSERT INTO cv2_profiles (user_id, industry, summary, stage)
    VALUES (uid, p_industry, '', 'onboarding')
    ON CONFLICT (user_id) DO NOTHING;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Insert a document (bypasses RLS on cv2_documents).
CREATE OR REPLACE FUNCTION insert_cv2_document(
    p_id UUID, p_user_id UUID, p_filename TEXT, p_doc_type TEXT, p_content_text TEXT
)
RETURNS void AS $$
BEGIN
    INSERT INTO cv2_documents (id, user_id, filename, doc_type, content_text)
    VALUES (p_id, p_user_id, p_filename, p_doc_type, p_content_text);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Update document analysis after CV processing.
CREATE OR REPLACE FUNCTION update_document_analysis(p_doc_id UUID, p_analysis JSONB)
RETURNS void AS $$
BEGIN
    UPDATE cv2_documents SET analysis = p_analysis WHERE id = p_doc_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Get documents for a user (bypasses RLS).
CREATE OR REPLACE FUNCTION get_user_documents(p_user_id UUID)
RETURNS TABLE(id UUID, filename TEXT, doc_type TEXT, analysis JSONB, created_at TIMESTAMPTZ) AS $$
BEGIN
    RETURN QUERY
    SELECT d.id, d.filename, d.doc_type, d.analysis, d.created_at
    FROM cv2_documents d
    WHERE d.user_id = p_user_id
    ORDER BY d.created_at DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Log a conversation (bypasses RLS on cv2_conversations).
CREATE OR REPLACE FUNCTION log_cv2_conversation(
    p_id UUID, p_user_id UUID, p_messages JSONB, p_metadata JSONB DEFAULT '{}'
)
RETURNS void AS $$
BEGIN
    INSERT INTO cv2_conversations (id, user_id, messages, metadata)
    VALUES (p_id, p_user_id, p_messages, p_metadata);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Update conversation quality score.
CREATE OR REPLACE FUNCTION update_conversation_quality(p_id UUID, p_score REAL)
RETURNS void AS $$
BEGIN
    UPDATE cv2_conversations SET quality_score = p_score WHERE id = p_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Get profile data for chat context (bypasses RLS on cv2_profiles).
CREATE OR REPLACE FUNCTION get_cv2_profile(p_user_id UUID)
RETURNS TABLE(user_id UUID, industry TEXT, summary TEXT, stage TEXT, social_analysis JSONB) AS $$
BEGIN
    RETURN QUERY
    SELECT p.user_id, p.industry, p.summary, p.stage, p.social_analysis
    FROM cv2_profiles p
    WHERE p.user_id = p_user_id
    LIMIT 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Update profile fields (bypasses RLS).
CREATE OR REPLACE FUNCTION update_cv2_profile(p_user_id UUID, p_industry TEXT DEFAULT NULL, p_summary TEXT DEFAULT NULL, p_stage TEXT DEFAULT NULL)
RETURNS void AS $$
BEGIN
    UPDATE cv2_profiles SET
        industry = COALESCE(p_industry, industry),
        summary = COALESCE(p_summary, summary),
        stage = COALESCE(p_stage, stage),
        updated_at = now()
    WHERE user_id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Get conversation count for a user.
CREATE OR REPLACE FUNCTION get_user_conversation_count(p_user_id UUID)
RETURNS TABLE(count BIGINT) AS $$
BEGIN
    RETURN QUERY SELECT COUNT(*)::BIGINT FROM cv2_conversations WHERE user_id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Get conversation history for a user.
CREATE OR REPLACE FUNCTION get_user_conversations(p_user_id UUID)
RETURNS TABLE(id UUID, messages JSONB, quality_score REAL, created_at TIMESTAMPTZ) AS $$
BEGIN
    RETURN QUERY
    SELECT c.id, c.messages, c.quality_score, c.created_at
    FROM cv2_conversations c
    WHERE c.user_id = p_user_id
    ORDER BY c.created_at DESC
    LIMIT 20;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Get a single conversation by ID (for DSPy learning).
CREATE OR REPLACE FUNCTION get_conversation(p_id UUID)
RETURNS TABLE(id UUID, user_id UUID, messages JSONB, metadata JSONB, quality_score REAL, created_at TIMESTAMPTZ) AS $$
BEGIN
    RETURN QUERY
    SELECT c.id, c.user_id, c.messages, c.metadata, c.quality_score, c.created_at
    FROM cv2_conversations c
    WHERE c.id = p_id
    LIMIT 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Insert collective patterns (for DSPy learning).
CREATE OR REPLACE FUNCTION insert_cv2_pattern(p_user_id UUID, p_conversation_id UUID, p_patterns JSONB, p_pattern_type TEXT)
RETURNS void AS $$
BEGIN
    INSERT INTO cv2_collective_patterns (user_id, source_conversation_id, patterns, pattern_type)
    VALUES (p_user_id, p_conversation_id, p_patterns, p_pattern_type);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Get user patterns (for DSPy learning context).
CREATE OR REPLACE FUNCTION get_user_patterns(p_user_id UUID)
RETURNS TABLE(patterns JSONB) AS $$
BEGIN
    RETURN QUERY
    SELECT cp.patterns FROM cv2_collective_patterns cp
    WHERE cp.user_id = p_user_id
    ORDER BY cp.created_at DESC LIMIT 10;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================
-- UPDATED_AT TRIGGER
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_updated_at ON cv2_users;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON cv2_users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
DROP TRIGGER IF EXISTS set_updated_at ON cv2_profiles;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON cv2_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
DROP TRIGGER IF EXISTS set_updated_at ON cv2_agents;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON cv2_agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
DROP TRIGGER IF EXISTS set_updated_at ON cv2_a2a_candidates;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON cv2_a2a_candidates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
DROP TRIGGER IF EXISTS set_updated_at ON cv2_jobs;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON cv2_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
DROP TRIGGER IF EXISTS set_updated_at ON cv2_a2a_matches;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON cv2_a2a_matches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
DROP TRIGGER IF EXISTS set_updated_at ON cv2_marketing_campaigns;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON cv2_marketing_campaigns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
