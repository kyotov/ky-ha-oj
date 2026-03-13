import type { Thermostat } from './types'

interface Props {
  thermostat: Thermostat
}

export function ThermostatCard({ thermostat: t }: Props) {
  const delta = t.temperature_f - t.set_point_f
  const aboveSP = delta > 0

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <span style={styles.name}>{t.name}</span>
        <div style={styles.badges}>
          <span style={{ ...styles.badge, background: t.online ? '#22c55e' : '#ef4444' }}>
            {t.online ? 'Online' : 'Offline'}
          </span>
          {t.heating && <span style={{ ...styles.badge, background: '#f97316' }}>Heating</span>}
          {t.vacation_mode && <span style={{ ...styles.badge, background: '#a855f7' }}>Vacation</span>}
        </div>
      </div>

      <div style={styles.temps}>
        <div style={styles.tempBlock}>
          <div style={styles.tempLabel}>Current</div>
          <div style={styles.tempValue}>{t.temperature_f.toFixed(1)}°F</div>
        </div>
        <div style={{ ...styles.arrow, color: aboveSP ? '#f97316' : '#60a5fa' }}>
          {aboveSP ? '▲' : '▼'}
        </div>
        <div style={styles.tempBlock}>
          <div style={styles.tempLabel}>Set Point</div>
          <div style={styles.tempValue}>{t.set_point_f.toFixed(1)}°F</div>
        </div>
        <div style={styles.tempBlock}>
          <div style={styles.tempLabel}>Δ</div>
          <div style={{ ...styles.tempValue, color: aboveSP ? '#f97316' : '#60a5fa' }}>
            {delta > 0 ? '+' : ''}{delta.toFixed(1)}°F
          </div>
        </div>
      </div>

      <div style={styles.details}>
        <Row label="Mode" value={t.regulation_mode} />
        <Row label="Manual SP" value={`${t.manual_temperature_f.toFixed(1)}°F`} />
        <Row label="Comfort SP" value={`${t.comfort_temperature_f.toFixed(1)}°F`} />
        <Row label="Comfort ends" value={fmtDate(t.comfort_end_time)} />
        <Row label="Range" value={`${t.min_temperature_f}–${t.max_temperature_f}°F`} />
        <Row label="Vacation SP" value={`${t.vacation_temperature_f.toFixed(1)}°F`} />
        <Row label="Vacation" value={`${fmtDate(t.vacation_begin)} → ${fmtDate(t.vacation_end)}`} />
        <Row label="Serial" value={t.serial_number} />
        <Row label="Firmware" value={t.firmware} />
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={styles.row}>
      <span style={styles.rowLabel}>{label}</span>
      <span style={styles.rowValue}>{value}</span>
    </div>
  )
}

function fmtDate(iso: string) {
  const d = new Date(iso)
  if (d.getFullYear() < 2000) return '—'
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    background: '#1e293b',
    borderRadius: 12,
    padding: '20px 24px',
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 8,
  },
  name: {
    fontSize: 18,
    fontWeight: 600,
    textTransform: 'capitalize',
    color: '#f1f5f9',
  },
  badges: { display: 'flex', gap: 6 },
  badge: {
    fontSize: 11,
    fontWeight: 600,
    padding: '2px 8px',
    borderRadius: 999,
    color: '#fff',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  temps: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    background: '#0f172a',
    borderRadius: 8,
    padding: '12px 16px',
  },
  tempBlock: { textAlign: 'center', flex: 1 },
  tempLabel: { fontSize: 10, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' },
  tempValue: { fontSize: 20, fontWeight: 700, color: '#f1f5f9', marginTop: 2 },
  arrow: { fontSize: 16, marginBottom: -4, flexShrink: 0 },
  details: { display: 'flex', flexDirection: 'column', gap: 6 },
  row: { display: 'flex', justifyContent: 'space-between', fontSize: 13 },
  rowLabel: { color: '#94a3b8' },
  rowValue: { color: '#e2e8f0', fontVariantNumeric: 'tabular-nums' },
}
