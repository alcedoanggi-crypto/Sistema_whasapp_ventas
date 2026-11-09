// Cliente HTTP mínimo: añade el token y traduce errores de FastAPI a mensajes legibles.
const CLAVE = 'wa_token'

export const sesion = {
  token: () => localStorage.getItem(CLAVE),
  guardar: (t) => localStorage.setItem(CLAVE, t),
  cerrar: () => localStorage.removeItem(CLAVE),
}

function mensajeError(cuerpo, status) {
  const d = cuerpo?.detail
  if (Array.isArray(d)) return d.map((e) => `${e.loc?.slice(1).join('.')}: ${e.msg}`).join(' · ')
  return d || `Error ${status}`
}

export async function api(ruta, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  const t = sesion.token()
  if (t) headers.Authorization = `Bearer ${t}`
  const r = await fetch(`/api${ruta}`, { method, headers, body: body ? JSON.stringify(body) : undefined })
  if (r.status === 401 && ruta !== '/auth/login') {
    sesion.cerrar()
    window.location.href = '/login'
    return
  }
  if (r.status === 204) return null
  const datos = await r.json().catch(() => null)
  if (!r.ok) throw new Error(mensajeError(datos, r.status))
  return datos
}

export const get = (ruta) => api(ruta)
export const post = (ruta, body) => api(ruta, { method: 'POST', body })
export const put = (ruta, body) => api(ruta, { method: 'PUT', body })
export const patch = (ruta, body) => api(ruta, { method: 'PATCH', body })
export const del = (ruta) => api(ruta, { method: 'DELETE' })
