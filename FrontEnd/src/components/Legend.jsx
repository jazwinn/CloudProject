import React from 'react';

export default function Legend({ filter, clusterData }) {
  if (filter === 'all' || !clusterData || !clusterData[filter]) {
    return (
      <div style={styles.container}>
        <span style={styles.hint}>Select a filter to cluster by category</span>
      </div>
    );
  }

  const config = clusterData[filter];

  return (
    <div style={styles.container}>
      <span style={styles.label}>{config.label}</span>
      <div style={styles.items}>
        {config.clusters.map((c) => (
          <div key={c.id} style={styles.item}>
            <div
              style={{
                ...styles.dot,
                background: c.color,
                boxShadow: `0 0 8px ${c.color}44`,
              }}
            />
            <span style={styles.name}>{c.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles = {
  container: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    padding: '16px 24px',
    zIndex: 20,
    background: 'linear-gradient(to top, rgba(5,5,5,0.9) 0%, rgba(5,5,5,0) 100%)',
    pointerEvents: 'none',
  },
  label: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    fontWeight: 700,
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
    color: 'var(--text-tertiary)',
  },
  items: {
    display: 'flex',
    gap: '16px',
    flexWrap: 'wrap',
  },
  item: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  dot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
  },
  name: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
  },
  hint: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
    fontStyle: 'italic',
  },
};
