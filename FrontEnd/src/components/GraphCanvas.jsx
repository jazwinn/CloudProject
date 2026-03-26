import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import { generateColorsForClusters, getDefaultColor } from '../data/photos';
import { useForceSimulation } from '../hooks/useForceSimulation';
import FilterBar from './FilterBar';
import Legend from './Legend';
import Tooltip from './Tooltip';
import StatsPanel from './StatsPanel';
import { getGraph, getClusters } from '../api';

export default function GraphCanvas({ token, refreshTrigger }) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  
  const [filter, setFilter] = useState('all'); 
  const [hovered, setHovered] = useState(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [dims, setDims] = useState({ w: 800, h: 600 });
  
  // Data State
  const [photos, setPhotos] = useState([]);
  const [edges, setEdges] = useState([]);
  const [clusterData, setClusterData] = useState({});
  const [loading, setLoading] = useState(false);

  const frameRef = useRef(null);
  const colorsRef = useRef([]);
  const sim = useForceSimulation();

  useEffect(() => {
    if (!token) return;

    let mounted = true;
    const fetchData = async () => {
      setLoading(true);
      try {
        const graphRes = await getGraph(token);
        const clusterResCombined = await getClusters(token, 'combined');
        const clusterResTime = await getClusters(token, 'time');
        const clusterResLoc = await getClusters(token, 'location');

        if (!mounted) return;

        // Map nodes
        const mappedNodes = (graphRes.nodes || []).map((n, i) => ({
          ...n,
          id: n.id,
          label: n.id.split('/').pop(),
          radius: 5 + Math.random() * 5, 
        }));

        // Map edges 
        const idToIndex = {};
        mappedNodes.forEach((n, i) => { idToIndex[n.id] = i; });

        const mappedEdges = (graphRes.edges || []).map(e => ({
          source: idToIndex[e.source],
          target: idToIndex[e.target],
          strength: 1
        })).filter(e => e.source !== undefined && e.target !== undefined);

        setPhotos(mappedNodes);
        setEdges(mappedEdges);

        const buildConfig = (label, res) => {
          const clusters = generateColorsForClusters(
            (res.clusters || []).map(c => ({
              id: c.cluster_id,
              name: c.label,
              photo_ids: c.photo_ids
            }))
          );
          return { label, clusters };
        };

        setClusterData({
          combined: buildConfig('Combined', clusterResCombined),
          time: buildConfig('Time period', clusterResTime),
          location: buildConfig('Location', clusterResLoc),
        });

      } catch (err) {
        console.error("Failed to fetch graph data", err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    return () => { mounted = false; };
  }, [token, refreshTrigger]);

  const assignColors = useCallback((currentFilter) => {
      colorsRef.current = photos.map((p, i) => {
        if (currentFilter === 'all' || !clusterData[currentFilter]) {
          return getDefaultColor(i);
        }
        
        const config = clusterData[currentFilter];
        const cluster = config.clusters.find(c => c.photo_ids.includes(p.id));
        return cluster ? cluster.color : '#444444'; 
      });
  }, [photos, clusterData]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || photos.length === 0) return;
    const rect = el.getBoundingClientRect();
    const w = rect.width;
    const h = rect.height;
    setDims({ w, h });
    sim.init(photos, edges, w, h);
    assignColors(filter);
  }, [photos, edges, sim.init, assignColors, filter]);

  const handleFilterChange = useCallback((f) => {
      setFilter(f);
      assignColors(f);
  }, [assignColors]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || photos.length === 0) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;

    const render = () => {
      const { w, h } = dims;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = w + 'px';
      canvas.style.height = h + 'px';
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      const nodes = sim.tick(w, h);
      const colors = colorsRef.current;

      ctx.fillStyle = '#050505';
      ctx.fillRect(0, 0, w, h);

      for (const e of edges) {
        const a = nodes[e.source];
        const b = nodes[e.target];
        if (!a || !b) continue;
        const dist = Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2);
        let alpha = Math.max(0, 0.07 - dist * 0.00018) * e.strength;
        const isHighlighted = hovered !== null && (e.source === hovered || e.target === hovered);
        
        ctx.strokeStyle = isHighlighted ? `rgba(255,255,255,${Math.min(0.45, alpha * 6)})` : `rgba(255,255,255,${alpha})`;
        ctx.lineWidth = isHighlighted ? 1 : 0.4;
        
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }

      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];
        const col = colors[i] || '#888';
        const isHov = hovered === i;
        if (isHov) {
          ctx.shadowColor = col;
          ctx.shadowBlur = 16;
        }
        ctx.globalAlpha = isHov ? 1 : 0.82;
        ctx.fillStyle = col;
        ctx.beginPath();
        ctx.arc(n.x, n.y, isHov ? (n.r || 5) + 2 : (n.r || 5), 0, Math.PI * 2);
        ctx.fill();
        if (isHov) {
          ctx.strokeStyle = '#fff';
          ctx.lineWidth = 1.5;
          ctx.stroke();
          ctx.shadowBlur = 0;
        }
        ctx.globalAlpha = 1;
      }

      frameRef.current = requestAnimationFrame(render);
    };

    frameRef.current = requestAnimationFrame(render);
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [dims, edges, filter, hovered, sim.tick, photos.length]);

  const handleMouseMove = useCallback((e) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      setMousePos({ x: mx, y: my });

      const nodes = sim.nodesRef.current || [];
      let found = null;
      for (let i = nodes.length - 1; i >= 0; i--) {
        const dx = mx - nodes[i].x;
        const dy = my - nodes[i].y;
        const r = nodes[i].r || 5;
        if (dx * dx + dy * dy < (r + 5) * (r + 5)) {
          found = i;
          break;
        }
      }
      setHovered(found);
  }, [sim.nodesRef]);

  const handleMouseLeave = useCallback(() => {
    setHovered(null);
  }, []);

  const tooltipData = hovered !== null ? photos[hovered] : null;

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100vh', position: 'relative', overflow: 'hidden', background: '#050505' }}>
      
      {loading && <div style={{ position: 'absolute', top: 20, left: 20, color: 'white', zIndex: 10 }}>Loading Live Data...</div>}
      {!token && <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: '#ccc', zIndex: 10, fontSize: '1.2rem' }}>Please enter your Cognito Token using the Data Panel to load photos.</div>}

      <FilterBar active={filter} onChange={handleFilterChange} />
      <StatsPanel photoCount={photos.length} edgeCount={edges.length} filter={filter} />
      <canvas ref={canvasRef} onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave} style={{ cursor: hovered !== null ? 'pointer' : 'default' }} />
      <Tooltip data={tooltipData} x={mousePos.x} y={mousePos.y} />
      <Legend filter={filter} clusterData={clusterData} />
    </div>
  );
}
