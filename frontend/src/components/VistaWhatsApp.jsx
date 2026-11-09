import { hora, momento as formatoMomento } from '../formato'

// Aplica el formato de WhatsApp (*negrita*, _cursiva_, ~tachado~) y resalta {{variables}} sin valor.
function formatear(texto) {
  const partes = []
  const re = /(\*[^*\n]+\*|_[^_\n]+_|~[^~\n]+~|\{\{\s*[a-z_][a-z0-9_]*\s*\}\})/g
  let ultimo = 0
  for (const m of texto.matchAll(re)) {
    if (m.index > ultimo) partes.push(texto.slice(ultimo, m.index))
    const t = m[0]
    if (t.startsWith('{{'))
      partes.push(
        <span key={m.index} className="bg-amber-200/70 text-amber-900 rounded px-0.5 font-mono text-[12px]">
          {t}
        </span>,
      )
    else if (t[0] === '*') partes.push(<strong key={m.index}>{t.slice(1, -1)}</strong>)
    else if (t[0] === '_') partes.push(<em key={m.index}>{t.slice(1, -1)}</em>)
    else partes.push(<s key={m.index}>{t.slice(1, -1)}</s>)
    ultimo = m.index + t.length
  }
  if (ultimo < texto.length) partes.push(texto.slice(ultimo))
  return partes
}

export function Texto({ children }) {
  return <span className="whitespace-pre-wrap break-words">{formatear(children || '')}</span>
}

const PALOMITAS = { aceptado: '✓', enviado: '✓', entregado: '✓✓', leido: '✓✓', fallido: '⚠', en_cola: '🕓', enviando: '🕓' }

export function Burbuja({ saliente = true, encabezado, cuerpo, pie, botones = [], estado, momento, etiqueta, error }) {
  return (
    <div className={`flex ${saliente ? 'justify-end' : 'justify-start'} mb-1.5`}>
      <div className="max-w-[85%]">
        <div
          className={`rounded-lg shadow-sm px-2.5 pt-1.5 pb-1 text-[14px] text-slate-900 ${
            saliente ? 'bg-wa-bubble rounded-tr-none' : 'bg-white rounded-tl-none'
          }`}
        >
          {etiqueta && <div className="text-[11px] font-medium text-wa-700 mb-0.5">{etiqueta}</div>}
          {encabezado && (
            <div className="font-bold mb-1">
              <Texto>{encabezado}</Texto>
            </div>
          )}
          <Texto>{cuerpo}</Texto>
          {pie && (
            <div className="text-[12px] text-slate-500 mt-1">
              <Texto>{pie}</Texto>
            </div>
          )}
          <div className="flex justify-end items-center gap-1 text-[11px] text-slate-500 mt-0.5">
            <span>{momento ? formatoMomento(momento) : hora(new Date())}</span>
            {saliente && estado && (
              <span
                title={estado}
                className={estado === 'leido' ? 'text-sky-500' : estado === 'fallido' ? 'text-red-500' : ''}
              >
                {PALOMITAS[estado] || ''}
              </span>
            )}
          </div>
        </div>
        {error && <div className="text-[11px] text-red-600 mt-0.5 text-right">{error}</div>}
        {botones.filter(Boolean).map((b, i) => (
          <div key={i} className="bg-white rounded-lg shadow-sm mt-0.5 py-2 text-center text-[14px] text-sky-600 font-medium">
            ↩ {b}
          </div>
        ))}
      </div>
    </div>
  )
}

// Marco de teléfono con cabecera verde: vista previa del editor de plantillas.
export function Telefono({ nombre = 'Tienda Demo', children }) {
  return (
    <div className="mx-auto w-full max-w-[340px] rounded-[2rem] border-[10px] border-slate-800 bg-slate-800 shadow-xl overflow-hidden">
      <div className="bg-wa-800 text-white px-3 py-2.5 flex items-center gap-2.5">
        <span className="text-lg">‹</span>
        <div className="w-8 h-8 rounded-full bg-wa-500 grid place-items-center text-sm font-bold">{nombre[0]}</div>
        <div className="leading-tight">
          <div className="text-sm font-semibold">
            {nombre} <span className="text-wa-100" title="Cuenta de empresa">✔</span>
          </div>
          <div className="text-[11px] text-wa-100">Cuenta de empresa</div>
        </div>
      </div>
      <div className="wa-fondo min-h-[420px] p-3 flex flex-col justify-end">
        <div className="text-center mb-3">
          <span className="text-[11px] bg-white/80 text-slate-600 rounded px-2 py-0.5 shadow-sm">HOY</span>
        </div>
        {children}
      </div>
    </div>
  )
}
