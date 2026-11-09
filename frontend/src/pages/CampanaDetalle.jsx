import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { post } from '../api'
import { useApi } from '../hooks'
import { dinero, fechaHora, pct } from '../formato'
import { Aviso, Boton, Card, Cargando, Encabezado, Estado, Input, Insignia, Tabla, Td, Vacio, useAccion } from '../components/ui'

function Paso({ titulo, valor, total, color }) {
  const ancho = total ? Math.max(2, (100 * valor) / total) : 0
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span>{titulo}</span>
        <span className="tabular-nums font-medium">{valor}</span>
      </div>
      <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${ancho}%` }} />
      </div>
    </div>
  )
}

export default function CampanaDetalle() {
  const { id } = useParams()
  const { datos: c, recargar } = useApi(`/campanas/${id}`, { intervalo: 3000 })
  const [ejecutar, ocupado, error] = useAccion()
  const [fecha, setFecha] = useState('')

  if (!c) return <Cargando />
  const m = c.metricas || { total: 0, en_cola: 0, enviados: 0, entregados: 0, leidos: 0, fallidos: 0, respondidos: 0, conversiones: 0, ingresos: 0 }
  const editable = ['BORRADOR', 'PROGRAMADA'].includes(c.estado)

  const accion = async (ruta, cuerpo) => {
    if (await ejecutar(() => post(`/campanas/${id}/${ruta}`, cuerpo))) recargar()
  }

  return (
    <>
      <Encabezado titulo={c.nombre} subtitulo={<>Plantilla <span className="font-mono">{c.plantilla}</span> · creada {fechaHora(c.creado)}</>}>
        <Estado valor={c.estado} />
      </Encabezado>
      <div className="space-y-6">
        {editable && c.errores.length > 0 && <Aviso tipo="alerta">No se puede lanzar: {c.errores.join(' · ')}</Aviso>}
        <Aviso>{error}</Aviso>
        <div className="flex flex-wrap gap-2 items-center">
          {editable && (
            <>
              <Boton onClick={() => confirm(`¿Enviar ahora a ${c.audiencia_estimada} contactos?`) && accion('lanzar')} disabled={ocupado || c.errores.length > 0}>
                ▶ Lanzar ahora ({c.audiencia_estimada})
              </Boton>
              <div className="flex gap-2 items-center">
                <Input type="datetime-local" value={fecha} onChange={(e) => setFecha(e.target.value)} />
                <Boton variante="secundario" disabled={!fecha || ocupado} onClick={() => accion('programar', { programada_para: new Date(fecha).toISOString() })}>
                  Programar
                </Boton>
              </div>
            </>
          )}
          {!['COMPLETADA', 'CANCELADA'].includes(c.estado) && (
            <Boton variante="peligro" onClick={() => confirm('¿Cancelar la campaña? Lo que aún esté en cola no se enviará.') && accion('cancelar')} disabled={ocupado}>
              Cancelar
            </Boton>
          )}
        </div>

        <div className="grid md:grid-cols-4 gap-4 text-sm">
          <Card><div className="text-slate-500 text-xs uppercase">Programada</div><div className="font-medium mt-1">{fechaHora(c.programada_para)}</div></Card>
          <Card><div className="text-slate-500 text-xs uppercase">Iniciada</div><div className="font-medium mt-1">{fechaHora(c.iniciada)}</div></Card>
          <Card><div className="text-slate-500 text-xs uppercase">Finalizada</div><div className="font-medium mt-1">{fechaHora(c.finalizada)}</div></Card>
          <Card>
            <div className="text-slate-500 text-xs uppercase">Segmento</div>
            <div className="mt-1 flex flex-wrap gap-1">
              {c.segmento.etiquetas?.length ? c.segmento.etiquetas.map((e) => <Insignia key={e}>{e}</Insignia>) : 'Todos con opt-in'}
            </div>
          </Card>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          <Card titulo="Embudo">
            <div className="space-y-3">
              <Paso titulo="Destinatarios" valor={m.total} total={m.total} color="bg-slate-400" />
              <Paso titulo="En cola" valor={m.en_cola} total={m.total} color="bg-slate-300" />
              <Paso titulo="Enviados" valor={m.enviados} total={m.total} color="bg-sky-300" />
              <Paso titulo="Entregados" valor={m.entregados} total={m.total} color="bg-wa-500" />
              <Paso titulo="Leídos" valor={m.leidos} total={m.total} color="bg-sky-500" />
              <Paso titulo="Respondidos" valor={m.respondidos} total={m.total} color="bg-violet-500" />
              <Paso titulo="Fallidos" valor={m.fallidos} total={m.total} color="bg-red-400" />
            </div>
            <div className="grid grid-cols-2 gap-3 mt-5 pt-4 border-t text-sm">
              <div><div className="text-xs text-slate-500">Entrega</div><div className="font-semibold">{pct(m.tasa_entrega)}</div></div>
              <div><div className="text-xs text-slate-500">Lectura</div><div className="font-semibold">{pct(m.tasa_lectura)}</div></div>
              <div><div className="text-xs text-slate-500">Respuesta</div><div className="font-semibold">{pct(m.tasa_respuesta)}</div></div>
              <div><div className="text-xs text-slate-500">Conversión</div><div className="font-semibold">{pct(m.tasa_conversion)}</div></div>
              <div className="col-span-2"><div className="text-xs text-slate-500">{m.conversiones} compras atribuidas</div><div className="font-semibold text-emerald-700">{dinero(m.ingresos)}</div></div>
            </div>
          </Card>
          <Card titulo="Mensajes" className="lg:col-span-2" sinPadding>
            {c.mensajes.length === 0 ? <Vacio>Sin mensajes todavía</Vacio> : (
              <div className="max-h-[560px] overflow-y-auto">
                <Tabla columnas={['Contacto', 'Estado', 'Intentos', 'Enviado', 'Leído', 'Detalle']}>
                  {c.mensajes.map((x) => (
                    <tr key={x.id}>
                      <Td><Link className="text-wa-700 hover:underline" to={`/conversaciones/${x.contacto_id}`}>{x.contacto}</Link></Td>
                      <Td><Estado valor={x.estado} /></Td>
                      <Td className="tabular-nums">{x.intentos}</Td>
                      <Td className="text-xs text-slate-500 whitespace-nowrap">{fechaHora(x.enviado_en)}</Td>
                      <Td className="text-xs text-slate-500 whitespace-nowrap">{fechaHora(x.leido_en)}</Td>
                      <Td className="text-xs text-red-600 max-w-64 truncate" title={x.error}>{x.error}</Td>
                    </tr>
                  ))}
                </Tabla>
              </div>
            )}
          </Card>
        </div>
      </div>
    </>
  )
}
