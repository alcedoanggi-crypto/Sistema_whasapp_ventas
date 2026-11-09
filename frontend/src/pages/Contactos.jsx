import { useState } from 'react'
import { Link } from 'react-router-dom'
import { del, patch, post } from '../api'
import { useApi } from '../hooks'
import { fechaHora } from '../formato'
import {
  Aviso, Boton, Campo, Card, Cargando, Encabezado, Estado, Input, Insignia, Modal, Select, Tabla, Td, Textarea, Vacio, useAccion,
} from '../components/ui'

const VACIO = { telefono: '', nombre: '', email: '', etiquetas: '', opt_in: true, origen_consentimiento: 'formulario_web', evidencia: '' }

function FormContacto({ origenes, onListo }) {
  const [f, setF] = useState(VACIO)
  const [ejecutar, ocupado, error] = useAccion()
  const cambiar = (k) => (e) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  async function guardar(e) {
    e.preventDefault()
    const r = await ejecutar(() =>
      post('/contactos', {
        ...f,
        email: f.email || null,
        etiquetas: f.etiquetas.split(','),
        origen_consentimiento: f.opt_in ? f.origen_consentimiento : null,
        evidencia: f.evidencia || null,
      }),
    )
    if (r) onListo()
  }

  return (
    <form onSubmit={guardar} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <Campo etiqueta="Teléfono (internacional)" ayuda="Código de país sin +, ej. 584121234567">
          <Input value={f.telefono} onChange={cambiar('telefono')} required />
        </Campo>
        <Campo etiqueta="Nombre">
          <Input value={f.nombre} onChange={cambiar('nombre')} />
        </Campo>
      </div>
      <Campo etiqueta="Email">
        <Input type="email" value={f.email} onChange={cambiar('email')} />
      </Campo>
      <Campo etiqueta="Etiquetas (segmentos)" ayuda="Separadas por coma: vip, calzado, caracas">
        <Input value={f.etiquetas} onChange={cambiar('etiquetas')} />
      </Campo>
      <div className="rounded-lg border border-slate-200 p-3 space-y-3 bg-slate-50">
        <label className="flex items-center gap-2 text-sm font-medium">
          <input type="checkbox" checked={f.opt_in} onChange={cambiar('opt_in')} className="accent-wa-700 w-4 h-4" />
          El cliente dio su consentimiento (opt-in) para recibir mensajes por WhatsApp
        </label>
        {f.opt_in && (
          <>
            <Campo etiqueta="Origen del consentimiento">
              <Select value={f.origen_consentimiento} onChange={cambiar('origen_consentimiento')}>
                {Object.entries(origenes || {})
                  .filter(([k]) => !['palabra_clave', 'manual'].includes(k))
                  .map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
              </Select>
            </Campo>
            <Campo etiqueta="Evidencia" ayuda="Ej.: casilla marcada en el formulario /registro, IP 190.x.x.x">
              <Textarea rows={2} value={f.evidencia} onChange={cambiar('evidencia')} />
            </Campo>
            <p className="text-xs text-slate-500">Al guardarlo se dispara el mensaje de bienvenida si esa automatización está activa.</p>
          </>
        )}
      </div>
      <Aviso>{error}</Aviso>
      <div className="flex justify-end">
        <Boton disabled={ocupado}>Guardar contacto</Boton>
      </div>
    </form>
  )
}

function DetalleContacto({ id, origenes, onCambio }) {
  const { datos, recargar } = useApi(`/contactos/${id}`)
  const [ejecutar, ocupado, error] = useAccion()
  const [etiquetas, setEtiquetas] = useState(null)
  if (!datos) return <Cargando />
  const c = datos.contacto

  async function consentimiento(opt_in) {
    const evidencia = opt_in ? prompt('Evidencia del nuevo consentimiento (obligatoria para auditoría):') : 'Baja manual desde el panel'
    if (opt_in && !evidencia) return
    if (await ejecutar(() => post(`/contactos/${id}/consentimiento`, { opt_in, origen: 'manual', evidencia }))) {
      recargar(); onCambio()
    }
  }
  async function guardarEtiquetas() {
    if (await ejecutar(() => patch(`/contactos/${id}`, { etiquetas: etiquetas.split(',') }))) {
      setEtiquetas(null); recargar(); onCambio()
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-sm">+{c.telefono}</span>
        {c.opt_in ? <Insignia color="verde">opt-in vigente</Insignia> : <Insignia color="rojo">sin consentimiento</Insignia>}
        <Link to={`/conversaciones/${c.id}`} className="ml-auto text-sm text-wa-700 hover:underline">Abrir conversación →</Link>
      </div>
      <div>
        <div className="text-xs font-medium text-slate-500 mb-1">Etiquetas</div>
        {etiquetas === null ? (
          <div className="flex flex-wrap gap-1 items-center">
            {c.etiquetas.map((e) => <Insignia key={e}>{e}</Insignia>)}
            <button className="text-xs text-wa-700 hover:underline ml-1" onClick={() => setEtiquetas(c.etiquetas.join(', '))}>editar</button>
          </div>
        ) : (
          <div className="flex gap-2">
            <Input value={etiquetas} onChange={(e) => setEtiquetas(e.target.value)} />
            <Boton onClick={guardarEtiquetas} disabled={ocupado}>OK</Boton>
          </div>
        )}
      </div>
      <div>
        <div className="flex items-center justify-between mb-1">
          <div className="text-xs font-medium text-slate-500">Historial de consentimiento (auditoría)</div>
          {c.opt_in ? (
            <Boton variante="secundario" className="!py-1 text-xs" onClick={() => consentimiento(false)} disabled={ocupado}>Dar de baja</Boton>
          ) : (
            <Boton variante="secundario" className="!py-1 text-xs" onClick={() => consentimiento(true)} disabled={ocupado}>Registrar opt-in</Boton>
          )}
        </div>
        <ul className="border rounded-lg divide-y text-sm">
          {datos.consentimientos.length === 0 && <li className="px-3 py-2 text-slate-400">Sin registros</li>}
          {datos.consentimientos.map((x) => (
            <li key={x.id} className="px-3 py-2 flex gap-3">
              <Insignia color={x.tipo === 'opt_in' ? 'verde' : 'rojo'}>{x.tipo}</Insignia>
              <div className="flex-1 min-w-0">
                <div>{origenes?.[x.origen] || x.origen}</div>
                {x.detalle && <div className="text-xs text-slate-500 truncate" title={x.detalle}>{x.detalle}</div>}
              </div>
              <div className="text-xs text-slate-500 whitespace-nowrap">{fechaHora(x.fecha)}</div>
            </li>
          ))}
        </ul>
      </div>
      {datos.eventos.length > 0 && (
        <div>
          <div className="text-xs font-medium text-slate-500 mb-1">Eventos de tienda</div>
          <ul className="border rounded-lg divide-y text-sm">
            {datos.eventos.map((e) => (
              <li key={e.id} className="px-3 py-2 flex gap-3 items-center">
                <span className="flex-1">{e.tipo.replaceAll('_', ' ')} {e.referencia && <span className="text-slate-400">· {e.referencia}</span>}</span>
                <Estado valor={e.disparo_estado} />
                <span className="text-xs text-slate-500">{fechaHora(e.creado)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <Aviso>{error}</Aviso>
    </div>
  )
}

export default function Contactos() {
  const [q, setQ] = useState('')
  const [etiqueta, setEtiqueta] = useState('')
  const [optIn, setOptIn] = useState('')
  const [pagina, setPagina] = useState(1)
  const [nuevo, setNuevo] = useState(false)
  const [detalle, setDetalle] = useState(null)
  const params = new URLSearchParams({ pagina, por_pagina: 25, ...(q && { q }), ...(etiqueta && { etiqueta }), ...(optIn && { opt_in: optIn }) })
  const { datos, cargando, recargar } = useApi(`/contactos?${params}`)
  const { datos: etiquetas, recargar: recargarEtiquetas } = useApi('/contactos/etiquetas')
  const { datos: origenes } = useApi('/contactos/origenes')
  const paginas = datos ? Math.max(1, Math.ceil(datos.total / 25)) : 1

  async function eliminar(c) {
    if (!confirm(`¿Eliminar a ${c.nombre || c.telefono} y todo su historial?`)) return
    await del(`/contactos/${c.id}`)
    recargar()
  }

  return (
    <>
      <Encabezado titulo="Contactos" subtitulo="Solo los contactos con opt-in vigente reciben campañas y mensajes automáticos">
        <Boton onClick={() => setNuevo(true)}>+ Nuevo contacto</Boton>
      </Encabezado>
      <Card sinPadding>
        <div className="flex flex-wrap gap-3 p-4 border-b border-slate-100">
          <div className="flex-1 min-w-48">
            <Input placeholder="Buscar por nombre, teléfono o email…" value={q} onChange={(e) => { setQ(e.target.value); setPagina(1) }} />
          </div>
          <div className="w-44">
            <Select value={etiqueta} onChange={(e) => { setEtiqueta(e.target.value); setPagina(1) }}>
              <option value="">Todas las etiquetas</option>
              {etiquetas?.map((e) => <option key={e.etiqueta} value={e.etiqueta}>{e.etiqueta} ({e.contactos})</option>)}
            </Select>
          </div>
          <div className="w-44">
            <Select value={optIn} onChange={(e) => { setOptIn(e.target.value); setPagina(1) }}>
              <option value="">Todos</option>
              <option value="true">Con opt-in</option>
              <option value="false">Sin opt-in / baja</option>
            </Select>
          </div>
        </div>
        {cargando && !datos ? <Cargando /> : datos?.items.length === 0 ? <Vacio>Sin contactos</Vacio> : (
          <Tabla columnas={['Contacto', 'Teléfono', 'Etiquetas', 'Consentimiento', 'Último mensaje', '']}>
            {datos?.items.map((c) => (
              <tr key={c.id} className="hover:bg-slate-50 cursor-pointer" onClick={() => setDetalle(c)}>
                <Td>
                  <div className="font-medium">{c.nombre || '—'}</div>
                  <div className="text-xs text-slate-500">{c.email}</div>
                </Td>
                <Td className="font-mono text-xs">+{c.telefono}</Td>
                <Td><div className="flex flex-wrap gap-1">{c.etiquetas.map((e) => <Insignia key={e}>{e}</Insignia>)}</div></Td>
                <Td>
                  {c.opt_in ? (
                    <div><Insignia color="verde">opt-in</Insignia><div className="text-xs text-slate-500 mt-0.5">{origenes?.[c.opt_in_origen] || c.opt_in_origen} · {fechaHora(c.opt_in_fecha)}</div></div>
                  ) : c.opt_out_fecha ? (
                    <div><Insignia color="rojo">baja</Insignia><div className="text-xs text-slate-500 mt-0.5">{fechaHora(c.opt_out_fecha)}</div></div>
                  ) : <Insignia>sin opt-in</Insignia>}
                </Td>
                <Td className="text-xs text-slate-500 whitespace-nowrap">{fechaHora(c.ultimo_mensaje)}</Td>
                <Td onClick={(e) => e.stopPropagation()}>
                  <button className="text-slate-400 hover:text-red-600 text-sm" onClick={() => eliminar(c)} title="Eliminar">🗑</button>
                </Td>
              </tr>
            ))}
          </Tabla>
        )}
        <div className="flex items-center justify-between p-3 text-sm text-slate-500 border-t border-slate-100">
          <span>{datos?.total ?? 0} contactos</span>
          <div className="flex gap-2 items-center">
            <Boton variante="secundario" disabled={pagina <= 1} onClick={() => setPagina(pagina - 1)}>‹</Boton>
            <span>{pagina} / {paginas}</span>
            <Boton variante="secundario" disabled={pagina >= paginas} onClick={() => setPagina(pagina + 1)}>›</Boton>
          </div>
        </div>
      </Card>

      <Modal abierto={nuevo} titulo="Nuevo contacto" onCerrar={() => setNuevo(false)}>
        <FormContacto origenes={origenes} onListo={() => { setNuevo(false); recargar(); recargarEtiquetas() }} />
      </Modal>
      <Modal abierto={!!detalle} titulo={detalle?.nombre || 'Contacto'} onCerrar={() => setDetalle(null)} ancho="max-w-2xl">
        {detalle && <DetalleContacto id={detalle.id} origenes={origenes} onCambio={() => { recargar(); recargarEtiquetas() }} />}
      </Modal>
    </>
  )
}
