export type ZoneStatus = 'low' | 'medium' | 'high' | 'critical';

export interface Zone {
  zone_id: string;
  name: string;
  type: 'gate' | 'concession' | 'restroom' | 'seating';
  capacity: number;
  current_count: number;
  crowd_level: number;
  status: ZoneStatus;
  predicted_wait_time?: number;
  lat?: number;
  lng?: number;
  x_hint?: number;
  y_hint?: number;
}

export interface Particle {
  id: string;
  x: number;
  y: number;
  type: string;
}

export interface VenueSnapshot {
  snapshot_time: string;
  match_minute: number;
  match_phase: string;
  zones: Zone[];
  particles?: Particle[];
}

export interface WaitTimePrediction {
  zone_id: string;
  predicted_wait_minutes: number;
  confidence: number;
  trend: 'rising' | 'stable' | 'falling';
  recommendation: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  crowd_level: number;
  status: ZoneStatus;
  capacity: number;
  current_count: number;
  predicted_wait_time?: number;
  x_hint: number;
  y_hint: number;
  lat?: number;
  lng?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight: number;
  is_congested: boolean;
  distance_m: number;
}

export interface VenueGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}
