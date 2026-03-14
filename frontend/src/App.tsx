import { useEffect, useState } from 'react'
import { fetchThermostats, refreshThermostats } from './api'
import { ThermostatCard } from './ThermostatCard'
import { Controls } from './Controls'
import type { ThermostatsResponse } from './types'

const POLL_INTERVAL = 60_000

export default function App() {
  const [data, setData] = useState<ThermostatsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [showBulk, setShowBulk] = useState(false)

  useEffect(() => {
    const load = () =>
      fetchThermostats()
        .then(setData)
        .catch((e) => setError(e.message))

    load()
    const id = setInterval(load, POLL_INTERVAL)
    return () => clearInterval(id)
  }, [])

  return (
    <div style={styles.root}>
      <header style={styles.header}>
        <h1 style={styles.title}>Thermostats</h1>
        {data?.last_updated && (
          <span style={styles.updated}>
            Updated {new Date(data.last_updated).toLocaleTimeString()}
          </span>
        )}
        <button
          style={{ ...styles.headerBtn, ...(showBulk ? styles.headerBtnActive : {}) }}
          onClick={() => setShowBulk((v) => !v)}
        >
          ⚙ All
        </button>
        <button
          style={{ ...styles.headerBtn, opacity: refreshing ? 0.5 : 1 }}
          disabled={refreshing}
          onClick={() => {
            setRefreshing(true)
            refreshThermostats()
              .then(setData)
              .catch((e) => setError(e.message))
              .finally(() => setRefreshing(false))
          }}
        >
          {refreshing ? 'Refreshing…' : '↺ Refresh'}
        </button>
      </header>

      {showBulk && (
        <div style={styles.bulkPanel}>
          <span style={styles.bulkLabel}>All thermostats</span>
          <div style={styles.bulkControls}>
            <Controls onSuccess={setData} />
          </div>
        </div>
      )}

      {error && <div style={styles.error}>Error: {error}</div>}

      {!data && !error && <div style={styles.loading}>Loading…</div>}

      {data && (
        <div style={styles.grid}>
          {data.thermostats.map((t) => (
            <ThermostatCard key={t.serial_number} thermostat={t} onSuccess={setData} />
          ))}
        </div>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  root: {
    minHeight: '100vh',
    background: '#0f172a',
    color: '#f1f5f9',
    fontFamily: 'system-ui, sans-serif',
    padding: '32px 24px',
    boxSizing: 'border-box',
  },
  header: {
    display: 'flex',
    alignItems: 'baseline',
    gap: 16,
    marginBottom: 24,
  },
  title: { margin: 0, fontSize: 28, fontWeight: 700 },
  updated: { fontSize: 13, color: '#64748b' },
  headerBtn: {
    background: '#1e293b',
    color: '#94a3b8',
    border: '1px solid #334155',
    borderRadius: 6,
    padding: '6px 14px',
    fontSize: 13,
    cursor: 'pointer',
  },
  headerBtnActive: {
    background: '#1d4ed8',
    color: '#fff',
    borderColor: '#1d4ed8',
  },
  bulkPanel: {
    background: '#1e293b',
    borderRadius: 10,
    padding: '16px 20px',
    marginBottom: 24,
    display: 'flex',
    alignItems: 'flex-start',
    gap: 20,
    flexWrap: 'wrap',
  },
  bulkLabel: {
    fontSize: 14,
    fontWeight: 600,
    color: '#94a3b8',
    paddingTop: 6,
    whiteSpace: 'nowrap',
  },
  bulkControls: { flex: 1, minWidth: 260 },
  error: {
    background: '#450a0a',
    color: '#fca5a5',
    borderRadius: 8,
    padding: '12px 16px',
    marginBottom: 24,
  },
  loading: { color: '#64748b', fontSize: 16 },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
    gap: 20,
  },
}
