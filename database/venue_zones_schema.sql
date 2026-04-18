-- Optimized SQL Schema for HITEX Ground-Truth Persistence
-- Run this in the Supabase SQL Editor.

-- 1. Create venue_zones table for static ground-truth storage
CREATE TABLE IF NOT EXISTS public.venue_zones (
    zone_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL, -- gate | seating | concession | parking
    capacity INTEGER DEFAULT 1000,
    lat FLOAT NOT NULL,
    lng FLOAT NOT NULL,
    x_hint FLOAT DEFAULT 0.5,
    y_hint FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Enable RLS
ALTER TABLE public.venue_zones ENABLE ROW LEVEL SECURITY;

-- 3. Public Read Access (Everyone can see the map layout)
CREATE POLICY "Public read access for venue zones" 
ON public.venue_zones FOR SELECT 
TO public 
USING (true);

-- 4. Admin Write Access (Only authenticated admins/service role can update truth)
CREATE POLICY "Admin write access for venue zones" 
ON public.venue_zones FOR ALL 
TO service_role 
USING (true) 
WITH CHECK (true);

-- 5. UPSERT Logic Demo (How to update the truth via JSON)
-- Use this pattern when ingesting a new calibration:
/*
INSERT INTO public.venue_zones (zone_id, name, type, capacity, lat, lng, x_hint, y_hint)
VALUES ('gate_main', 'Main Gate Entrance (MG)', 'gate', 5000, 17.469243, 78.376628, 0.5, 0.5)
ON CONFLICT (zone_id) DO UPDATE SET
    lat = EXCLUDED.lat,
    lng = EXCLUDED.lng,
    x_hint = EXCLUDED.x_hint,
    y_hint = EXCLUDED.y_hint,
    updated_at = now();
*/

-- 6. Add trigger for automatic updated_at timestamp
CREATE OR REPLACE FUNCTION update_timestamp_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_venue_zones_timestamp
BEFORE UPDATE ON public.venue_zones
FOR EACH ROW
EXECUTE PROCEDURE update_timestamp_column();
