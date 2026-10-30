'use client';
import { auth } from '@/lib/firebase/client';
const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await auth?.currentUser?.getIdToken();
  const headers = new Headers(init.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const res = await fetch(`${base}${path}`, { ...init, headers });
  if (!res.ok) { const body = await res.json().catch(() => ({})); throw new Error(body.detail ?? `Request failed (${res.status})`); }
  return res.status === 204 ? undefined as T : res.json();
}
