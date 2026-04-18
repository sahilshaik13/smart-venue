-- setup_tables.sql
-- Run this in the Supabase SQL Editor.

-- 1. Create chat_messages table tied to auth.users
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL, -- Logical session (e.g. current map view session)
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    zones_referenced TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Create zone_snapshots for historical density tracking
CREATE TABLE IF NOT EXISTS public.zone_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_minute INTEGER,
    match_phase TEXT,
    snapshot_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. Create wait_predictions for logging AI performance
CREATE TABLE IF NOT EXISTS public.wait_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    zone_id TEXT NOT NULL,
    predicted_wait_minutes INTEGER NOT NULL,
    confidence FLOAT NOT NULL,
    trend TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 4. Enable RLS (Row Level Security)
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;

-- 5. Create policies so users can only read/write their own chat messages
CREATE POLICY "Users can view their own chat messages" 
ON public.chat_messages FOR SELECT 
TO authenticated 
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own chat messages" 
ON public.chat_messages FOR INSERT 
TO authenticated 
WITH CHECK (auth.uid() = user_id);

-- 6. Allow service role to view/manage all for admin logic
CREATE POLICY "Service role full access" 
ON public.chat_messages 
TO service_role 
USING (true) 
WITH CHECK (true);
