import { forwardRef, useEffect, useState } from 'react'

export function Card({ titulo, accion, children, className = '', sinPadding = false }) {
  return (
    <section className={`bg-white rounded-xl border border-slate-200 shadow-sm ${className}`}>
      {(titulo || accion) && (
        <header className="flex items-center justify-between gap-3 px-5 py-3 border-b border-slate-100">
          <h2 className="font-semibold text-slate-800">{titulo}</h2>
          {accion}
        </header>
      )}
      <div className={sinPadding ? '' : 'p-5'}>{children}</div>
    </section>
  )
}

const VARIANTES = {
  primario: 'bg-wa-700 hover:bg-wa-800 text-white',
  secundario: 'bg-white hover:bg-slate-50 text-slate-700 border border-slate-300',
  peligro: 'bg-red-600 hover:bg-red-700 text-white',
  fantasma: 'hover:bg-slate-100 text-slate-600',
}
export function Boton({ variante = 'primario', className = '', ...props }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium transition disabled:opacity-50 disabled:cursor-not-allowed ${VARIANTES[variante]} ${className}`}
      {...props}
    />
  )
}

export function Campo({ etiqueta, ayuda, children }) {
  return (
    <label className="block">
      <span className="block text-sm font-medium text-slate-700 mb-1">{etiqueta}</span>
      {children}
      {ayuda && <span className="block text-xs text-slate-500 mt-1">{ayuda}</span>}
    </label>
  )
}

export const claseInput =
  'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-wa-500/40 focus:border-wa-600 bg-white'
export const Input = (p) => <input className={claseInput} {...p} />
export const Textarea = forwardRef((p, ref) => <textarea ref={ref} className={claseInput} {...p} />)
export const Select = ({ children, ...p }) => (
  <select className={claseInput} {...p}>
    {children}
  </select>
)

const COLORES = {
  verde: 'bg-emerald-100 text-emerald-800',
  azul: 'bg-sky-100 text-sky-800',
  amarillo: 'bg-amber-100 text-amber-800',
  rojo: 'bg-red-100 text-red-800',
  gris: 'bg-slate-100 text-slate-700',
  morado: 'bg-violet-100 text-violet-800',
}
export function Insignia({ color = 'gris', children }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${COLORES[color]}`}>
      {children}
    </span>
  )
}

const COLOR_ESTADO = {
  // plantillas
  APROBADA: 'verde', PENDIENTE: 'amarillo', RECHAZADA: 'rojo', BORRADOR: 'gris',
  // campañas
  PROGRAMADA: 'azul', EN_CURSO: 'morado', COMPLETADA: 'verde', CANCELADA: 'rojo',
  // mensajes
  en_cola: 'gris', enviando: 'gris', aceptado: 'azul', enviado: 'azul', entregado: 'verde', leido: 'verde', fallido: 'rojo', recibido: 'morado',
  // disparos de eventos
  pendiente: 'amarillo', procesando: 'azul', omitido: 'gris', cancelado: 'rojo',
}
export function Estado({ valor }) {
  if (!valor) return null
  return <Insignia color={COLOR_ESTADO[valor] || 'gris'}>{String(valor).replaceAll('_', ' ')}</Insignia>
}

export function Modal({ abierto, titulo, onCerrar, children, ancho = 'max-w-lg' }) {
  useEffect(() => {
    const esc = (e) => e.key === 'Escape' && onCerrar()
    if (abierto) window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [abierto, onCerrar])
  if (!abierto) return null
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-900/40 p-4 overflow-y-auto" onMouseDown={onCerrar}>
      <div className={`bg-white rounded-xl shadow-xl w-full ${ancho} mt-10`} onMouseDown={(e) => e.stopPropagation()}>
        <header className="flex items-center justify-between px-5 py-3 border-b">
          <h3 className="font-semibold">{titulo}</h3>
          <button onClick={onCerrar} className="text-slate-400 hover:text-slate-700 text-xl leading-none">
            ×
          </button>
        </header>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

export function Aviso({ tipo = 'error', children }) {
  if (!children) return null
  const c = {
    error: 'bg-red-50 text-red-800 border-red-200',
    ok: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    info: 'bg-sky-50 text-sky-800 border-sky-200',
    alerta: 'bg-amber-50 text-amber-900 border-amber-200',
  }[tipo]
  return <div className={`border rounded-lg px-3 py-2 text-sm ${c}`}>{children}</div>
}

export const Cargando = () => <div className="py-10 text-center text-slate-400 text-sm">Cargando…</div>
export const Vacio = ({ children }) => <div className="py-10 text-center text-slate-400 text-sm">{children}</div>

export function Encabezado({ titulo, subtitulo, children }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3 mb-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{titulo}</h1>
        {subtitulo && <p className="text-sm text-slate-500 mt-0.5">{subtitulo}</p>}
      </div>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
  )
}

export function Tabla({ columnas, children }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-slate-500 border-b border-slate-200">
            {columnas.map((c) => (
              <th key={c} className="px-4 py-2.5 font-medium whitespace-nowrap">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">{children}</tbody>
      </table>
    </div>
  )
}
export const Td = ({ className = '', ...p }) => <td className={`px-4 py-2.5 ${className}`} {...p} />

// Ejecuta una acción async capturando el error para mostrarlo en pantalla.
export function useAccion() {
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState(null)
  async function ejecutar(fn) {
    setOcupado(true)
    setError(null)
    try {
      return await fn()
    } catch (e) {
      setError(e.message)
      return undefined
    } finally {
      setOcupado(false)
    }
  }
  return [ejecutar, ocupado, error, setError]
}
