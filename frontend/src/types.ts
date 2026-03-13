export interface Thermostat {
  name: string
  serial_number: string
  model: string
  firmware: string
  online: boolean
  heating: boolean
  regulation_mode: string
  temperature_f: number
  set_point_f: number
  manual_temperature_f: number
  comfort_temperature_f: number
  comfort_end_time: string
  min_temperature_f: number
  max_temperature_f: number
  vacation_mode: boolean
  vacation_begin: string
  vacation_end: string
  vacation_temperature_f: number
}

export interface ThermostatsResponse {
  last_updated: string | null
  thermostats: Thermostat[]
}
