import { useEffect, useState } from 'react'
import { del, post, put } from '../api'
import { useApi } from '../hooks'
import { Aviso, Boton, Campo, Card, Cargando, Encabezado, Input, Insignia, Modal, Select, Textarea, useAccion } from '../components/ui'

const INFO_DISPARADOR = {
  bienvenida: { icono: '👋', titulo: 'Bienvenida', evento: 'alta (contacto nuevo con opt-in)' },
  carrito_abandonado: { icono: '🛒', titulo: 'Carrito abandonado', evento: 'carrito_abandonado · se cancela si llega "compra"' },
  recordatorio_pago: { icono: '💳', titulo: 'Recordatorio de pago', evento: 'pago_pendiente · se cancela con "pago_realizado"' },
  post_venta: { icono: '⭐', titulo: 'Seguimiento post-venta', evento: 'compra' },
}

function describirRetraso(min) {
  if (min === 0) return 'inmediato'
  if (min % 1440 === 0) return `${min / 1440} día(s) después`
  if (min % 60 === 0) return `${min / 60} hora(s) después`
  return `${min} min después`
}

function Disparador({ d, plantillas, onGuardado }) {
  const [f, setF] = useState(d)
  const [ejecutar, ocupado, error] = useAccion()
  const [ok, setOk] = useState(false)
  useEffect(() => setF(d), [d])
  const info = INFO_DISPARADOR[d.tipo] || { icono: '⚡', titulo: d.tipo, evento: d.tipo }
  const cambiado = f.activo !== d.activo || f.plantilla_id !== d.plantilla_id || f.retraso_minutos !== d.retraso_minutos

  async function guardar(datos = f) {
    setOk(false)
    const r = await ejecutar(() => put(`/automatizaciones/disparadores/${d.id}`, { activo: datos.activo, plantilla_id: datos.plantilla_id, retraso_minutos: datos.retraso_minutos }))
    if (r) { setOk(true); onGuardado() } else setF(d)
  }

  return (
    <div className={`rounded-xl border p-4 space-y-3 transition ${f.activo ? 'border-wa-500 bg-wa-50/40' : 'border-slate-200 bg-white'}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-semibold">{info.icono} {info.titulo}</div>
          <div className="text-xs text-slate-500">{d.descripcion}</div>
          <div className="text-[11px] text-slate-400 mt-0.5">Evento: <span className="font-mono">{info.evento}</span></div>
        </div>
        <button
          onClick={() => { const n = { ...f, activo: !f.activo }; setF(n); guardar(n) }}
          className={`relative w-11 h-6 rounded-full transition shrink-0 ${f.activo ? 'bg-wa-600' : 'bg-slate-300'}`}
          title={f.activo ? 'Desactivar' : 'Activar'}
          disabled={ocupado}
        >
          <span className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all ${f.activo ? 'left-5.5' : 'left-0.5'}`} />
        </button>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Campo etiqueta="Plantilla">
          <Select value={f.plantilla_id || ''} onChange={(e) => setF({ ...f, plantilla_id: e.target.value ? Number(e.target.value) : null })}>
            <option value="">—</option>
            {plantillas?.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
          </Select>
        </Campo>
        <Campo etiqueta="Retraso (minutos)" ayuda={describirRetraso(f.retraso_minutos)}>
          <Input type="number" min={0} value={f.retraso_minutos} onChange={(e) => setF({ ...f, retraso_minutos: Number(e.target.value) })} />
        </Campo>
      </div>
      <Aviso>{error}</Aviso>
      {ok && !cambiado && <div className="text-xs text-emerald-700">✓ Guardado</div>}
      {cambiado && <Boton onClick={() => guardar()} disabled={ocupado}>Guardar cambios</Boton>}
    </div>
  )
}

const RESPUESTA_VACIA = { nombre: '', palabras_clave: '', respuesta: '', activo: true, prioridad: 0 }

function FormRespuesta({ inicial, onListo }) {
  const [f, setF] = useState(inicial ? { ...inicial, palabras_clave: inicial.palabras_clave.join(', ') } : RESPUESTA_VACIA)
  const [ejecutar, ocupado, error] = useAccion()

  async function guardar(e) {
    e.preventDefault()
    const datos = { ...f, palabras_clave: f.palabras_clave.split(',').map((p) => p.trim()).filter(Boolean), prioridad: Number(f.prioridad) }
    const r = await ejecutar(() => (inicial ? put(`/automatizaciones/respuestas/${inicial.id}`, datos) : post('/automatizaciones/respuestas', datos)))
    if (r) onListo()
  }

  return (
    <form onSubmit={guardar} className="space-y-3">
      <Campo etiqueta="Nombre"><Input value={f.nombre} onChange={(e) => setF({ ...f, nombre: e.target.value })} required /></Campo>
      <Campo etiqueta="Palabras clave" ayuda="Separadas por coma. Se ignoran mayúsculas y tildes. BAJA/STOP/ALTA están reservadas.">
        <Input value={f.palabras_clave} onChange={(e) => setF({ ...f, palabras_clave: e.target.value })} required />
      </Campo>
      <Campo etiqueta="Respuesta" ayuda="Puedes usar {{nombre}}. Solo se envía dentro de la ventana de 24 h (el cliente acaba de escribir).">
        <Textarea rows={4} value={f.respuesta} onChange={(e) => setF({ ...f, respuesta: e.target.value })} required />
      </Campo>
      <div className="grid grid-cols-2 gap-3 items-end">
        <Campo etiqueta="Prioridad" ayuda="Mayor gana si coinciden varias">
          <Input type="number" value={f.prioridad} onChange={(e) => setF({ ...f, prioridad: e.target.value })} />
        </Campo>
        <label className="flex items-center gap-2 text-sm pb-6">
          <input type="checkbox" className="accent-wa-700 w-4 h-4" checked={f.activo} onChange={(e) => setF({ ...f, activo: e.target.checked })} /> Activa
        </label>
      </div>
      <Aviso>{error}</Aviso>
      <div className="flex justify-end"><Boton disabled={ocupado}>Guardar</Boton></div>
    </form>
  )
}

function Probador() {
  const [texto, setTexto] = useState('')
  const [r, setR] = useState(null)
  const [ejecutar, ocupado] = useAccion()
  async function probar(e) {
    e.preventDefault()
    setR(await ejecutar(() => post('/automatizaciones/respuestas/probar', { texto })))
  }
  return (
    <form onSubmit={probar} className="space-y-2">
      <div className="flex gap-2">
        <Input placeholder="Ej.: ¿Cuánto cuesta el envío?" value={texto} onChange={(e) => setTexto(e.target.value)} />
        <Boton variante="secundario" disabled={!texto || ocupado}>Probar</Boton>
      </div>
      {r && (
        <Aviso tipo={r.accion === 'ninguna' ? 'alerta' : 'info'}>
          {r.accion === 'baja' && 'Palabra de baja: se registra el opt-out del contacto y se le confirma.'}
          {r.accion === 'alta' && 'Palabra de alta: se registra el opt-in (origen: WhatsApp) y se le confirma.'}
          {r.accion === 'respuesta' && <>Responde la regla <strong>{r.regla.nombre}</strong>: “{r.regla.respuesta}”</>}
          {r.accion === 'ninguna' && 'Ninguna regla coincide: el mensaje queda en la bandeja para respuesta manual.'}
        </Aviso>
      )}
    </form>
  )
}

export default function Automatizaciones() {
  const { datos: disparadores, recargar: recargarD } = useApi('/automatizaciones/disparadores')
  const { datos: respuestas, recargar: recargarR } = useApi('/automatizaciones/respuestas')
  const { datos: plantillas } = useApi('/plantillas?estado=APROBADA')
  const [editando, setEditando] = useState(null) // null | 'nueva' | respuesta

  async function eliminar(r) {
    if (!confirm(`¿Eliminar la respuesta "${r.nombre}"?`)) return
    await del(`/automatizaciones/respuestas/${r.id}`)
    recargarR()
  }

  return (
    <>
      <Encabezado titulo="Automatizaciones" subtitulo="Disparadores por eventos de la tienda y respuestas automáticas por palabra clave" />
      <div className="space-y-6">
        <Card titulo="Disparadores automáticos" accion={<span className="text-xs text-slate-500">Solo plantillas aprobadas · solo contactos con opt-in</span>}>
          {!disparadores ? <Cargando /> : (
            <div className="grid md:grid-cols-2 gap-4">
              {disparadores.map((d) => <Disparador key={d.id} d={d} plantillas={plantillas} onGuardado={recargarD} />)}
            </div>
          )}
        </Card>

        <div className="grid lg:grid-cols-3 gap-6 items-start">
          <Card titulo="Respuestas por palabra clave" className="lg:col-span-2" accion={<Boton onClick={() => setEditando('nueva')}>+ Nueva</Boton>} sinPadding>
            <ul className="divide-y">
              {respuestas?.map((r) => (
                <li key={r.id} className="p-4 flex gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{r.nombre}</span>
                      {!r.activo && <Insignia>inactiva</Insignia>}
                      <span className="text-xs text-slate-400">prioridad {r.prioridad} · {r.coincidencias} usos</span>
                    </div>
                    <div className="flex flex-wrap gap-1 my-1.5">
                      {r.palabras_clave.map((p) => <Insignia key={p} color="amarillo">{p}</Insignia>)}
                    </div>
                    <p className="text-sm text-slate-600 whitespace-pre-wrap">{r.respuesta}</p>
                  </div>
                  <div className="flex flex-col gap-1">
                    <Boton variante="fantasma" onClick={() => setEditando(r)}>Editar</Boton>
                    <Boton variante="fantasma" className="text-red-600" onClick={() => eliminar(r)}>Eliminar</Boton>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
          <Card titulo="Probar el bot">
            <p className="text-sm text-slate-500 mb-3">Qué haría el sistema si un cliente escribiera esto (no envía nada).</p>
            <Probador />
            <div className="mt-4 text-xs text-slate-500 space-y-1">
              <div><strong>Baja automática:</strong> BAJA, STOP, DETENER, CANCELAR, UNSUBSCRIBE</div>
              <div><strong>Alta:</strong> ALTA, START, SUSCRIBIRME</div>
            </div>
          </Card>
        </div>
      </div>
      <Modal abierto={!!editando} titulo={editando === 'nueva' ? 'Nueva respuesta automática' : 'Editar respuesta'} onCerrar={() => setEditando(null)}>
        {editando && <FormRespuesta inicial={editando === 'nueva' ? null : editando} onListo={() => { setEditando(null); recargarR() }} />}
      </Modal>
    </>
  )
}
