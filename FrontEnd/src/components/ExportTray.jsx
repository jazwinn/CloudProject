import React, { forwardRef } from 'react';

const ExportTray = forwardRef(function ExportTray({ items, onRemove, onClear, isDragOver }, ref) {
  const handleExport = () => {
    items.forEach((item) => {
      if (!item.imageUrl) return;
      const a = document.createElement('a');
      a.href = item.imageUrl;
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      a.click();
    });
  };

  return (
    <div ref={ref} style={styles.tray}>
      <div style={styles.header}>
        <span style={styles.title}>Export Tray</span>
        {items.length > 0 && (
          <button style={styles.clearBtn} onClick={onClear}>Clear</button>
        )}
      </div>

      <div style={{ ...styles.dropZone, ...(isDragOver ? styles.dropZoneActive : {}) }}>
        {items.length === 0 ? (
          <div style={styles.emptyHint}>
            <div style={styles.emptyIcon}>&#8659;</div>
            <span>Drag photos here</span>
          </div>
        ) : (
          <div style={styles.grid}>
            {items.map((item) => (
              <div key={item.id} style={styles.thumb} title={item.label}>
                {item.imageUrl ? (
                  <img src={item.imageUrl} alt={item.label} style={styles.thumbImg} />
                ) : (
                  <div style={styles.thumbPlaceholder} />
                )}
                <button
                  style={styles.removeBtn}
                  onClick={() => onRemove(item.id)}
                  title="Remove"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {items.length > 0 && (
        <button style={styles.exportBtn} onClick={handleExport}>
          Open {items.length} image{items.length !== 1 ? 's' : ''}
        </button>
      )}
    </div>
  );
});

export default ExportTray;

const styles = {
  tray: {
    position: 'absolute',
    right: 0,
    top: 0,
    bottom: 0,
    width: '220px',
    background: 'rgba(10,10,10,0.92)',
    borderLeft: '1px solid rgba(255,255,255,0.08)',
    backdropFilter: 'blur(20px)',
    WebkitBackdropFilter: 'blur(20px)',
    display: 'flex',
    flexDirection: 'column',
    zIndex: 20,
    padding: '14px 12px',
    gap: '10px',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  title: {
    fontSize: '12px',
    fontWeight: 600,
    color: 'rgba(255,255,255,0.7)',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },
  clearBtn: {
    background: 'none',
    border: 'none',
    color: 'rgba(255,255,255,0.3)',
    fontSize: '11px',
    cursor: 'pointer',
    padding: '2px 4px',
  },
  dropZone: {
    flex: 1,
    border: '1px dashed rgba(255,255,255,0.1)',
    borderRadius: '6px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'flex-start',
    overflowY: 'auto',
    padding: '8px',
    transition: 'border-color 0.15s, background 0.15s',
  },
  dropZoneActive: {
    borderColor: 'rgba(133,183,235,0.6)',
    background: 'rgba(133,183,235,0.05)',
  },
  emptyHint: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '8px',
    color: 'rgba(255,255,255,0.2)',
    fontSize: '11px',
    marginTop: 'auto',
    marginBottom: 'auto',
    height: '100%',
    justifyContent: 'center',
  },
  emptyIcon: {
    fontSize: '24px',
    opacity: 0.4,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '6px',
    width: '100%',
  },
  thumb: {
    position: 'relative',
    borderRadius: '4px',
    overflow: 'hidden',
    aspectRatio: '1',
    background: 'rgba(255,255,255,0.05)',
  },
  thumbImg: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    display: 'block',
  },
  thumbPlaceholder: {
    width: '100%',
    height: '100%',
    background: 'rgba(255,255,255,0.08)',
  },
  removeBtn: {
    position: 'absolute',
    top: '3px',
    right: '3px',
    width: '18px',
    height: '18px',
    borderRadius: '50%',
    background: 'rgba(0,0,0,0.7)',
    border: 'none',
    color: 'rgba(255,255,255,0.7)',
    fontSize: '9px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 0,
  },
  exportBtn: {
    background: 'rgba(133,183,235,0.15)',
    border: '1px solid rgba(133,183,235,0.3)',
    borderRadius: '6px',
    color: '#85B7EB',
    fontSize: '12px',
    fontWeight: 500,
    padding: '8px 0',
    cursor: 'pointer',
    width: '100%',
    transition: 'background 0.15s',
  },
};
