import React, { useState, useRef, useEffect } from 'react';
import * as d3 from 'd3';
import type { VenueGraph, GraphNode, GraphEdge } from '../types';
import { getApiUrl } from '../utils/config';

interface GraphSectionProps {
  onZoneClick: (zoneName: string, status: string) => void;
  sessionToken: string;
  refreshTrigger?: number;
}

export const GraphSection: React.FC<GraphSectionProps> = ({ 
  onZoneClick, 
  refreshTrigger,
  sessionToken
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  const lastTransform = useRef<d3.ZoomTransform | null>(null);
  const activeNodeId = useRef<string | null>(null);
  const graphDataRef = useRef<VenueGraph | null>(null);

  // Update tooltip live if active
  useEffect(() => {
    if (activeNodeId.current && graphDataRef.current && tooltipRef.current) {
      const node = graphDataRef.current.nodes.find(n => n.id === activeNodeId.current);
      if (node) {
        const statusToColor = (s: string) => ({ low: '#22c55e', medium: '#f59e0b', high: '#ef4444', critical: '#a855f7' }[s] || '#6b7a99');
        tooltipRef.current.innerHTML = `
          <strong>${node.label}</strong><br>
          Type: ${node.type}<br>
          Crowd: ${Math.round(node.crowd_level*100)}%<br>
          Status: <span style="color:${statusToColor(node.status)}">${node.status}</span><br>
          ${node.current_count} / ${node.capacity} people
        `;
      }
    }
  }, [refreshTrigger]);

  useEffect(() => {
    const fetchAndRenderGraph = async () => {
      try {
        const res = await fetch(`${getApiUrl()}/api/graph`, {
          headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        if (!res.ok) return;
        const graph: VenueGraph = await res.json();
        graphDataRef.current = graph;
        
        if (!containerRef.current || !svgRef.current || !tooltipRef.current) return;

        // Viewport scale
        const width = 1200;
        const height = 1000;

        const nodes = graph.nodes.map(n => ({
          ...n,
          x: n.x_hint * width,
          y: n.y_hint * height,
        }));
        const nodeById = Object.fromEntries(nodes.map(n => [n.id, n]));
        const edges = graph.edges.map(e => ({
          ...e,
          source: nodeById[e.source],
          target: nodeById[e.target],
        })).filter((e: any) => e.source && e.target);

        const svg = d3.select(svgRef.current)
          .attr("viewBox", `0 0 ${width} ${height}`)
          .attr("preserveAspectRatio", "xMidYMid meet");

        svg.selectAll('*').remove();
        const g = svg.append('g');
        
        const statusToColor = (s: string) => ({ low: '#22c55e', medium: '#f59e0b', high: '#ef4444', critical: '#a855f7' }[s] || '#6b7a99');

        const zoom = d3.zoom<SVGSVGElement, unknown>()
          .scaleExtent([0.1, 8])
          .on('zoom', (evt) => {
            g.attr('transform', evt.transform);
            lastTransform.current = evt.transform;
          });
          
        svg.call(zoom);

        // Apply persistent transform
        if (lastTransform.current) {
          svg.call(zoom.transform, lastTransform.current);
        } else {
          // Initial Auto-Fit: Calculate bounds
          const xExtent = d3.extent(nodes, d => d.x) as [number, number];
          const yExtent = d3.extent(nodes, d => d.y) as [number, number];
          const graphWidth = xExtent[1] - xExtent[0];
          const graphHeight = yExtent[1] - yExtent[0];
          const scale = 0.7 / Math.max(graphWidth / width, graphHeight / height);
          const t = d3.zoomIdentity
            .translate(width / 2, height / 2)
            .scale(scale)
            .translate(-(xExtent[0] + graphWidth / 2), -(yExtent[0] + graphHeight / 2));
          svg.call(zoom.transform, t);
        }

        const link = g.append('g').selectAll('line')
          .data(edges).enter().append('line')
          .attr('class', d => d.weight > 0.8 ? 'graph-link jammed' : d.weight > 0.45 ? 'graph-link slow' : 'graph-link flowing')
          .attr('stroke-width', d => 1.5 + d.weight * 6)
          .attr('x1', (d: any) => d.source.x).attr('y1', (d: any) => d.source.y)
          .attr('x2', (d: any) => d.target.x).attr('y2', (d: any) => d.target.y);

        const node = g.append('g').selectAll('g')
          .data(nodes).enter().append('g')
          .attr('class', 'graph-node')
          .attr('transform', d => `translate(${d.x},${d.y})`)
          .on('click', (evt, d: any) => onZoneClick(d.label, d.status));

        const radius = (d: any) => 10 + d.crowd_level * 16;
        
        node.append('circle')
          .attr('r', radius)
          .attr('fill', d => statusToColor(d.status) + '22')
          .attr('stroke', d => statusToColor(d.status))
          .on('mouseover', (evt, d: any) => {
            activeNodeId.current = d.id;
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
            activeNodeId.current = null;
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
  }, [onZoneClick, refreshTrigger, sessionToken]);

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
