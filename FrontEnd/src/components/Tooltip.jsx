import React from 'react';

export default function Tooltip({ data, x, y, imageUrl, inTray }) {
  if (!data) return null;

  return (
    <div
      style={{
        ...styles.tooltip,
        left: x + 16,
        top: y - 12,
      }}
    >
      {imageUrl ? (
        <img src={imageUrl} alt={data.label} style={styles.preview} />
      ) : (
        <div style={styles.previewPlaceholder}>
          <span style={styles.placeholderText}>Loading...</span>
        </div>
      )}
      <div style={styles.label}>{data.label}</div>
      <div style={styles.meta}>
        {data.date_taken && (
          <span style={styles.tag}>
            <span style={{ ...styles.tagDot, background: '#85B7EB' }} />
            {data.date_taken}
          </span>
        )}
        {(data.gps_lat != null && data.gps_lon != null) && (
          <span style={styles.tag}>
            <span style={{ ...styles.tagDot, background: '#ED93B1' }} />
            {data.gps_lat.toFixed(4)}, {data.gps_lon.toFixed(4)}
          </span>
        )}
      </div>
      <div style={styles.hint}>
        {inTray ? '✓ In tray — drag to remove' : 'Drag to tray to export'}
      </div>
    </div>
  );
}

const styles = {
  tooltip: {
    position: 'absolute',
    background: 'rgba(12, 12, 12, 0.95)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 'var(--radius-md)',
    padding: '10px',
    pointerEvents: 'none',
    zIndex: 30,
    backdropFilter: 'blur(16px)',
    WebkitBackdropFilter: 'blur(16px)',
    width: '200px',
  },
  preview: {
    width: '100%',
    height: '130px',
    objectFit: 'cover',
    borderRadius: '4px',
    marginBottom: '8px',
    display: 'block',
  },
  previewPlaceholder: {
    width: '100%',
    height: '130px',
    background: 'rgba(255,255,255,0.05)',
    borderRadius: '4px',
    marginBottom: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  placeholderText: {
    fontSize: '11px',
    color: 'rgba(255,255,255,0.3)',
  },
  label: {
    fontSize: '12px',
    fontWeight: 500,
    color: '#fff',
    marginBottom: '5px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  meta: {
    display: 'flex',
    flexDirection: 'column',
    gap: '3px',
    marginBottom: '6px',
  },
  tag: {
    display: 'flex',
    alignItems: 'center',
    gap: '5px',
    fontSize: '10px',
    color: 'rgba(255,255,255,0.45)',
  },
  tagDot: {
    width: '5px',
    height: '5px',
    borderRadius: '50%',
    flexShrink: 0,
  },
  hint: {
    fontSize: '10px',
    color: 'rgba(255,255,255,0.25)',
    fontStyle: 'italic',
  },
};
