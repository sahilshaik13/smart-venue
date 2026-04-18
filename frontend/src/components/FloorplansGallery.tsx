import React from 'react';

const FLOORS = [
  { id: 'hall1', src: '/assets/maps/HITEX_Hall_01_Layout_page-0001.jpg', title: 'Hall 1 Blueprint' },
  { id: 'hall2', src: '/assets/maps/HITEX_Hall_02_Layout_page-0001.jpg', title: 'Hall 2 Blueprint' },
  { id: 'hall3', src: '/assets/maps/HITEX_Hall_03_Layout_page-0001.jpg', title: 'Hall 3 Blueprint' },
  { id: 'hall4', src: '/assets/maps/HITEX_Hall_04_Layout_page-0001.jpg', title: 'Hall 4 Blueprint' },
];

export const FloorplansGallery: React.FC = () => {
  return (
    <section className="card" style={{ gridColumn: '1 / -1', marginTop: '24px', background: 'var(--surface)' }}>
      <div className="card-header" style={{ paddingBottom: '16px', borderBottom: '1px solid var(--border)' }}>
        <h2 className="card-title" style={{ fontSize: '1.2rem', color: 'var(--text)' }}>
          🏛️ Venue Blueprints Gallery
          <span style={{ fontSize: '0.75rem', fontWeight: 400, marginLeft: '12px', color: 'var(--text-muted)' }}>
            High-Resolution Exhibition Schematics
          </span>
        </h2>
      </div>
      <div 
        style={{ 
          display: 'flex', 
          overflowX: 'auto', 
          gap: '24px', 
          padding: '24px',
          scrollSnapType: 'x mandatory',
          scrollbarWidth: 'thin',
          scrollbarColor: 'var(--accent) var(--surface-2)'
        }}
      >
        {FLOORS.map((floor) => (
          <div 
            key={floor.id} 
            style={{ 
              minWidth: '300px', 
              maxWidth: '400px',
              flex: '0 0 auto', 
              scrollSnapAlign: 'start',
              borderRadius: '12px',
              overflow: 'hidden',
              background: 'var(--surface-2)',
              border: '1px solid var(--border)',
              boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
              cursor: 'zoom-in',
              transition: 'transform 0.2s ease, border-color 0.2s'
            }}
            onClick={() => window.open(floor.src, '_blank')}
            onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--accent)'}
            onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
          >
            <div style={{ padding: '12px 16px', background: 'rgba(0,0,0,0.4)', borderBottom: '1px solid var(--border)', fontSize: '0.9rem', fontWeight: 600 }}>
              {floor.title}
            </div>
            <img 
              src={floor.src} 
              alt={floor.title} 
              style={{ width: '100%', height: '220px', objectFit: 'cover', display: 'block', transition: 'transform 0.3s' }}
            />
          </div>
        ))}
      </div>
    </section>
  );
};
