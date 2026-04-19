import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import type { VenueGraph, GraphNode, GraphEdge } from '../types';
import { getApiUrl } from '../utils/config';

interface GraphSectionProps {
  onZoneClick: (zoneName: string, status: string) => void;
  refreshTrigger?: number;
}

export const GraphSection: React.FC<GraphSectionProps> = ({ 
  onZoneClick, 
  refreshTrigger 
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let simulation: any;

    const fetchAndRenderGraph = async () => {
      try {
        const res = await fetch(`${getApiUrl()}/api/graph`);
        if (!res.ok) return;
        const graph: VenueGraph = await res.json();
        
        if (!containerRef.current || !svgRef.current || !tooltipRef.current) return;

        const W = containerRef.current.clientWidth;
        const H = containerRef.current.clientHeight;

        const statusToColor = (status: string) => {
          return { low: '#22c55e', medium: '#f59e0b', high: '#ef4444', critical: '#a855f7' }[status] || '#6b7a99';
        };

        const nodes = graph.nodes.map(n => ({
          ...n,
          x: n.x_hint * W,
          y: n.y_hint * H,
          fx: n.x_hint * W,
          fy: n.y_hint * H,
        }));
        const nodeById = Object.fromEntries(nodes.map(n => [n.id, n]));

        const edges = graph.edges.map(e => ({
          ...e,
          source: nodeById[e.source],
          target: nodeById[e.target],
        })).filter((e: any) => e.source && e.target);

        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();

        const g = svg.append('g');
        
        const zoom = d3.zoom<SVGSVGElement, unknown>()
          .scaleExtent([0.5, 3])
          .on('zoom', evt => g.attr('transform', evt.transform));
          
        svg.call(zoom);

        const link = g.append('g').selectAll('line')
          .data(edges).enter().append('line')
          .attr('class', d => {
            if (d.weight > 0.8) return 'graph-link jammed';
            if (d.weight > 0.45) return 'graph-link slow';
            return 'graph-link flowing';
          })
          .attr('stroke-width', d => 1.5 + d.weight * 6)
          .attr('x1', (d: any) => d.source.x).attr('y1', (d: any) => d.source.y)
          .attr('x2', (d: any) => d.target.x).attr('y2', (d: any) => d.target.y);

        const node = g.append('g').selectAll('g')
          .data(nodes).enter().append('g')
          .attr('class', 'graph-node')
          .attr('transform', d => `translate(${d.x},${d.y})`)
          .style('cursor', 'pointer')
          .on('click', (evt, d: any) => onZoneClick(d.label, d.status));


        const radius = (d: any) => 10 + d.crowd_level * 16;
        
        node.append('circle')
          .attr('r', radius)
          .attr('fill', d => statusToColor(d.status) + '22')
          .attr('stroke', d => statusToColor(d.status))
          .on('mouseover', (evt, d: any) => {
            const tt = tooltipRef.current;
            if (tt) {
              tt.style.opacity = '1';
              tt.style.left = (evt.offsetX + 12) + 'px';
              tt.style.top  = (evt.offsetY - 10) + 'px';
              tt.innerHTML = `
                <strong>${d.label}</strong><br>
                Type: ${d.type}<br>
                Crowd: ${Math.round(d.crowd_level*100)}%<br>
                Status: <span style="color:${statusToColor(d.status)}">${d.status}</span><br>
                ${d.current_count} / ${d.capacity} people
              `;
            }
          })
          .on('mouseleave', () => {
            if (tooltipRef.current) tooltipRef.current.style.opacity = '0';
          });

        node.append('text')
          .attr('dy', d => radius(d) + 11)
          .text(d => d.label.split('—')[0].trim().substring(0, 12));

      } catch (e) {
        console.warn('Graph layout error', e);
      }
    };

    fetchAndRenderGraph();
  }, [onZoneClick, refreshTrigger]);

  return (
    <section id="graph-section" className="card" aria-labelledby="graph-title">
      <div className="card-header">
        <h2 className="card-title" id="graph-title">Venue Knowledge Graph <small style={{fontSize:'.7rem',color:'var(--text-muted)',fontFamily:'var(--font-body)',fontWeight:400}}>— inspired by GitNexus</small></h2>
        <span style={{fontSize:'.72rem',color:'var(--text-muted)'}}>Nodes = zones · Edges = walkways · Width = crowd flow</span>
      </div>
      <div id="graph-container" ref={containerRef} style={{ flex: 1, position: 'relative', overflow: 'hidden' }} role="img" aria-label="Interactive force-directed knowledge graph of venue zones and their connections">
        <svg id="graph-svg" ref={svgRef} style={{ width: '100%', height: '100%' }} aria-hidden="true"></svg>
        <div id="graph-tooltip" ref={tooltipRef} className="graph-tooltip" role="tooltip" aria-live="polite"></div>
      </div>
      <div className="graph-legend" aria-label="Graph legend">
        <div className="legend-item"><div className="legend-dot" style={{background:'var(--low)'}}></div>Low</div>
        <div className="legend-item"><div className="legend-dot" style={{background:'var(--medium)'}}></div>Medium</div>
        <div className="legend-item"><div className="legend-dot" style={{background:'var(--high)'}}></div>High</div>
        <div className="legend-item"><div className="legend-dot" style={{background:'var(--critical)'}}></div>Critical</div>
      </div>
    </section>
  );
}
