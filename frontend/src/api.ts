import axios from 'axios'
import type { ThermostatsResponse } from './types'

const client = axios.create({ baseURL: import.meta.env.DEV ? '/api' : '/' })

const get = <T>(url: string) => client.get<T>(url).then((r) => r.data)
const post = <T>(url: string, data?: unknown) => client.post<T>(url, data).then((r) => r.data)

export const fetchThermostats = () => get<ThermostatsResponse>('/thermostats')
export const refreshThermostats = () => post<ThermostatsResponse>('/thermostats/refresh')

// Single thermostat
export const setManual = (name: string, temperature_f: number) =>
  post<ThermostatsResponse>(`/thermostats/${encodeURIComponent(name)}/manual`, { temperature_f })

export const setComfort = (name: string, temperature_f: number, end_time: string) =>
  post<ThermostatsResponse>(`/thermostats/${encodeURIComponent(name)}/comfort`, { temperature_f, end_time })

export const setVacation = (name: string, payload: VacationPayload) =>
  post<ThermostatsResponse>(`/thermostats/${encodeURIComponent(name)}/vacation`, payload)

export const setVacationSetpoint = (name: string, temperature_f: number) =>
  post<ThermostatsResponse>(`/thermostats/${encodeURIComponent(name)}/vacation-setpoint`, { temperature_f })

export const setMode = (name: string, mode: number) =>
  post<ThermostatsResponse>(`/thermostats/${encodeURIComponent(name)}/mode`, { mode })

// All thermostats
export const setAllManual = (temperature_f: number) =>
  post<ThermostatsResponse>('/thermostats/all/manual', { temperature_f })

export const setAllComfort = (temperature_f: number, end_time: string) =>
  post<ThermostatsResponse>('/thermostats/all/comfort', { temperature_f, end_time })

export const setAllVacation = (payload: VacationPayload) =>
  post<ThermostatsResponse>('/thermostats/all/vacation', payload)

export const setAllVacationSetpoint = (temperature_f: number) =>
  post<ThermostatsResponse>('/thermostats/all/vacation-setpoint', { temperature_f })

export const setAllMode = (mode: number) =>
  post<ThermostatsResponse>('/thermostats/all/mode', { mode })

export interface VacationPayload {
  enabled: boolean
  temperature_f?: number
  begin?: string
  end?: string
}
