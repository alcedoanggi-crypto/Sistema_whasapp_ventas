import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { post } from '../api'
import { useApi } from '../hooks'
import { extraerVariables, hora, renderizar } from '../formato'
import { Aviso, Boton, Campo, Input, Insignia, Modal, Select, Vacio, useAccion } from '../components/ui'
import { Burbuja } from '../components/VistaWhatsApp'

const ETIQUETA_ORIGEN = {
  campana: '📣 Campaña',
  disparador: '⚡ Automatización',
  auto_respuesta: '🤖 Respuesta automática',
  sistema: '🤖 Sistema',
  manual: null,
}

function Lista({ seleccionado }) {
  const [q, setQ] = useState('')
  const [soloNoLeidos, setSoloNoLeidos] = useState(false)
  const params = new URLSearchParams({ ...(q && { q }), ...(soloNoLeidos && { solo_no_leidos: true }) })
  const { datos } = useApi(`/conversaciones?${params}`, { intervalo: 4000 })

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 space-y-2 border-b">
        <Input placeholder="Buscar conversación…" value={q} onChange={(e) => setQ(e.target.value)} />
        <label className="flex items-center gap-2 text-xs text-slate-600">
          <input type="checkbox" className="accent-wa-700" checked={soloNoLeidos} onChange={(e) => setSoloNoLeidos(e.target.checked)} />
          Solo no leídos
        </label>
      </div>
      <ul className="flex-1 overflow-y-auto divide-y">
        {datos?.length === 0 && <Vacio>Sin conversaciones</Vacio>}
        {datos?.map(({ contacto: c, ultimo, ventana_abierta }) => (
          <li key={c.id}>
            <Link
              to={`/conversaciones/${c.id}`}
              className={`flex gap-3 px-3 py-2.5 hover:bg-slate-50 ${Number(seleccionado) === c.id ? 'bg-wa-50' : ''}`}
            >
              <div className="w-10 h-10 rounded-full bg-slate-200 grid place-items-center font-semibold text-slate-600 shrink-0">
                {(c.nombre || '#')[0].toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex justify-between gap-2">
                  <span className="font-medium truncate">{c.nombre || `+${c.telefono}`}</span>
                  <span className="text-[11px] text-slate-500 shrink-0">{hora(c.ultimo_mensaje)}</span>
                </div>
                <div className="flex justify-between gap-2 items-center">
                  <span className="text-xs text-slate-500 truncate">
                    {ultimo?.direccion === 'saliente' && '✓ '}
                    {ultimo?.contenido}
                  </span>
                  {c.no_leidos > 0 && (
                    <span className="bg-wa-500 text-white text-[11px] rounded-full min-w-5 h-5 px-1 grid place-items-center shrink-0">{c.no_leidos}</span>
                  )}
                </div>
                {ventana_abierta && <span className="text-[10px] text-wa-700">● ventana 24 h abierta</span>}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}

function EnviarPlantilla({ contacto, onListo }) {
  const { datos: plantillas } = useApi('/plantillas?estado=APROBADA')
  const [id, setId] = useState('')
  const [valores, setValores] = useState({})
  const [ejecutar, ocupado, error] = useAccion()
  const p = plantillas?.find((x) => x.id === Number(id))
  const variables = p ? extraerVariables(p.encabezado, p.cuerpo).filter((v) => !['nombre', 'nombre_completo', 'telefono'].includes(v)) : []

  async function enviar() {
    if (await ejecutar(() => post(`/conversaciones/${contacto.id}/plantilla`, { plantilla_id: p.id, variables: valores }))) onListo()
  }

  return (
    <div className="space-y-3">
      <Campo etiqueta="Plantilla aprobada">
        <Select value={id} onChange={(e) => { setId(e.target.value); setValores({}) }}>
          <option value="">Selecciona…</option>
          {plantillas?.map((x) => <option key={x.id} value={x.id}>{x.nombre}</option>)}
        </Select>
      </Campo>
      {variables.map((v) => (
        <Campo key={v} etiqueta={<span className="font-mono">{`{{${v}}}`}</span>}>
          <Input value={valores[v] || ''} onChange={(e) => setValores({ ...valores, [v]: e.target.value })} />
        </Campo>
      ))}
      {p && (
        <div className="wa-fondo rounded-lg p-3">
          <Burbuja
            encabezado={renderizar(p.encabezado, { nombre: contacto.nombre?.split(' ')[0], ...valores })}
            cuerpo={renderizar(p.cuerpo, { nombre: contacto.nombre?.split(' ')[0], ...valores })}
            pie={p.pie}
            botones={p.botones}
          />
        </div>
      )}
      <Aviso>{error}</Aviso>
      <div className="flex justify-end">
        <Boton onClick={enviar} disabled={!p || ocupado}>Enviar plantilla</Boton>
      </div>
    </div>
  )
}

function Hilo({ id, sandbox }) {
  const { datos, recargar } = useApi(`/conversaciones/${id}`, { intervalo: 2500 })
  const [texto, setTexto] = useState('')
  const [simulado, setSimulado] = useState('')
  const [modalPlantilla, setModalPlantilla] = useState(false)
  const [ejecutar, ocupado, error] = useAccion()
  const fin = useRef(null)
  const cantidad = datos?.mensajes.length

  useEffect(() => { fin.current?.scrollIntoView({ block: 'end' }) }, [cantidad])
  useEffect(() => {
    if (datos?.contacto.no_leidos) post(`/conversaciones/${id}/leido`).catch(() => {})
  }, [id, datos?.contacto.no_leidos])

  if (!datos) return <Vacio>Cargando…</Vacio>
  const { contacto: c, ventana_abierta, mensajes } = datos

  async function responder(e) {
    e.preventDefault()
    if (await ejecutar(() => post(`/conversaciones/${id}/texto`, { texto }))) { setTexto(''); recargar() }
  }
  async function simular(e) {
    e.preventDefault()
    if (await ejecutar(() => post(`/conversaciones/${id}/simular-entrante`, { texto: simulado }))) {
      setSimulado('')
      setTimeout(recargar, 800)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <header className="flex items-center gap-3 px-4 py-2.5 bg-slate-50 border-b">
        <div className="w-9 h-9 rounded-full bg-slate-200 grid place-items-center font-semibold text-slate-600">{(c.nombre || '#')[0].toUpperCase()}</div>
        <div className="min-w-0 flex-1">
          <div className="font-medium truncate">{c.nombre || 'Sin nombre'}</div>
          <div className="text-xs text-slate-500 font-mono">+{c.telefono}</div>
        </div>
        {c.opt_in ? <Insignia color="verde">opt-in</Insignia> : <Insignia color="rojo">sin opt-in</Insignia>}
        {ventana_abierta ? <Insignia color="verde">ventana 24 h abierta</Insignia> : <Insignia color="amarillo">ventana cerrada</Insignia>}
      </header>

      <div className="flex-1 overflow-y-auto wa-fondo p-4">
        {mensajes.map((m) => (
          <Burbuja
            key={m.id}
            saliente={m.direccion === 'saliente'}
            cuerpo={m.contenido}
            estado={m.estado}
            momento={m.creado}
            etiqueta={m.direccion === 'saliente' ? ETIQUETA_ORIGEN[m.origen] : null}
            error={m.estado === 'fallido' ? m.error : null}
          />
        ))}
        <div ref={fin} />
      </div>

      <div className="border-t bg-white p-3 space-y-2">
        <Aviso>{error}</Aviso>
        {ventana_abierta ? (
          <form onSubmit={responder} className="flex gap-2">
            <Input placeholder="Escribe una respuesta…" value={texto} onChange={(e) => setTexto(e.target.value)} />
            <Boton disabled={!texto.trim() || ocupado}>Enviar</Boton>
          </form>
        ) : (
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <span className="text-slate-600 flex-1">
              Han pasado más de 24 h desde el último mensaje del cliente: WhatsApp solo permite retomar con una plantilla aprobada.
            </span>
            <Boton variante="secundario" onClick={() => setModalPlantilla(true)} disabled={!c.opt_in}>Enviar plantilla</Boton>
          </div>
        )}
        {sandbox && (
          <form onSubmit={simular} className="flex gap-2 pt-2 border-t border-dashed">
            <Input placeholder="🧪 Simular mensaje del cliente (prueba: precio, horario, BAJA, ALTA)…" value={simulado} onChange={(e) => setSimulado(e.target.value)} />
            <Boton variante="secundario" disabled={!simulado.trim() || ocupado}>Simular</Boton>
          </form>
        )}
      </div>
      <Modal abierto={modalPlantilla} titulo={`Plantilla para ${c.nombre || c.telefono}`} onCerrar={() => setModalPlantilla(false)}>
        <EnviarPlantilla contacto={c} onListo={() => { setModalPlantilla(false); recargar() }} />
      </Modal>
    </div>
  )
}

export default function Conversaciones() {
  const { id } = useParams()
  const navegar = useNavigate()
  const { datos: sistema } = useApi('/sistema')

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden grid md:grid-cols-[320px_1fr] h-[calc(100vh-7rem)]">
      <div className={`border-r ${id ? 'hidden md:block' : ''}`}>
        <Lista seleccionado={id} />
      </div>
      <div className={id ? '' : 'hidden md:block'}>
        {id ? (
          <>
            <button className="md:hidden text-sm text-wa-700 px-3 py-2" onClick={() => navegar('/conversaciones')}>‹ Volver</button>
            <Hilo key={id} id={id} sandbox={sistema?.modo === 'sandbox'} />
          </>
        ) : (
          <div className="h-full grid place-items-center wa-fondo text-slate-500 text-sm">
            <div className="text-center">
              <div className="text-5xl mb-2">💬</div>
              Selecciona una conversación
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
