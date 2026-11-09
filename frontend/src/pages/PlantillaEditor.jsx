import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { del, get, post, put } from '../api'
import { extraerVariables, renderizar } from '../formato'
import { Aviso, Boton, Campo, Card, Cargando, Encabezado, Estado, Input, Select, Textarea, useAccion } from '../components/ui'
import { Burbuja, Telefono } from '../components/VistaWhatsApp'

const NUEVA = {
  nombre: '',
  idioma: 'es',
  categoria: 'MARKETING',
  encabezado: '',
  cuerpo: 'Hola {{nombre}}, ',
  pie: 'Responde BAJA para no recibir promociones',
  botones: [],
  ejemplos: { nombre: 'Ana' },
}
const SUGERIDAS = ['nombre', 'producto', 'descuento', 'monto', 'fecha', 'codigo', 'pedido']

export default function PlantillaEditor() {
  const { id } = useParams()
  const navegar = useNavigate()
  const [p, setP] = useState(id ? null : NUEVA)
  const [estado, setEstado] = useState(null) // estado y datos de Meta de la plantilla guardada
  const [verJson, setVerJson] = useState(false)
  const [json, setJson] = useState(null)
  const [ejecutar, ocupado, error, setError] = useAccion()
  const [ok, setOk] = useState(null)
  const cuerpoRef = useRef(null)

  useEffect(() => {
    if (!id) return
    get(`/plantillas/${id}`).then((d) => {
      setP({ ...d, encabezado: d.encabezado || '', pie: d.pie || '' })
      setEstado(d)
    }).catch((e) => setError(e.message))
  }, [id, setError])

  const variables = useMemo(() => (p ? extraerVariables(p.encabezado, p.cuerpo) : []), [p])
  const bloqueada = estado && ['PENDIENTE', 'APROBADA'].includes(estado.estado)

  if (!p) return <Cargando />

  const cambiar = (k) => (e) => setP({ ...p, [k]: e.target.value })
  const datos = () => ({
    ...p,
    encabezado: p.encabezado || null,
    pie: p.pie || null,
    botones: p.botones.filter((b) => b.trim()),
    ejemplos: Object.fromEntries(variables.map((v) => [v, p.ejemplos[v] || ''])),
  })

  function insertarVariable(nombre) {
    const el = cuerpoRef.current
    const ini = el?.selectionStart ?? p.cuerpo.length
    const fin = el?.selectionEnd ?? p.cuerpo.length
    const texto = `{{${nombre}}}`
    setP({ ...p, cuerpo: p.cuerpo.slice(0, ini) + texto + p.cuerpo.slice(fin) })
    setTimeout(() => { el?.focus(); el?.setSelectionRange(ini + texto.length, ini + texto.length) })
  }

  function formato(marca) {
    const el = cuerpoRef.current
    if (!el) return
    const { selectionStart: a, selectionEnd: b } = el
    if (a === b) return
    setP({ ...p, cuerpo: p.cuerpo.slice(0, a) + marca + p.cuerpo.slice(a, b) + marca + p.cuerpo.slice(b) })
  }

  async function guardar() {
    setOk(null)
    const r = await ejecutar(() => (id ? put(`/plantillas/${id}`, datos()) : post('/plantillas', datos())))
    if (r) {
      setEstado(r)
      setOk('Guardada como borrador')
      if (!id) navegar(`/plantillas/${r.id}`, { replace: true })
    }
  }

  async function enviarAMeta() {
    setOk(null)
    const r = await ejecutar(() => post(`/plantillas/${id}/enviar-a-meta`))
    if (r) {
      setEstado(r)
      setOk(r.estado === 'APROBADA' ? 'Aprobada (en sandbox la aprobación es inmediata)' : 'Enviada a revisión de Meta. El resultado llegará por webhook.')
    }
  }

  async function sincronizar() {
    const r = await ejecutar(() => post(`/plantillas/${id}/sincronizar`))
    if (r) { setEstado(r); setOk(`Estado en Meta: ${r.estado}`) }
  }

  async function duplicar() {
    const nombre = prompt('Nombre de la nueva versión:', `${p.nombre}_v2`)
    if (!nombre) return
    const r = await ejecutar(() => post('/plantillas', { ...datos(), nombre }))
    if (r) {
      setOk('Copia creada como borrador')
      navegar(`/plantillas/${r.id}`)
    }
  }

  async function eliminar() {
    if (!confirm('¿Eliminar la plantilla?')) return
    if ((await ejecutar(() => del(`/plantillas/${id}`))) !== undefined) navegar('/plantillas')
  }

  async function mostrarJson() {
    const r = await ejecutar(() => post('/plantillas/vista-previa', datos()))
    if (r) { setJson(r.componentes_meta); setVerJson(true) }
  }

  return (
    <>
      <Encabezado titulo={id ? `Plantilla ${p.nombre}` : 'Nueva plantilla'} subtitulo="Variables con nombre: {{nombre}}, {{producto}}, {{descuento}}…">
        {estado && <Estado valor={estado.estado} />}
      </Encabezado>
      <div className="grid lg:grid-cols-[1fr_380px] gap-6 items-start">
        <div className="space-y-6">
          {bloqueada && (
            <Aviso tipo="info">
              Esta plantilla ya se envió a Meta y no puede editarse (Meta la devolvería a revisión). Duplícala para crear una nueva versión.
            </Aviso>
          )}
          <Card titulo="Contenido">
            <fieldset disabled={bloqueada} className="space-y-4">
              <div className="grid sm:grid-cols-3 gap-3">
                <Campo etiqueta="Nombre" ayuda="minúsculas y guion bajo">
                  <Input value={p.nombre} onChange={cambiar('nombre')} placeholder="promo_verano" />
                </Campo>
                <Campo etiqueta="Categoría" ayuda="Meta cobra distinto cada una">
                  <Select value={p.categoria} onChange={cambiar('categoria')}>
                    <option value="MARKETING">MARKETING (promociones)</option>
                    <option value="UTILITY">UTILITY (transaccional)</option>
                  </Select>
                </Campo>
                <Campo etiqueta="Idioma">
                  <Select value={p.idioma} onChange={cambiar('idioma')}>
                    <option value="es">Español (es)</option>
                    <option value="es_MX">Español México (es_MX)</option>
                    <option value="es_AR">Español Argentina (es_AR)</option>
                    <option value="en_US">Inglés (en_US)</option>
                  </Select>
                </Campo>
              </div>
              <Campo etiqueta="Encabezado (opcional)" ayuda="Máx. 60 caracteres">
                <Input value={p.encabezado} onChange={cambiar('encabezado')} maxLength={60} />
              </Campo>
              <div>
                <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
                  <span className="text-sm font-medium text-slate-700">Cuerpo</span>
                  <div className="flex flex-wrap gap-1">
                    <button type="button" onClick={() => formato('*')} className="px-2 py-0.5 text-xs rounded border font-bold">B</button>
                    <button type="button" onClick={() => formato('_')} className="px-2 py-0.5 text-xs rounded border italic">I</button>
                    <button type="button" onClick={() => formato('~')} className="px-2 py-0.5 text-xs rounded border line-through">S</button>
                    {SUGERIDAS.map((v) => (
                      <button key={v} type="button" onClick={() => insertarVariable(v)} className="px-2 py-0.5 text-xs rounded bg-amber-100 text-amber-900 font-mono hover:bg-amber-200">
                        {`{{${v}}}`}
                      </button>
                    ))}
                  </div>
                </div>
                <Textarea ref={cuerpoRef} rows={6} value={p.cuerpo} onChange={cambiar('cuerpo')} maxLength={1024} />
                <div className="text-xs text-slate-500 text-right">{p.cuerpo.length} / 1024</div>
              </div>
              <Campo etiqueta="Pie (opcional)" ayuda="En MARKETING conviene indicar cómo darse de baja">
                <Input value={p.pie} onChange={cambiar('pie')} maxLength={60} />
              </Campo>
              <div>
                <span className="block text-sm font-medium text-slate-700 mb-1">Botones de respuesta rápida (máx. 3)</span>
                <div className="space-y-2">
                  {p.botones.map((b, i) => (
                    <div key={i} className="flex gap-2">
                      <Input value={b} maxLength={25} onChange={(e) => setP({ ...p, botones: p.botones.map((x, j) => (j === i ? e.target.value : x)) })} />
                      <Boton type="button" variante="fantasma" onClick={() => setP({ ...p, botones: p.botones.filter((_, j) => j !== i) })}>✕</Boton>
                    </div>
                  ))}
                  {p.botones.length < 3 && (
                    <Boton type="button" variante="secundario" onClick={() => setP({ ...p, botones: [...p.botones, ''] })}>+ Botón</Boton>
                  )}
                </div>
              </div>
            </fieldset>
          </Card>

          <Card titulo="Valores de ejemplo" accion={<span className="text-xs text-slate-500">Meta los exige para revisar la plantilla</span>}>
            {variables.length === 0 ? (
              <p className="text-sm text-slate-500">La plantilla no tiene variables.</p>
            ) : (
              <div className="grid sm:grid-cols-2 gap-3">
                {variables.map((v) => (
                  <Campo key={v} etiqueta={<span className="font-mono">{`{{${v}}}`}</span>}>
                    <Input
                      disabled={bloqueada}
                      value={p.ejemplos[v] || ''}
                      onChange={(e) => setP({ ...p, ejemplos: { ...p.ejemplos, [v]: e.target.value } })}
                    />
                  </Campo>
                ))}
              </div>
            )}
          </Card>

          <Aviso>{error}</Aviso>
          <Aviso tipo="ok">{ok}</Aviso>
          {estado?.motivo_rechazo && <Aviso>Motivo de rechazo de Meta: {estado.motivo_rechazo}</Aviso>}
          <div className="flex flex-wrap gap-2">
            {!bloqueada && <Boton onClick={guardar} disabled={ocupado}>Guardar borrador</Boton>}
            {id && estado && ['BORRADOR', 'RECHAZADA'].includes(estado.estado) && (
              <Boton variante="secundario" onClick={enviarAMeta} disabled={ocupado}>Enviar a revisión de Meta</Boton>
            )}
            {id && ['PENDIENTE', 'BORRADOR', 'RECHAZADA'].includes(estado?.estado) && <Boton variante="secundario" onClick={sincronizar} disabled={ocupado}>Consultar estado en Meta</Boton>}
            {bloqueada && <Boton variante="secundario" onClick={duplicar}>Duplicar como nueva versión</Boton>}
            <Boton variante="fantasma" onClick={mostrarJson}>{'{ }'} JSON para Meta</Boton>
            {id && <Boton variante="fantasma" className="ml-auto text-red-600" onClick={eliminar}>Eliminar</Boton>}
          </div>
          {verJson && json && (
            <Card titulo="components (POST /{WABA_ID}/message_templates)" accion={<button className="text-sm text-slate-500" onClick={() => setVerJson(false)}>ocultar</button>}>
              <pre className="text-xs bg-slate-900 text-emerald-300 rounded-lg p-3 overflow-x-auto">{JSON.stringify(json, null, 2)}</pre>
            </Card>
          )}
        </div>

        <div className="lg:sticky lg:top-6 space-y-3">
          <Telefono>
            <Burbuja
              encabezado={renderizar(p.encabezado, p.ejemplos)}
              cuerpo={renderizar(p.cuerpo, p.ejemplos) || ' '}
              pie={p.pie}
              botones={p.botones}
            />
          </Telefono>
          <p className="text-xs text-center text-slate-500">
            Vista previa con los valores de ejemplo. Las variables sin valor se resaltan en amarillo.
          </p>
        </div>
      </div>
    </>
  )
}
