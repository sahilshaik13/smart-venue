import React, { useState, useEffect } from 'react';
import type { VenueSnapshot } from './types';
import { HeatmapSection } from './components/HeatmapSection';
import { WaitTimesSection } from './components/WaitTimesSection';
import { GraphSection } from './components/GraphSection';
import { MapSection } from './components/MapSection';
import { ChatWidget } from './components/ChatWidget';
import { FloorplansGallery } from './components/FloorplansGallery';
import { supabase } from './supabaseClient';
import type { Session } from '@supabase/supabase-js';

import { getApiUrl } from './utils/config';

import { SimulatorConsole } from './components/SimulatorConsole';

function App() {
  const [snapshot, setSnapshot] = useState<VenueSnapshot | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshTrigger, setRefreshTrigger] = useState(Date.now());
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });
    return () => subscription.unsubscribe();
  }, []);

  // 📡 High-Speed WebSocket Real-time Stream
  useEffect(() => {
    if (!session) return;

    let socket: WebSocket | null = null;
    let reconnectTimeout: any = null;

    const connect = () => {
      const apiUrl = getApiUrl();
      const wsUrl = apiUrl.replace(/^http/, 'ws') + '/api/ws/venue';
      
      socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        setWsConnected(true);
        console.log('Venue Intelligence Stream Connected');
      };

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'SNAPSHOT_UPDATE') {
            setSnapshot(message.data);
            setRefreshTrigger(Date.now()); // Pulse downstream components
          }
        } catch (err) {
          console.error('Socket message error:', err);
        }
      };

      socket.onclose = () => {
        setWsConnected(false);
        console.warn('Venue Intelligence Stream Disconnected. Reconnecting...');
        reconnectTimeout = setTimeout(connect, 3000); // 3s backoff
      };

      socket.onerror = (err) => {
        console.error('WebSocket Error:', err);
        socket?.close();
      };
    };

    connect();

    return () => {
      socket?.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, [session]);

  const refreshDashboardContent = async () => {
    // This now serves as a manual trigger for non-websocket updates
    // or to force a state refresh in the simulator console
    setRefreshTrigger(Date.now());
  };

  const handleLogin = () => {
    supabase.auth.signInWithOAuth({ 
      provider: 'google',
      options: { redirectTo: window.location.origin }
    });
  };

  const handleLogout = () => {
    supabase.auth.signOut();
  };

  const handleZoneClick = (zoneName: string, status: string) => {
    console.log(`Focusing zone: ${zoneName} (${status})`);
  };

  if (loading) return null;

  if (!session) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-logo">Smart<span>Venue</span> AI</div>
          <div className="auth-title">Production Venue Intelligence Platform</div>
          <p style={{ color: 'var(--text-muted)', marginBottom: '24px', fontSize: '0.9rem' }}>
            Predict crowd flow, manage wait times, and interact with venue digital twins using Gemini 2.5.
          </p>
          <button className="google-login-btn" onClick={handleLogin}>
            <img src="https://www.gstatic.com/images/branding/product/1x/gsa_512dp.png" alt="Google" className="google-icon" />
            Sign in with Google
          </button>
          <p style={{ marginTop: '24px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            &copy; 2026 HITEX Exhibition Center &bull; Powered by Google Cloud
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <a href="#main-content" className="skip-link">Skip to main content</a>

      <header role="banner">
        <div className="logo">Smart<span>Venue</span> AI</div>
        
        <div className="header-meta">
          <SimulatorConsole 
            sessionToken={session.access_token} 
            onRefresh={refreshDashboardContent} 
          />
          
          <div className="user-profile" title={session.user.email}>
            <img src={session.user.user_metadata.avatar_url} alt="User Avatar" className="user-avatar" />
            <button className="btn-logout" onClick={handleLogout}>Log out</button>
          </div>
          
          <span className="match-phase" id="match-phase" aria-live="polite">
            {snapshot ? snapshot.match_phase.toUpperCase() : 'LOADING…'}
          </span>
          <span className={`live-dot ${wsConnected ? 'active' : ''}`} aria-label="Live data status">
            {wsConnected ? 'LIVE' : 'SYNCING…'}
          </span>
        </div>
      </header>

      <main id="main-content" role="main">
        <HeatmapSection snapshot={snapshot} onZoneClick={handleZoneClick} />
        <WaitTimesSection zones={snapshot ? snapshot.zones : []} />
        <GraphSection onZoneClick={handleZoneClick} refreshTrigger={refreshTrigger} />
        <MapSection zones={snapshot ? snapshot.zones : []} particles={snapshot?.particles} />
        <FloorplansGallery />
      </main>

      <ChatWidget sessionToken={session.access_token} />
    </>
  );
}

export default App;
