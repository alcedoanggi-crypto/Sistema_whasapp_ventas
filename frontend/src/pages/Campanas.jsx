import { Link } from 'react-router-dom'
import { useApi } from '../hooks'
import { fechaHora, pct } from '../formato'
import { Boton, Card, Cargando, Encabezado, Estado, Insignia, Tabla, Td, Vacio } from '../components/ui'

function Progreso({ m }) {
  if (!m?.total) return <span className="text-slate-400">—</span>
  const ancho = (n) => `${(100 * n) / m.total}%`
  return (
    <div className="w-36">
      <div className="flex h-2 rounded-full overflow-hidden bg-slate-100">
        <div className="bg-sky-500" style={{ width: ancho(m.leidos) }} />
        <div className="bg-wa-500" style={{ width: ancho(m.entregados - m.leidos) }} />
        <div className="bg-slate-400" style={{ width: ancho(m.enviados - m.entregados) }} />
        <div className="bg-red-400" style={{ width: ancho(m.fallidos) }} />
      </div>
      <div className="text-[11px] text-slate-500 mt-0.5">
        {m.total - m.en_cola}/{m.total} procesados
      </div>
    </div>
  )
}

export default function Campanas() {
  const { datos, cargando } = useApi('/campanas', { intervalo: 5000 })

  return (
    <>
      <Encabezado titulo="Campañas" subtitulo="Envíos masivos a un segmento de contactos con opt-in, con plantilla aprobada">
        <Link to="/campanas/nueva"><Boton>+ Nueva campaña</Boton></Link>
      </Encabezado>
      <Card sinPadding>
        {cargando && !datos ? <Cargando /> : datos?.length === 0 ? <Vacio>Aún no hay campañas</Vacio> : (
          <Tabla columnas={['Campaña', 'Plantilla', 'Segmento', 'Estado', 'Programada / iniciada', 'Progreso', 'Lectura', 'Conv.']}>
            {datos?.map((c) => (
              <tr key={c.id} className="hover:bg-slate-50">
                <Td><Link to={`/campanas/${c.id}`} className="font-medium text-wa-700 hover:underline">{c.nombre}</Link></Td>
                <Td className="font-mono text-xs">{c.plantilla}</Td>
                <Td>
                  {c.segmento.etiquetas?.length ? (
                    <div className="flex flex-wrap gap-1">
                      {c.segmento.etiquetas.map((e) => <Insignia key={e}>{e}</Insignia>)}
                      {c.segmento.etiquetas.length > 1 && <span className="text-[11px] text-slate-500">({c.segmento.modo})</span>}
                    </div>
                  ) : <span className="text-xs text-slate-500">Todos con opt-in</span>}
                </Td>
                <Td><Estado valor={c.estado} /></Td>
                <Td className="text-xs text-slate-500 whitespace-nowrap">{fechaHora(c.iniciada || c.programada_para)}</Td>
                <Td><Progreso m={c.metricas} /></Td>
                <Td className="tabular-nums">{c.metricas ? pct(c.metricas.tasa_lectura) : '—'}</Td>
                <Td className="tabular-nums">{c.metricas?.conversiones ?? '—'}</Td>
              </tr>
            ))}
          </Tabla>
        )}
      </Card>
    </>
  )
}
