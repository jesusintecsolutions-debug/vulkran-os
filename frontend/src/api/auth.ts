import { api } from './client'

export interface User {
  id: string
  email: string
  name: string
  role: 'admin' | 'partner' | 'client'
  avatar_url: string | null
  is_active: boolean
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>('/auth/login', { email, password })
  return data
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>('/auth/me')
  return data
}

export async function refreshToken(refresh_token: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>('/auth/refresh', { refresh_token })
  return data
}
