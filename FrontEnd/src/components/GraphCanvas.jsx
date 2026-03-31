import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import { generateColorsForClusters, getDefaultColor } from '../data/photos';
import { useForceSimulation } from '../hooks/useForceSimulation';
import FilterBar from './FilterBar';
import Legend from './Legend';
import Tooltip from './Tooltip';
import StatsPanel from './StatsPanel';
import ExportTray from './ExportTray';
import { getGraph, getClusters, getImageUrl } from '../api';

export default function GraphCanvas({ token, refreshTrigger }) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const trayRef = useRef(null);

  const [filter, setFilter] = useState('all');
  const [hovered, setHovered] = useState(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [dims, setDims] = useState({ w: 800, h: 600 });

  // Data State
  const [photos, setPhotos] = useState([]);
  const [edges, setEdges] = useState([]);
  const [clusterData, setClusterData] = useState({});
  const [loading, setLoading] = useState(false);

  // Image preview state
  const imageCache = useRef(new Map()); // imageId -> presigned URL
  const [imageUrl, setImageUrl] = useState(null);

  // Tray state
  const [trayItems, setTrayItems] = useState([]);
  const [isDragOver, setIsDragOver] = useState(false);

  // Drag state
  const [dragging, setDragging] = useState(null); // { photo, startX, startY }
  const [dragPos, setDragPos] = useState({ x: 0, y: 0 });

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

        const mappedNodes = (graphRes.nodes || []).map((n, i) => ({
          ...n,
          id: n.id,
          label: n.id.split('/').pop(),
          radius: 5 + Math.random() * 5,
        }));

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

  // Fetch presigned URL when hovered node changes
  useEffect(() => {
    if (hovered === null || !token) {
      setImageUrl(null);
      return;
    }
    const photo = photos[hovered];
    if (!photo) return;

    const imageId = photo.id;
    if (imageCache.current.has(imageId)) {
      setImageUrl(imageCache.current.get(imageId));
      return;
    }

    setImageUrl(null);
    getImageUrl(token, imageId)
      .then(data => {
        imageCache.current.set(imageId, data.presigned_url);
        // Only apply if this node is still hovered
        setHovered(prev => {
          if (prev !== null && photos[prev]?.id === imageId) {
            setImageUrl(data.presigned_url);
          }
          return prev;
        });
      })
      .catch(console.error);
  }, [hovered, photos, token]);

  // Canvas render loop
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

        ctx.strokeStyle = isHighlighted
          ? `rgba(255,255,255,${Math.min(0.45, alpha * 6)})`
          : `rgba(255,255,255,${alpha})`;
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
        const inTray = trayItems.some(t => t.id === photos[i]?.id);

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

        // Ring indicator for nodes in tray
        if (inTray) {
          ctx.globalAlpha = 0.9;
          ctx.strokeStyle = '#85B7EB';
          ctx.lineWidth = 2;
          ctx.shadowColor = '#85B7EB';
          ctx.shadowBlur = 8;
          ctx.beginPath();
          ctx.arc(n.x, n.y, (n.r || 5) + 4, 0, Math.PI * 2);
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
  }, [dims, edges, filter, hovered, trayItems, sim.tick, photos]);

  // Hit-test helper
  const getNodeAtPos = useCallback((mx, my) => {
    const nodes = sim.nodesRef.current || [];
    for (let i = nodes.length - 1; i >= 0; i--) {
      const dx = mx - nodes[i].x;
      const dy = my - nodes[i].y;
      const r = nodes[i].r || 5;
      if (dx * dx + dy * dy < (r + 5) * (r + 5)) return i;
    }
    return null;
  }, [sim.nodesRef]);

  const handleMouseMove = useCallback((e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    setMousePos({ x: mx, y: my });

    if (dragging) {
      setDragPos({ x: e.clientX, y: e.clientY });

      // Check if over tray
      const tray = trayRef.current;
      if (tray) {
        const trayRect = tray.getBoundingClientRect();
        const over = e.clientX >= trayRect.left && e.clientX <= trayRect.right &&
          e.clientY >= trayRect.top && e.clientY <= trayRect.bottom;
        setIsDragOver(over);
      }
      return;
    }

    setHovered(getNodeAtPos(mx, my));
  }, [dragging, getNodeAtPos]);

  const handleMouseLeave = useCallback(() => {
    if (!dragging) setHovered(null);
  }, [dragging]);

  const handleMouseDown = useCallback((e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const idx = getNodeAtPos(mx, my);
    if (idx === null) return;

    const photo = photos[idx];
    if (!photo) return;

    e.preventDefault();
    setDragging({
      ...photo,
      imageUrl: imageCache.current.get(photo.id) || null,
    });
    setDragPos({ x: e.clientX, y: e.clientY });
  }, [photos, getNodeAtPos]);

  const handleMouseUp = useCallback((e) => {
    if (!dragging) return;

    const tray = trayRef.current;
    if (tray) {
      const trayRect = tray.getBoundingClientRect();
      const droppedOnTray = e.clientX >= trayRect.left && e.clientX <= trayRect.right &&
        e.clientY >= trayRect.top && e.clientY <= trayRect.bottom;

      if (droppedOnTray) {
        setTrayItems(prev => {
          if (prev.find(p => p.id === dragging.id)) return prev;
          return [...prev, dragging];
        });
      }
    }

    setDragging(null);
    setIsDragOver(false);
  }, [dragging]);

  // When image loads into cache, update tray items that are missing their imageUrl
  const handleRemoveFromTray = useCallback((id) => {
    setTrayItems(prev => prev.filter(p => p.id !== id));
  }, []);

  const tooltipData = hovered !== null ? photos[hovered] : null;
  const tooltipInTray = tooltipData ? trayItems.some(p => p.id === tooltipData.id) : false;

  // Tray width offset so graph doesn't render behind tray
  const TRAY_WIDTH = 220;

  return (
    <div
      ref={containerRef}
      style={{ width: '100%', height: '100vh', position: 'relative', overflow: 'hidden', background: '#050505' }}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
    >
      {loading && (
        <div style={{ position: 'absolute', top: 20, left: 20, color: 'white', zIndex: 10 }}>
          Loading Live Data...
        </div>
      )}
      {!token && (
        <div style={{
          position: 'absolute', top: '50%', left: '50%',
          transform: 'translate(-50%, -50%)', color: '#ccc', zIndex: 10, fontSize: '1.2rem'
        }}>
          Please enter your Cognito Token using the Data Panel to load photos.
        </div>
      )}

      <FilterBar active={filter} onChange={handleFilterChange} />
      <StatsPanel photoCount={photos.length} edgeCount={edges.length} filter={filter} />

      <canvas
        ref={canvasRef}
        onMouseLeave={handleMouseLeave}
        onMouseDown={handleMouseDown}
        style={{
          cursor: dragging ? 'grabbing' : hovered !== null ? 'grab' : 'default',
          display: 'block',
        }}
      />

      <Tooltip
        data={tooltipData}
        x={mousePos.x}
        y={mousePos.y}
        imageUrl={imageUrl}
        inTray={tooltipInTray}
      />

      <Legend filter={filter} clusterData={clusterData} />

      <ExportTray
        ref={trayRef}
        items={trayItems}
        onRemove={handleRemoveFromTray}
        onClear={() => setTrayItems([])}
        isDragOver={isDragOver}
      />

      {/* Drag ghost */}
      {dragging && (
        <div style={{
          position: 'fixed',
          left: dragPos.x - 24,
          top: dragPos.y - 24,
          width: 48,
          height: 48,
          borderRadius: '50%',
          background: '#85B7EB',
          border: '2px solid #fff',
          pointerEvents: 'none',
          zIndex: 100,
          overflow: 'hidden',
          boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
          opacity: 0.9,
        }}>
          {dragging.imageUrl && (
            <img
              src={dragging.imageUrl}
              alt=""
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          )}
        </div>
      )}
    </div>
  );
}
