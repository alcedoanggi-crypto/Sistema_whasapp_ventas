import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useApi } from '../hooks'
import { dinero, fecha, pct } from '../formato'
import { Card, Cargando, Encabezado, Estado, Select, Tabla, Td, Vacio, Aviso } from '../components/ui'

function Kpi({ titulo, valor, detalle, color = 'text-slate-900' }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{titulo}</div>
      <div className={`text-2xl font-bold mt-1 tabular-nums ${color}`}>{valor}</div>
      {detalle && <div className="text-xs text-slate-500 mt-0.5">{detalle}</div>}
    </div>
  )
}

export default function Dashboard() {
  const [dias, setDias] = useState(30)
  const { datos, error, cargando } = useApi(`/dashboard?dias=${dias}`, { intervalo: 10000 })

  return (
    <>
      <Encabezado titulo="Dashboard" subtitulo="Mensajes proactivos (plantillas) del período: campañas y disparadores">
        <div className="w-40">
          <Select value={dias} onChange={(e) => setDias(Number(e.target.value))}>
            <option value={7}>Últimos 7 días</option>
            <option value={30}>Últimos 30 días</option>
            <option value={90}>Últimos 90 días</option>
            <option value={365}>Último año</option>
          </Select>
        </div>
      </Encabezado>
      <Aviso>{error}</Aviso>
      {cargando && !datos ? (
        <Cargando />
      ) : datos && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Kpi titulo="Enviados" valor={datos.kpis.enviados} detalle={`${datos.kpis.fallidos} fallidos`} />
            <Kpi titulo="Tasa de entrega" valor={pct(datos.kpis.tasa_entrega)} detalle={`${datos.kpis.entregados} entregados`} color="text-wa-700" />
            <Kpi titulo="Tasa de lectura" valor={pct(datos.kpis.tasa_lectura)} detalle={`${datos.kpis.leidos} leídos`} color="text-sky-600" />
            <Kpi titulo="Tasa de respuesta" valor={pct(datos.kpis.tasa_respuesta)} detalle={`${datos.kpis.respondidos} respondidos`} color="text-violet-600" />
            <Kpi titulo="Conversiones" valor={datos.kpis.conversiones} detalle="compras atribuidas a campañas" />
            <Kpi titulo="Ingresos atribuidos" valor={dinero(datos.kpis.ingresos)} color="text-emerald-700" />
            <Kpi titulo="Contactos con opt-in" valor={`${datos.contactos.con_opt_in} / ${datos.contactos.total}`} detalle={`${datos.contactos.bajas_periodo} bajas en el período`} />
            <Kpi titulo="Mensajes recibidos" valor={datos.kpis.mensajes_recibidos} detalle="respuestas de clientes" />
          </div>

          <Card titulo="Embudo diario">
            {datos.serie.length === 0 ? (
              <Vacio>Sin envíos en el período.</Vacio>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={datos.serie} margin={{ left: -20, right: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="dia" tickFormatter={(d) => d.slice(5)} fontSize={12} />
                  <YAxis allowDecimals={false} fontSize={12} />
                  <Tooltip labelFormatter={(d) => fecha(d + 'T12:00:00')} />
                  <Legend />
                  <Area type="monotone" dataKey="enviados" name="Enviados" stroke="#94a3b8" fill="#cbd5e1" fillOpacity={0.4} />
                  <Area type="monotone" dataKey="entregados" name="Entregados" stroke="#128c7e" fill="#25d366" fillOpacity={0.25} />
                  <Area type="monotone" dataKey="leidos" name="Leídos" stroke="#0284c7" fill="#38bdf8" fillOpacity={0.25} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </Card>

          <div className="grid lg:grid-cols-5 gap-6">
            <Card titulo="Conversión por campaña" className="lg:col-span-2">
              {datos.campanas.length === 0 ? (
                <Vacio>Aún no hay campañas lanzadas.</Vacio>
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={datos.campanas.map((c) => ({ ...c, nombre: c.nombre.slice(0, 18) }))} layout="vertical" margin={{ left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis type="number" unit="%" fontSize={12} />
                    <YAxis type="category" dataKey="nombre" width={110} fontSize={11} />
                    <Tooltip formatter={(v) => `${v}%`} />
                    <Legend />
                    <Bar dataKey="tasa_lectura" name="Lectura" fill="#38bdf8" />
                    <Bar dataKey="tasa_conversion" name="Conversión" fill="#128c7e" />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
            <Card titulo="Últimas campañas" className="lg:col-span-3" sinPadding>
              <Tabla columnas={['Campaña', 'Estado', 'Entrega', 'Lectura', 'Respuesta', 'Conv.', 'Ingresos']}>
                {datos.campanas.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50">
                    <Td>
                      <Link to={`/campanas/${c.id}`} className="font-medium text-wa-700 hover:underline">{c.nombre}</Link>
                      <div className="text-xs text-slate-500">{fecha(c.iniciada)}</div>
                    </Td>
                    <Td><Estado valor={c.estado} /></Td>
                    <Td className="tabular-nums">{pct(c.tasa_entrega)}</Td>
                    <Td className="tabular-nums">{pct(c.tasa_lectura)}</Td>
                    <Td className="tabular-nums">{pct(c.tasa_respuesta)}</Td>
                    <Td className="tabular-nums">{c.conversiones ?? 0}</Td>
                    <Td className="tabular-nums">{dinero(c.ingresos)}</Td>
                  </tr>
                ))}
              </Tabla>
            </Card>
          </div>
        </div>
      )}
    </>
  )
}
