import React, { useEffect, useState } from 'react';
import type { Zone, WaitTimePrediction } from '../types';
import { getApiUrl } from '../utils/config';

interface WaitTimesSectionProps {
  zones: Zone[];
}

export const WaitTimesSection: React.FC<WaitTimesSectionProps> = ({ zones }) => {
  const [predictions, setPredictions] = useState<Record<string, WaitTimePrediction>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!zones.length) return;
    
    let isSubscribed = true;
    
    const fetchPromises = async () => {
      setLoading(true);
      try {
        const topZones = zones.slice(0, 8);
        const results = await Promise.allSettled(
          topZones.map(z => fetch(`${getApiUrl()}/api/predict/${z.zone_id}`).then(r => r.json()))
        );
        
        if (isSubscribed) {
          const newPreds: Record<string, WaitTimePrediction> = {};
          results.forEach((res) => {
            if (res.status === 'fulfilled') {
              newPreds[res.value.zone_id] = res.value;
            }
          });
          setPredictions(newPreds);
        }
      } catch (e) {
        console.error("Failed to fetch wait times", e);
      } finally {
        if (isSubscribed) setLoading(false);
      }
    };
    
    fetchPromises();
    return () => { isSubscribed = false; };
  }, [zones]);

  const getTrendIcon = (trend: string) => {
    switch(trend) {
      case 'rising': return '↑';
      case 'falling': return '↓';
      default: return '→';
    }
  };

  const getStatusColor = (status: string) => {
      if (status === 'low') return 'var(--low)';
      if (status === 'medium') return 'var(--medium)';
      if (status === 'high') return 'var(--high)';
      return 'var(--critical)';
  };

  return (
    <section id="waittimes-section" className="card" aria-labelledby="wait-title">
      <div className="card-header">
        <h2 className="card-title" id="wait-title">Predicted Wait Times</h2>
      </div>
      <div className="card-body">
        <div id="wait-cards" className="wait-cards" aria-live="polite" aria-label="Wait time predictions per zone">
          {(!zones.length || loading) ? (
            <>
              <div className="skeleton"></div><div className="skeleton"></div>
              <div className="skeleton"></div><div className="skeleton"></div>
            </>
          ) : (
            zones.slice(0, 8).map(zone => {
              const p = predictions[zone.zone_id];
              if (!p) return null;
              
              return (
                <div key={zone.zone_id} className="wait-card">
                  <div className="wait-left">
                    <div className="wait-zone">{zone.name}</div>
                    <div className="wait-type">{zone.type}</div>
                  </div>
                  <div className="wait-right">
                    <div className="wait-minutes" style={{ color: getStatusColor(zone.status) }}>{p.predicted_wait_minutes}m</div>
                    <div className={`wait-trend trend-${p.trend}`} aria-label={`Trend: ${p.trend}`}>
                      {getTrendIcon(p.trend)}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </section>
  );
};
