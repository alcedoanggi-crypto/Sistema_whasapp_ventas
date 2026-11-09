import { useState } from 'react'
import { post } from '../api'
import { useApi } from '../hooks'
import { dinero, fechaHora } from '../formato'
import { Aviso, Boton, Campo, Card, Encabezado, Estado, Input, Select, Tabla, Td, Vacio, useAccion } from '../components/ui'

const TIPOS = {
  carrito_abandonado: { nombre: '🛒 Carrito abandonado', campos: ['producto'] },
  pago_pendiente: { nombre: '💳 Pago pendiente', campos: ['monto', 'fecha'] },
  pago_realizado: { nombre: '✅ Pago realizado', campos: [] },
  compra: { nombre: '🛍 Compra', campos: ['producto'], monto: true },
  alta: { nombre: '👋 Alta de cliente', campos: [] },
}

export default function Eventos() {
  const [tipoFiltro, setTipoFiltro] = useState('')
  const { datos: eventos, recargar } = useApi(`/eventos?limite=100${tipoFiltro ? `&tipo=${tipoFiltro}` : ''}`, { intervalo: 5000 })
  const { datos: contactos } = useApi('/contactos?por_pagina=200&opt_in=true')
  const [f, setF] = useState({ telefono: '', tipo: 'carrito_abandonado', referencia: '', datos: {}, monto: '' })
  const [ejecutar, ocupado, error] = useAccion()
  const [ok, setOk] = useState(null)
  const nombrePorId = Object.fromEntries((contactos?.items || []).map((c) => [c.id, c.nombre || c.telefono]))

  async function enviar(e) {
    e.preventDefault()
    setOk(null)
    const r = await ejecutar(() =>
      post('/eventos', { ...f, referencia: f.referencia || null, monto: f.monto ? Number(f.monto) : null }),
    )
    if (r) {
      setOk(
        r.disparo_estado === 'pendiente'
          ? `Evento registrado. Mensaje programado para ${fechaHora(r.disparo_en)}.`
          : r.disparo_estado === 'enviado'
            ? 'Evento registrado y mensaje enviado.'
            : `Evento registrado (${r.disparo_estado}${r.disparo_detalle ? ': ' + r.disparo_detalle : ''}).`,
      )
      recargar()
    }
  }

  const tipo = TIPOS[f.tipo]

  return (
    <>
      <Encabezado
        titulo="Eventos de tienda"
        subtitulo="Lo que tu e-commerce/CRM envía a POST /api/eventos (con X-API-Key) para alimentar los disparadores"
      />
      <div className="grid lg:grid-cols-3 gap-6 items-start">
        <Card titulo="Simular evento">
          <form onSubmit={enviar} className="space-y-3">
            <Campo etiqueta="Contacto">
              <Select value={f.telefono} onChange={(e) => setF({ ...f, telefono: e.target.value })} required>
                <option value="">Selecciona…</option>
                {contactos?.items.map((c) => <option key={c.id} value={c.telefono}>{c.nombre || c.telefono}</option>)}
              </Select>
            </Campo>
            <Campo etiqueta="Tipo de evento">
              <Select value={f.tipo} onChange={(e) => setF({ ...f, tipo: e.target.value, datos: {} })}>
                {Object.entries(TIPOS).map(([k, v]) => <option key={k} value={k}>{v.nombre}</option>)}
              </Select>
            </Campo>
            <Campo etiqueta="Referencia" ayuda="ID del carrito / pedido / factura">
              <Input value={f.referencia} onChange={(e) => setF({ ...f, referencia: e.target.value })} placeholder="pedido-1042" />
            </Campo>
            {tipo.campos.map((c) => (
              <Campo key={c} etiqueta={<>Dato <span className="font-mono">{c}</span> (variable de la plantilla)</>}>
                <Input value={f.datos[c] || ''} onChange={(e) => setF({ ...f, datos: { ...f.datos, [c]: e.target.value } })} />
              </Campo>
            ))}
            {tipo.monto && (
              <Campo etiqueta="Monto de la compra (USD)" ayuda="Se atribuye a la última campaña entregada (ventana de atribución)">
                <Input type="number" step="0.01" value={f.monto} onChange={(e) => setF({ ...f, monto: e.target.value })} />
              </Campo>
            )}
            <Aviso>{error}</Aviso>
            <Aviso tipo="ok">{ok}</Aviso>
            <Boton className="w-full" disabled={ocupado}>Registrar evento</Boton>
          </form>
        </Card>

        <Card
          titulo="Historial"
          className="lg:col-span-2"
          sinPadding
          accion={
            <div className="w-48">
              <Select value={tipoFiltro} onChange={(e) => setTipoFiltro(e.target.value)}>
                <option value="">Todos los tipos</option>
                {Object.entries(TIPOS).map(([k, v]) => <option key={k} value={k}>{v.nombre}</option>)}
              </Select>
            </div>
          }
        >
          {eventos?.length === 0 ? <Vacio>Sin eventos</Vacio> : (
            <Tabla columnas={['Evento', 'Contacto', 'Datos', 'Mensaje', 'Fecha']}>
              {eventos?.map((e) => (
                <tr key={e.id}>
                  <Td>
                    <div className="font-medium whitespace-nowrap">{TIPOS[e.tipo]?.nombre || e.tipo}</div>
                    {e.referencia && <div className="text-xs text-slate-500">{e.referencia}</div>}
                  </Td>
                  <Td>{nombrePorId[e.contacto_id] || `#${e.contacto_id}`}</Td>
                  <Td className="text-xs text-slate-600">
                    {Object.entries(e.datos || {}).map(([k, v]) => <div key={k}>{k}: {String(v)}</div>)}
                    {e.monto != null && <div className="font-medium">{dinero(e.monto)}{e.campana_id && <span className="text-emerald-700"> · campaña #{e.campana_id}</span>}</div>}
                  </Td>
                  <Td>
                    <Estado valor={e.disparo_estado} />
                    {e.disparo_estado === 'pendiente' && <div className="text-[11px] text-slate-500 mt-0.5">{fechaHora(e.disparo_en)}</div>}
                    {e.disparo_detalle && <div className="text-[11px] text-slate-500 mt-0.5 max-w-48">{e.disparo_detalle}</div>}
                  </Td>
                  <Td className="text-xs text-slate-500 whitespace-nowrap">{fechaHora(e.creado)}</Td>
                </tr>
              ))}
            </Tabla>
          )}
        </Card>
      </div>
    </>
  )
}
