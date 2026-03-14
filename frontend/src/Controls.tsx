import { useState } from 'react'
import type { ThermostatsResponse } from './types'
import {
  setManual, setComfort, setVacationSetpoint, setMode,
  setAllManual, setAllComfort, setAllVacationSetpoint, setAllMode,
} from './api'

interface Props {
  name?: string  // undefined = all thermostats
  onSuccess: (data: ThermostatsResponse) => void
}

type Section = 'manual' | 'comfort' | 'vacsp' | 'mode' | null

const MODES = [
  { value: 1, label: 'Manual' },
  { value: 2, label: 'Comfort' },
  { value: 3, label: 'Schedule' },
  { value: 4, label: 'Vacation' },
]

export function Controls({ name, onSuccess }: Props) {
  const [open, setOpen] = useState<Section>(null)
  const [temp, setTemp] = useState('68')
  const [endTime, setEndTime] = useState(() => {
    const d = new Date()
    d.setDate(d.getDate() + 1)
    return d.toISOString().slice(0, 16)
  })
  const [mode, setModeVal] = useState('1')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  function toggle(s: Section) {
    setOpen((prev) => (prev === s ? null : s))
    setErr(null)
  }

  async function submit(action: () => Promise<ThermostatsResponse>) {
    setBusy(true)
    setErr(null)
    try {
      const data = await action()
      onSuccess(data)
      setOpen(null)
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const tempF = parseFloat(temp)

  return (
    <div style={s.root}>
      <div style={s.tabs}>
        {(['manual', 'comfort', 'vacsp', 'mode'] as Section[]).map((sec) => (
          <button
            key={sec}
            style={{ ...s.tab, ...(open === sec ? s.tabActive : {}) }}
            onClick={() => toggle(sec)}
          >
            {sec === 'manual' ? 'Manual' : sec === 'comfort' ? 'Comfort' : sec === 'vacsp' ? 'Vac SP' : 'Mode'}
          </button>
        ))}
      </div>

      {open === 'manual' && (
        <div style={s.form}>
          <TempInput value={temp} onChange={setTemp} />
          <Btn
            busy={busy}
            onClick={() =>
              submit(() =>
                name ? setManual(name, tempF) : setAllManual(tempF)
              )
            }
          />
        </div>
      )}

      {open === 'comfort' && (
        <div style={s.form}>
          <TempInput value={temp} onChange={setTemp} />
          <input
            type="datetime-local"
            value={endTime}
            onChange={(e) => setEndTime(e.target.value)}
            style={s.input}
          />
          <Btn
            busy={busy}
            onClick={() =>
              submit(() =>
                name
                  ? setComfort(name, tempF, endTime)
                  : setAllComfort(tempF, endTime)
              )
            }
          />
        </div>
      )}

      {open === 'vacsp' && (
        <div style={s.form}>
          <TempInput value={temp} onChange={setTemp} />
          <Btn
            busy={busy}
            onClick={() =>
              submit(() =>
                name ? setVacationSetpoint(name, tempF) : setAllVacationSetpoint(tempF)
              )
            }
          />
        </div>
      )}

      {open === 'mode' && (
        <div style={s.form}>
          <select value={mode} onChange={(e) => setModeVal(e.target.value)} style={s.input}>
            {MODES.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
          <Btn
            busy={busy}
            onClick={() =>
              submit(() =>
                name ? setMode(name, parseInt(mode)) : setAllMode(parseInt(mode))
              )
            }
          />
        </div>
      )}

      {err && <div style={s.err}>{err}</div>}
    </div>
  )
}

function TempInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <input
        type="number"
        value={value}
        step="0.5"
        onChange={(e) => onChange(e.target.value)}
        style={{ ...s.input, width: 80 }}
      />
      <span style={{ color: '#94a3b8', fontSize: 13 }}>°F</span>
    </div>
  )
}

function Btn({ busy, onClick }: { busy: boolean; onClick: () => void }) {
  return (
    <button style={{ ...s.setBtn, opacity: busy ? 0.5 : 1 }} disabled={busy} onClick={onClick}>
      {busy ? '…' : 'Set'}
    </button>
  )
}

const s: Record<string, React.CSSProperties> = {
  root: { display: 'flex', flexDirection: 'column', gap: 8 },
  tabs: { display: 'flex', gap: 4 },
  tab: {
    flex: 1,
    background: '#0f172a',
    color: '#94a3b8',
    border: '1px solid #334155',
    borderRadius: 6,
    padding: '5px 4px',
    fontSize: 12,
    cursor: 'pointer',
  },
  tabActive: {
    background: '#1d4ed8',
    color: '#fff',
    borderColor: '#1d4ed8',
  },
  form: { display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' },
  input: {
    background: '#0f172a',
    color: '#f1f5f9',
    border: '1px solid #334155',
    borderRadius: 6,
    padding: '5px 10px',
    fontSize: 13,
    flex: 1,
    minWidth: 0,
  },
  setBtn: {
    background: '#1d4ed8',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    padding: '5px 16px',
    fontSize: 13,
    cursor: 'pointer',
    flexShrink: 0,
  },
  err: { color: '#fca5a5', fontSize: 12 },
}
