import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { post } from '../api'
import { useApi } from '../hooks'
import { extraerVariables, renderizar } from '../formato'
import { Aviso, Boton, Campo, Card, Encabezado, Input, Select, useAccion } from '../components/ui'
import { Burbuja, Telefono } from '../components/VistaWhatsApp'

// Estas se completan con los datos de cada contacto al enviar.
const DE_CONTACTO = ['nombre', 'nombre_completo', 'telefono']

function enUnaHora() {
  const d = new Date(Date.now() + 60 * 60 * 1000)
  d.setSeconds(0, 0)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}

export default function CampanaNueva() {
  const navegar = useNavigate()
  const { datos: plantillas } = useApi('/plantillas?estado=APROBADA')
  const { datos: etiquetas } = useApi('/contactos/etiquetas')
  const [nombre, setNombre] = useState('')
  const [plantillaId, setPlantillaId] = useState('')
  const [segmento, setSegmento] = useState({ etiquetas: [], modo: 'cualquiera' })
  const [variables, setVariables] = useState({})
  const [cuando, setCuando] = useState('ahora') // ahora | programar | borrador
  const [fecha, setFecha] = useState(enUnaHora())
  const [audiencia, setAudiencia] = useState(null)
  const [ejecutar, ocupado, error] = useAccion()

  const plantilla = plantillas?.find((p) => p.id === Number(plantillaId))
  const requeridas = useMemo(
    () => (plantilla ? extraerVariables(plantilla.encabezado, plantilla.cuerpo).filter((v) => !DE_CONTACTO.includes(v)) : []),
    [plantilla],
  )

  useEffect(() => {
    post('/campanas/segmento/contar', segmento).then((r) => setAudiencia(r.contactos)).catch(() => setAudiencia(null))
  }, [segmento])

  useEffect(() => {
    if (plantilla) setVariables(Object.fromEntries(requeridas.map((v) => [v, plantilla.ejemplos?.[v] || ''])))
  }, [plantilla, requeridas])

  function alternarEtiqueta(e) {
    const ya = segmento.etiquetas.includes(e)
    setSegmento({ ...segmento, etiquetas: ya ? segmento.etiquetas.filter((x) => x !== e) : [...segmento.etiquetas, e] })
  }

  async function crear(e) {
    e.preventDefault()
    const r = await ejecutar(async () => {
      const c = await post('/campanas', {
        nombre,
        plantilla_id: Number(plantillaId),
        segmento,
        variables,
        programada_para: cuando === 'programar' ? new Date(fecha).toISOString() : null,
      })
      if (cuando === 'ahora') await post(`/campanas/${c.id}/lanzar`)
      return c
    })
    if (r) navegar(`/campanas/${r.id}`)
  }

  const valoresVista = { nombre: 'Ana', nombre_completo: 'Ana Pérez', ...variables }

  return (
    <>
      <Encabezado titulo="Nueva campaña" subtitulo="Segmento → plantilla → variables → cuándo enviar" />
      <form onSubmit={crear} className="grid lg:grid-cols-[1fr_380px] gap-6 items-start">
        <div className="space-y-6">
          <Card titulo="1 · Nombre">
            <Input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Black Friday clientes VIP" required />
          </Card>

          <Card titulo="2 · Segmento" accion={
            <span className="text-sm">
              Audiencia: <strong className="text-wa-700 tabular-nums">{audiencia ?? '…'}</strong> contactos con opt-in
            </span>
          }>
            <p className="text-sm text-slate-500 mb-3">
              Sin etiquetas = todos los contactos con consentimiento vigente. Los que se dieron de baja nunca se incluyen.
            </p>
            <div className="flex flex-wrap gap-2 mb-3">
              {etiquetas?.map((e) => {
                const activa = segmento.etiquetas.includes(e.etiqueta)
                return (
                  <button
                    type="button"
                    key={e.etiqueta}
                    onClick={() => alternarEtiqueta(e.etiqueta)}
                    className={`px-3 py-1 rounded-full text-sm border transition ${activa ? 'bg-wa-700 text-white border-wa-700' : 'bg-white hover:border-wa-500'}`}
                  >
                    {e.etiqueta} <span className="opacity-60">{e.contactos}</span>
                  </button>
                )
              })}
            </div>
            {segmento.etiquetas.length > 1 && (
              <div className="flex gap-4 text-sm">
                {[['cualquiera', 'Tiene cualquiera de las etiquetas'], ['todas', 'Tiene todas las etiquetas']].map(([v, t]) => (
                  <label key={v} className="flex items-center gap-1.5">
                    <input type="radio" className="accent-wa-700" checked={segmento.modo === v} onChange={() => setSegmento({ ...segmento, modo: v })} />
                    {t}
                  </label>
                ))}
              </div>
            )}
          </Card>

          <Card titulo="3 · Plantilla y variables">
            {plantillas?.length === 0 && <Aviso tipo="alerta">No hay plantillas aprobadas. Crea una y envíala a revisión de Meta.</Aviso>}
            <Campo etiqueta="Plantilla aprobada">
              <Select value={plantillaId} onChange={(e) => setPlantillaId(e.target.value)} required>
                <option value="">Selecciona…</option>
                {plantillas?.map((p) => (
                  <option key={p.id} value={p.id}>{p.nombre} · {p.categoria}</option>
                ))}
              </Select>
            </Campo>
            {plantilla && (
              <div className="mt-4 space-y-3">
                <p className="text-xs text-slate-500">
                  <span className="font-mono">{'{{nombre}}'}</span> se completa con el nombre de cada contacto. El resto es igual para toda la campaña:
                </p>
                <div className="grid sm:grid-cols-2 gap-3">
                  {requeridas.map((v) => (
                    <Campo key={v} etiqueta={<span className="font-mono">{`{{${v}}}`}</span>}>
                      <Input value={variables[v] || ''} onChange={(e) => setVariables({ ...variables, [v]: e.target.value })} required />
                    </Campo>
                  ))}
                </div>
              </div>
            )}
          </Card>

          <Card titulo="4 · Envío">
            <div className="space-y-2 text-sm">
              {[
                ['ahora', 'Enviar ahora'],
                ['programar', 'Programar fecha y hora'],
                ['borrador', 'Guardar como borrador'],
              ].map(([v, t]) => (
                <label key={v} className="flex items-center gap-2">
                  <input type="radio" className="accent-wa-700" checked={cuando === v} onChange={() => setCuando(v)} /> {t}
                </label>
              ))}
              {cuando === 'programar' && (
                <div className="max-w-xs pt-1">
                  <Input type="datetime-local" value={fecha} onChange={(e) => setFecha(e.target.value)} required />
                  <p className="text-xs text-slate-500 mt-1">Hora local ({Intl.DateTimeFormat().resolvedOptions().timeZone}). Celery Beat la lanza al vencer.</p>
                </div>
              )}
            </div>
          </Card>
          <Aviso>{error}</Aviso>
          <Boton disabled={ocupado || !plantilla}>
            {cuando === 'ahora' ? `Lanzar a ${audiencia ?? 0} contactos` : cuando === 'programar' ? 'Programar campaña' : 'Guardar borrador'}
          </Boton>
        </div>

        <div className="lg:sticky lg:top-6">
          <Telefono>
            {plantilla ? (
              <Burbuja
                encabezado={renderizar(plantilla.encabezado, valoresVista)}
                cuerpo={renderizar(plantilla.cuerpo, valoresVista)}
                pie={plantilla.pie}
                botones={plantilla.botones}
              />
            ) : (
              <div className="text-center text-sm text-slate-500 bg-white/70 rounded-lg p-4">Elige una plantilla para ver el mensaje</div>
            )}
          </Telefono>
        </div>
      </form>
    </>
  )
}
