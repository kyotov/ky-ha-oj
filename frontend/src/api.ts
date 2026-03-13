import axios from 'axios'
import type { ThermostatsResponse } from './types'

const client = axios.create({ baseURL: import.meta.env.DEV ? '/api' : '/' })

export const fetchThermostats = () =>
  client.get<ThermostatsResponse>('/thermostats').then((r) => r.data)

export const refreshThermostats = () =>
  client.post<ThermostatsResponse>('/thermostats/refresh').then((r) => r.data)
