import { useEffect, useState } from 'react'
import { fetchThermostats, refreshThermostats } from './api'
import { ThermostatCard } from './ThermostatCard'
import type { ThermostatsResponse } from './types'

const POLL_INTERVAL = 60_000

export default function App() {
  const [data, setData] = useState<ThermostatsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

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
          style={{ ...styles.refreshBtn, opacity: refreshing ? 0.5 : 1 }}
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

      {error && <div style={styles.error}>Error: {error}</div>}

      {!data && !error && <div style={styles.loading}>Loading…</div>}

      {data && (
        <div style={styles.grid}>
          {data.thermostats.map((t) => (
            <ThermostatCard key={t.serial_number} thermostat={t} />
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
    marginBottom: 32,
  },
  title: { margin: 0, fontSize: 28, fontWeight: 700 },
  updated: { fontSize: 13, color: '#64748b' },
  error: {
    background: '#450a0a',
    color: '#fca5a5',
    borderRadius: 8,
    padding: '12px 16px',
    marginBottom: 24,
  },
  loading: { color: '#64748b', fontSize: 16 },
  refreshBtn: {
    marginLeft: 'auto',
    background: '#1e293b',
    color: '#94a3b8',
    border: '1px solid #334155',
    borderRadius: 6,
    padding: '6px 14px',
    fontSize: 13,
    cursor: 'pointer',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
    gap: 20,
  },
}
