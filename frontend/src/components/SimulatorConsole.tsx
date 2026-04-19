import { useState } from 'react';
import { getApiUrl } from '../utils/config';

interface SimulatorConsoleProps {
  sessionToken: string;
  onRefresh: () => void;
}

export const SimulatorConsole: React.FC<SimulatorConsoleProps> = ({ sessionToken, onRefresh }) => {
  const [theme, setTheme] = useState('hackathon');
  const [situation, setSituation] = useState('morning_entry');
  const [severity, setSeverity] = useState('medium');
  const [isUpdating, setIsUpdating] = useState(false);

  const themes = [
    { id: 'hackathon', label: 'Theme: Global Hackathon' },
    { id: 'marathon', label: 'Theme: City Marathon' },
    { id: 'expo', label: 'Theme: Technology Expo' },
    { id: 'awards', label: 'Theme: Awards Ceremony' },
    { id: 'auto_expo', label: 'Theme: Auto Expo' },
    { id: 'music_festival', label: 'Theme: Music Festival' },
    { id: 'startup_summit', label: 'Theme: StartUp Summit' },
  ];

  const situations = [
    { id: 'morning_entry', label: 'Sit: Morning Entry' },
    { id: 'program_init', label: 'Sit: Program Init' },
    { id: 'busy_peak', label: 'Sit: Busy Peak' },
    { id: 'lunch_break', label: 'Sit: Lunch Break' },
    { id: 'vip_entry', label: 'Sit: VIP Arrival' },
    { id: 'closing', label: 'Sit: Closing / Exit' },
  ];

  const severities = [
    { id: 'low', label: 'Dens: Low' },
    { id: 'medium', label: 'Dens: Med' },
    { id: 'high', label: 'Dens: High' },
  ];

  const handleApply = async () => {
    setIsUpdating(true);
    try {
      const res = await fetch(`${getApiUrl()}/api/simulate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify({ 
          theme, 
          situation, 
          severity 
        })
      });
      if (res.ok) {
        onRefresh();
      }
    } catch (e) {
      console.error('Failed to update simulation', e);
    } finally {
      setIsUpdating(false);
    }
  };

  const selectStyle: React.CSSProperties = {
    background: 'transparent',
    border: 'none',
    color: 'var(--text)',
    fontSize: '0.72rem',
    fontWeight: 500,
    cursor: 'pointer',
    outline: 'none',
    padding: '2px 4px',
    borderRadius: '4px',
    fontFamily: 'var(--font-body)',
  };

  const dividerStyle: React.CSSProperties = {
    width: '1px',
    height: '14px',
    background: 'var(--border)',
    margin: '0 4px'
  };

  return (
    <div className="sim-console" style={{ 
      display: 'flex', 
      alignItems: 'center', 
      gap: '4px', 
      background: 'rgba(22, 27, 39, 0.8)', 
      backdropFilter: 'blur(10px)',
      padding: '4px 8px', 
      borderRadius: '8px', 
      border: '1px solid var(--border)',
      boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '2px', marginRight: '4px' }}>
        <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: isUpdating ? 'var(--accent)' : 'var(--low)', boxShadow: isUpdating ? '0 0 8px var(--accent)' : 'none' }}></div>
        <span style={{ fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.05em' }}>SIM</span>
      </div>
      
      <select value={theme} onChange={(e) => setTheme(e.target.value)} disabled={isUpdating} style={selectStyle}>
        {themes.map(t => <option key={t.id} value={t.id} style={{background: 'var(--surface-2)'}}>{t.label}</option>)}
      </select>

      <div style={dividerStyle}></div>

      <select value={situation} onChange={(e) => setSituation(e.target.value)} disabled={isUpdating} style={selectStyle}>
        {situations.map(s => <option key={s.id} value={s.id} style={{background: 'var(--surface-2)'}}>{s.label}</option>)}
      </select>

      <div style={dividerStyle}></div>

      <select value={severity} onChange={(e) => setSeverity(e.target.value)} disabled={isUpdating} style={selectStyle}>
        {severities.map(s => <option key={s.id} value={s.id} style={{background: 'var(--surface-2)'}}>{s.label}</option>)}
      </select>

      <button 
        onClick={handleApply}
        disabled={isUpdating}
        style={{
          marginLeft: '8px',
          background: 'var(--accent)',
          border: 'none',
          color: 'white',
          fontSize: '0.68rem',
          fontWeight: 700,
          padding: '5px 10px',
          borderRadius: '4px',
          cursor: 'pointer',
          transition: 'all 0.2s',
          opacity: isUpdating ? 0.7 : 1,
          display: 'flex',
          alignItems: 'center',
          gap: '4px'
        }}
      >
        {isUpdating ? 'SYNCING...' : 'IMPLEMENT'}
      </button>
    </div>
  );
};
