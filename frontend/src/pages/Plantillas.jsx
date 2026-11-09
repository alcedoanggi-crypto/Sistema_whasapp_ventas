import { Link } from 'react-router-dom'
import { useApi } from '../hooks'
import { fechaHora } from '../formato'
import { Boton, Cargando, Encabezado, Estado, Insignia, Vacio } from '../components/ui'
import { Burbuja } from '../components/VistaWhatsApp'
import { renderizar } from '../formato'

export default function Plantillas() {
  const { datos, cargando } = useApi('/plantillas')

  return (
    <>
      <Encabezado
        titulo="Plantillas de mensaje"
        subtitulo="WhatsApp solo permite iniciar conversaciones con plantillas aprobadas por Meta"
      >
        <Link to="/plantillas/nueva"><Boton>+ Nueva plantilla</Boton></Link>
      </Encabezado>
      {cargando && !datos ? <Cargando /> : datos?.length === 0 ? <Vacio>Aún no hay plantillas</Vacio> : (
        <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {datos?.map((p) => (
            <Link
              key={p.id}
              to={`/plantillas/${p.id}`}
              className="bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md hover:border-wa-500 transition flex flex-col"
            >
              <div className="p-4 flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="font-mono text-sm font-semibold truncate">{p.nombre}</div>
                  <div className="flex gap-1.5 mt-1">
                    <Insignia color={p.categoria === 'MARKETING' ? 'morado' : 'azul'}>{p.categoria}</Insignia>
                    <Insignia>{p.idioma}</Insignia>
                  </div>
                </div>
                <Estado valor={p.estado} />
              </div>
              <div className="wa-fondo px-3 pt-3 pb-1 flex-1">
                <Burbuja
                  encabezado={renderizar(p.encabezado, p.ejemplos)}
                  cuerpo={renderizar(p.cuerpo, p.ejemplos)}
                  pie={p.pie}
                  botones={p.botones}
                  momento={p.actualizado}
                />
              </div>
              <div className="px-4 py-2 text-xs text-slate-500 flex justify-between border-t border-slate-100">
                <span>{p.variables.length ? p.variables.map((v) => `{{${v}}}`).join(' ') : 'sin variables'}</span>
                <span>{fechaHora(p.actualizado)}</span>
              </div>
              {p.motivo_rechazo && <div className="px-4 pb-2 text-xs text-red-600">Rechazo: {p.motivo_rechazo}</div>}
            </Link>
          ))}
        </div>
      )}
    </>
  )
}
