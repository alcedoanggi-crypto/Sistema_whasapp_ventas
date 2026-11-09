export const fechaHora = (v) =>
  v ? new Date(v).toLocaleString('es', { dateStyle: 'short', timeStyle: 'short' }) : '—'
export const fecha = (v) => (v ? new Date(v).toLocaleDateString('es', { dateStyle: 'medium' }) : '—')
export const hora = (v) => (v ? new Date(v).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' }) : '')
// Hora si es de hoy; fecha corta + hora si no (para las burbujas del chat)
export const momento = (v) => {
  const d = new Date(v)
  return d.toDateString() === new Date().toDateString()
    ? hora(d)
    : d.toLocaleString('es', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}
export const dinero = (v) =>
  new Intl.NumberFormat('es', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(v || 0)
export const pct = (v) => `${(v ?? 0).toFixed(1)}%`

// Mismo patrón que el backend (services/plantillas.py)
export const PATRON_VARIABLE = /\{\{\s*([a-z_][a-z0-9_]*)\s*\}\}/g
export function extraerVariables(...textos) {
  const vistas = []
  for (const t of textos) for (const m of (t || '').matchAll(PATRON_VARIABLE)) if (!vistas.includes(m[1])) vistas.push(m[1])
  return vistas
}
export function renderizar(texto, valores = {}) {
  return (texto || '').replace(PATRON_VARIABLE, (m, n) => (valores[n] ?? '') !== '' ? valores[n] : m)
}
