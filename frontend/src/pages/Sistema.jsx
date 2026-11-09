import { Fragment, useState } from 'react'
import { useApi } from '../hooks'
import { fechaHora } from '../formato'
import { Card, Encabezado, Insignia, Select, Tabla, Td, Vacio } from '../components/ui'

function Fila({ etiqueta, children }) {
  return (
    <div className="flex justify-between gap-3 py-2 text-sm border-b border-slate-100 last:border-0">
      <span className="text-slate-500">{etiqueta}</span>
      <span className="font-medium text-right">{children}</span>
    </div>
  )
}

const si = (v) => (v ? <Insignia color="verde">sí</Insignia> : <Insignia color="rojo">no</Insignia>)

export default function Sistema() {
  const { datos: s } = useApi('/sistema')
  const [tipo, setTipo] = useState('')
  const { datos: eventos } = useApi(`/webhook-eventos?limite=100${tipo ? `&tipo=${tipo}` : ''}`, { intervalo: 4000 })
  const [abierto, setAbierto] = useState(null)

  return (
    <>
      <Encabezado titulo="Webhook y sistema" subtitulo="Configuración activa y registro de todas las notificaciones recibidas" />
      <div className="grid lg:grid-cols-3 gap-6 items-start">
        <div className="space-y-6">
          <Card titulo="Configuración">
            {s && (
              <>
                <Fila etiqueta="Modo">{s.modo === 'sandbox' ? <Insignia color="amarillo">sandbox</Insignia> : <Insignia color="verde">cloud</Insignia>}</Fila>
                <Fila etiqueta="Versión Graph API">{s.api_version}</Fila>
                <Fila etiqueta="Token configurado">{si(s.token_configurado)}</Fila>
                <Fila etiqueta="Phone Number ID">{si(s.phone_number_id_configurado)}</Fila>
                <Fila etiqueta="Límite de velocidad">{s.rate_limit_mps} msg/s</Fila>
                <Fila etiqueta="Reintentos máximos">{s.max_reintentos}</Fila>
                <Fila etiqueta="Celery">{s.celery_eager ? 'en proceso (eager)' : 'worker + Redis'}</Fila>
                <Fila etiqueta="Ventana de atribución">{s.ventana_atribucion_dias} días</Fila>
              </>
            )}
          </Card>
          <Card titulo="Webhook en Meta">
            <div className="text-sm space-y-2 text-slate-600">
              <p>En <em>App Dashboard → WhatsApp → Configuración → Webhook</em>:</p>
              <div>
                <div className="text-xs text-slate-500">URL de devolución de llamada</div>
                <code className="block bg-slate-100 rounded px-2 py-1 text-xs break-all">https://TU-DOMINIO/webhook</code>
              </div>
              <div>
                <div className="text-xs text-slate-500">Token de verificación</div>
                <code className="block bg-slate-100 rounded px-2 py-1 text-xs">WHATSAPP_VERIFY_TOKEN del .env</code>
              </div>
              <p>Suscribe los campos <code className="text-xs">messages</code> y <code className="text-xs">message_template_status_update</code>.</p>
              <p className="text-xs">Cada POST se valida con HMAC-SHA256 del cuerpo usando el <strong>App Secret</strong> (cabecera <code>X-Hub-Signature-256</code>); los que no coinciden se rechazan con 401.</p>
              <p className="text-xs">En local expón el puerto con <code>ngrok http 5059</code> o <code>cloudflared tunnel</code>.</p>
            </div>
          </Card>
        </div>

        <Card
          titulo="Eventos de webhook recibidos"
          className="lg:col-span-2"
          sinPadding
          accion={
            <div className="w-44">
              <Select value={tipo} onChange={(e) => setTipo(e.target.value)}>
                <option value="">Todos</option>
                <option value="status">Estados de mensaje</option>
                <option value="message">Mensajes entrantes</option>
                <option value="template_status">Estado de plantilla</option>
              </Select>
            </div>
          }
        >
          {eventos?.length === 0 ? <Vacio>No ha llegado ninguna notificación</Vacio> : (
            <div className="max-h-[640px] overflow-y-auto">
              <Tabla columnas={['#', 'Origen', 'Tipo', 'wamid', 'Procesado', 'Recibido']}>
                {eventos?.map((e) => (
                  <Fragment key={e.id}>
                    <tr className="hover:bg-slate-50 cursor-pointer" onClick={() => setAbierto(abierto === e.id ? null : e.id)}>
                      <Td className="tabular-nums text-slate-400">{e.id}</Td>
                      <Td><Insignia color={e.origen === 'meta' ? 'verde' : 'amarillo'}>{e.origen}</Insignia></Td>
                      <Td>{e.tipo}</Td>
                      <Td className="font-mono text-[11px] text-slate-500 max-w-48 truncate" title={e.wamid}>{e.wamid}</Td>
                      <Td>{e.error ? <Insignia color="rojo">error</Insignia> : e.procesado ? <Insignia color="verde">✓</Insignia> : <Insignia>pendiente</Insignia>}</Td>
                      <Td className="text-xs text-slate-500 whitespace-nowrap">{fechaHora(e.recibido_en)}</Td>
                    </tr>
                    {abierto === e.id && (
                      <tr key={`${e.id}-p`}>
                        <td colSpan={6} className="px-4 pb-3">
                          {e.error && <div className="text-xs text-red-600 mb-1">{e.error}</div>}
                          <pre className="text-[11px] bg-slate-900 text-emerald-300 rounded-lg p-3 overflow-x-auto">{JSON.stringify(e.payload, null, 2)}</pre>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </Tabla>
            </div>
          )}
        </Card>
      </div>
    </>
  )
}
