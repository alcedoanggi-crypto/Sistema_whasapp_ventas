import { useCallback, useEffect, useRef, useState } from 'react'
import { get } from './api'

// Carga una ruta del API; `intervalo` (ms) la refresca sola (útil con el sandbox, que cambia estados en vivo).
export function useApi(ruta, { intervalo } = {}) {
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(null)
  const [cargando, setCargando] = useState(true)
  const vivo = useRef(true)

  const recargar = useCallback(async () => {
    if (!ruta) return
    try {
      const d = await get(ruta)
      if (vivo.current) { setDatos(d); setError(null) }
    } catch (e) {
      if (vivo.current) setError(e.message)
    } finally {
      if (vivo.current) setCargando(false)
    }
  }, [ruta])

  useEffect(() => {
    vivo.current = true
    setCargando(true)
    recargar()
    if (!intervalo) return () => { vivo.current = false }
    const id = setInterval(recargar, intervalo)
    return () => { vivo.current = false; clearInterval(id) }
  }, [recargar, intervalo])

  return { datos, error, cargando, recargar, setDatos }
}
