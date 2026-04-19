import { useState, useCallback } from 'react';
import { 
  APIProvider, 
  Map, 
  AdvancedMarker, 
  InfoWindow,
  useMap
} from '@vis.gl/react-google-maps';
import type { Zone } from '../types';

interface MapSectionProps {
  zones: Zone[];
  particles?: Particle[];
}

const getStatusColor = (status: string) => {
  switch(status) {
    case 'low': return '#22c55e';
    case 'medium': return '#fbbf24';
    case 'high': return '#f97316';
    case 'critical': return '#ef4444';
    default: return '#6b7a99';
  }
};

const MapHandler = ({ zones }: { zones: Zone[] }) => {
  const map = useMap();
  React.useEffect(() => {
    const criticalZone = zones.find(z => z.status === 'critical');
    if (criticalZone && criticalZone.lat && criticalZone.lng && map) {
      map.panTo({ lat: criticalZone.lat, lng: criticalZone.lng });
    }
  }, [zones, map]);
  return null;
};

const ParticleLayer = ({ particles }: { particles?: Particle[] }) => {
  if (!particles || particles.length === 0) return null;

  return (
    <>
      {particles.map(p => (
        <AdvancedMarker
          key={p.id}
          position={{ 
            lat: p.y, 
            lng: p.x 
          }}
          collisionBehavior="OPTIONAL_AND_HIDES_LOWER_PRIORITY"
        >
          <div style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: p.type === 'Biker' ? '#38bdf8' : '#fff',
            boxShadow: '0 0 8px rgba(255,255,255,0.8)',
            border: '1px solid rgba(0,0,0,0.3)',
            opacity: 0.8,
            transition: 'all 0.5s linear'
          }} />
        </AdvancedMarker>
      ))}
    </>
  );
};

export const MapSection: React.FC<MapSectionProps> = ({ zones, particles }) => {
  const [selectedZone, setSelectedZone] = useState<Zone | null>(null);
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';

  const center = { lat: 17.4720, lng: 78.3740 }; // HITEX Core

  return (
    <section id="map-section" className="card map-section">
      <div className="card-header">
         <h2 className="card-title">Live HITEX Spatial Intelligence</h2>
         <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <span style={{ fontSize: '0.75rem', color: '#fff', opacity: 0.8 }}>● Historical Trajectory</span>
            <span style={{ fontSize: '0.75rem', color: '#22c55e' }}>● Low</span>
            <span style={{ fontSize: '0.75rem', color: '#ef4444' }}>● Crit</span>
         </div>
      </div>
      
      <div style={{ flex: 1, width: '100%', borderRadius: '12px', overflow: 'hidden', position: 'relative' }}>
        <APIProvider apiKey={apiKey}>
          <Map
            defaultCenter={center}
            defaultZoom={17}
            mapId="bf51a910020fa25a"
            disableDefaultUI={true}
            gestureHandling={'greedy'}
            tilt={45}
            heading={0}
          >
            <MapHandler zones={zones} />
            <ParticleLayer particles={particles} />
            
            {zones.map(z => {
              if (!z.lat || !z.lng) return null;
// ... rest of marker logic ...
              const color = getStatusColor(z.status);
              
              return (
                <AdvancedMarker
                  key={z.zone_id}
                  position={{ lat: z.lat, lng: z.lng }}
                  draggable={false}
                  onClick={() => setSelectedZone(z)}
                >
                  <div style={{
                    position: 'relative',
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    background: color,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: `0 0 20px ${color}`,
                    border: '3px solid white',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease-out',
                    transform: selectedZone?.zone_id === z.zone_id ? 'scale(1.2)' : 'scale(1)',
                    pointerEvents: 'auto'
                  }}>
                    {z.status === 'critical' && (
                      <div style={{
                        position: 'absolute',
                        width: '100%',
                        height: '100%',
                        borderRadius: '50%',
                        border: `2px solid ${color}`,
                        animation: 'ping 1.5s infinite',
                        pointerEvents: 'none'
                      }} />
                    )}
                    
                    {/* ML Prediction Badge */}
                    {(z.predicted_wait_time ?? 0) > 0.5 && (
                      <div style={{
                        position: 'absolute',
                        top: '-20px',
                        background: 'rgba(0,0,0,0.8)',
                        color: 'white',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontSize: '10px',
                        fontWeight: 'bold',
                        whiteSpace: 'nowrap',
                        border: '1px solid rgba(255,255,255,0.2)',
                        boxShadow: '0 2px 4px rgba(0,0,0,0.5)',
                        zIndex: 10
                      }}>
                        {Math.round(z.predicted_wait_time!)}m wait
                      </div>
                    )}
                  </div>
                </AdvancedMarker>
              );
            })}

            {selectedZone && (
              <InfoWindow
                position={{ lat: selectedZone.lat!, lng: selectedZone.lng! }}
                onCloseClick={() => setSelectedZone(null)}
              >
                <div style={{ color: '#000', padding: '8px' }}>
                  <h3 style={{ margin: '0 0 4px 0', fontSize: '1rem' }}>{selectedZone.name}</h3>
                  <p style={{ margin: '0', fontSize: '0.9rem' }}>
                    <strong>Crowd:</strong> {selectedZone.current_count} / {selectedZone.capacity}<br/>
                    <strong>Level:</strong> {(selectedZone.crowd_level * 100).toFixed(1)}%
                  </p>
                </div>
              </InfoWindow>
            )}
          </Map>
        </APIProvider>
      </div>
    </section>
  );
};
