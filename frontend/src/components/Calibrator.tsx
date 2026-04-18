import React, { useState, useEffect } from 'react';
import { MapSection } from './MapSection';
import { GraphSection } from './GraphSection';
import type { VenueSnapshot, Zone } from '../types';

interface CalibratorProps {
  initialSnapshot: VenueSnapshot | null;
}

export const Calibrator: React.FC<CalibratorProps> = ({ initialSnapshot }) => {
  const [zones, setZones] = useState<Zone[]>(initialSnapshot?.zones || []);
  const [autoSync, setAutoSync] = useState(true);

  useEffect(() => {
    if (initialSnapshot && zones.length === 0) {
      setZones(initialSnapshot.zones);
    }
  }, [initialSnapshot]);

  // Project Lat/Lng to 0-1 Graph coordinates (HITEX Bounds)
  const projectToGraph = (lat: number, lng: number) => {
    const latTop = 17.4720, latBottom = 17.4688;
    const lngLeft = 78.3700, lngRight = 78.3780;
    
    return {
      x: (lng - lngLeft) / (lngRight - lngLeft),
      y: (latTop - lat) / (latTop - latBottom) // Y=0 is top
    };
  };

  const handleMapUpdate = (zoneId: string, lat: number, lng: number) => {
    setZones(prev => prev.map(z => {
      if (z.zone_id === zoneId) {
        const updates: any = { lat, lng };
        if (autoSync) {
          const projected = projectToGraph(lat, lng);
          updates.x_hint = projected.x;
          updates.y_hint = projected.y;
        }
        return { ...z, ...updates };
      }
      return z;
    }));
  };

  const handleGraphUpdate = (zoneId: string, x: number, y: number) => {
    setZones(prev => prev.map(z => 
      z.zone_id === zoneId ? { ...z, x_hint: x, y_hint: y } : z
    ));
  };

  const downloadConfig = () => {
    const config = {
      timestamp: new Date().toISOString(),
      zones: zones.map(z => ({
        id: z.zone_id,
        name: z.name,
        lat: z.lat,
        lng: z.lng,
        x_hint: z.x_hint || 0.5,
        y_hint: z.y_hint || 0.5
      }))
    };

    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `hitex_calibration_${new Date().getTime()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="calibrator-workspace" style={{ 
      display: 'grid', 
      gridTemplateColumns: '380px 1fr', 
      width: '100%',
      height: 'calc(100vh - 140px)', 
      gap: '24px', 
      padding: '0',
      background: '#0a0d12'
    }}>
      <aside className="calibrator-sidebar card" style={{ 
        display: 'flex', 
        flexDirection: 'column',
        padding: '24px',
        border: '1px solid #1e2733',
        background: '#111827'
      }}>
        <div className="sidebar-header" style={{ marginBottom: '24px' }}>
          <h2 style={{ fontSize: '1.2rem', marginBottom: '8px', color: '#f3f4f6' }}>Calibration Terminal</h2>
          <p style={{ fontSize: '0.8rem', color: '#9ca3af' }}>
            Snapping physical markers to satellite footprints and logical nodes to graph clusters.
          </p>
        </div>
        
        <button 
          className="btn-primary" 
          onClick={downloadConfig}
          style={{ 
            width: '100%', 
            padding: '12px',
            marginBottom: '24px', 
            background: '#10b981',
            borderRadius: '8px',
            fontWeight: 'bold',
            fontSize: '0.9rem',
            boxShadow: '0 4px 12px rgba(16, 185, 129, 0.2)'
          }}
        >
          ⬇ Export Final Ground Truth
        </button>

        <div className="sync-control" style={{ 
          marginBottom: '24px', 
          padding: '12px', 
          background: '#1f2937', 
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          border: '1px solid #374151'
        }}>
          <span style={{ fontSize: '0.8rem', color: '#e5e7eb', fontWeight: '500' }}>Mirror Map to Graph</span>
          <input 
            type="checkbox" 
            checked={autoSync} 
            onChange={(e) => setAutoSync(e.target.checked)}
            style={{ width: '18px', height: '18px', cursor: 'pointer' }}
          />
        </div>

        <div className="zone-list" style={{ 
          flex: 1, 
          overflowY: 'auto', 
          paddingRight: '8px',
          scrollbarWidth: 'thin',
          scrollbarColor: '#374151 #111827'
        }}>
          {zones.map(z => (
            <div key={z.zone_id} className="calibration-card" style={{ 
              marginBottom: '16px', 
              padding: '14px', 
              background: '#1f2937',
              borderRadius: '10px',
              border: '1px solid #374151'
            }}>
              <div style={{ fontSize: '0.9rem', fontWeight: '600', marginBottom: '6px', color: '#e5e7eb' }}>{z.name}</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div style={{ fontSize: '0.7rem', color: '#9ca3af' }}>
                  <span style={{ color: '#6366f1' }}>LAT:</span> {z.lat?.toFixed(6)}
                </div>
                <div style={{ fontSize: '0.7rem', color: '#9ca3af' }}>
                  <span style={{ color: '#6366f1' }}>LNG:</span> {z.lng?.toFixed(6)}
                </div>
                <div style={{ fontSize: '0.7rem', color: '#9ca3af' }}>
                  <span style={{ color: '#a855f7' }}>H-X:</span> {z.x_hint?.toFixed(3)}
                </div>
                <div style={{ fontSize: '0.7rem', color: '#9ca3af' }}>
                  <span style={{ color: '#a855f7' }}>H-Y:</span> {z.y_hint?.toFixed(3)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </aside>

      <div className="calibrator-visual-grid" style={{ 
        display: 'grid', 
        gridTemplateColumns: '1fr 1fr', 
        gap: '24px' 
      }}>
        <div className="card" style={{ height: '100%', overflow: 'hidden', border: '1px solid #1e2733' }}>
          <MapSection 
            zones={zones} 
            calibrationMode={true} 
            onMarkerDrag={handleMapUpdate} 
          />
        </div>
        <div className="card" style={{ height: '100%', overflow: 'hidden', border: '1px solid #1e2733' }}>
          <GraphSection 
            calibrationMode={true} 
            onNodeDrag={handleGraphUpdate} 
          />
        </div>
      </div>
    </div>
  );
};
