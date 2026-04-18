import React from 'react';
import type { VenueSnapshot } from '../types';

interface HeatmapSectionProps {
  snapshot: VenueSnapshot | null;
  onZoneClick: (zoneName: string, status: string) => void;
}

export const HeatmapSection: React.FC<HeatmapSectionProps> = ({ snapshot, onZoneClick }) => {
  return (
    <section id="heatmap-section" className="card" aria-labelledby="heatmap-title">
      <div className="card-header">
        <h2 className="card-title" id="heatmap-title">Zone Crowd Density</h2>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <span id="status-bar" aria-live="polite" aria-atomic="true">
            {snapshot ? `Updated ${new Date().toLocaleTimeString()}` : 'Loading...'}
          </span>
          <button id="refresh-toggle" aria-pressed="true" title="Toggle auto-refresh">⟳ Auto</button>
        </div>
      </div>
      <div className="card-body">
        <div id="zone-grid" className="zone-grid" role="grid" aria-label="Venue zone crowd density grid">
          {!snapshot ? (
            <>
              <div className="skeleton"></div><div className="skeleton"></div>
              <div className="skeleton"></div><div className="skeleton"></div>
            </>
          ) : (
            snapshot.zones.map(zone => {
              const pct = Math.round(zone.crowd_level * 100);
              return (
                <div 
                  key={zone.zone_id}
                  className="zone-cell" 
                  data-status={zone.status}
                  role="gridcell"
                  tabIndex={0}
                  onClick={() => onZoneClick(zone.name, zone.status)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' || e.key === ' ') onZoneClick(zone.name, zone.status);
                  }}
                >
                  <div className="zone-name">{zone.name}</div>
                  <div className="zone-percent">{pct}%</div>
                  <div className="zone-badge">{zone.status}</div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </section>
  );
};
