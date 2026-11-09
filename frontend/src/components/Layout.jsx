import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { sesion } from '../api'
import { useApi } from '../hooks'

const MENU = [
  ['/', 'Dashboard', '📊'],
  ['/conversaciones', 'Conversaciones', '💬'],
  ['/campanas', 'Campañas', '📣'],
  ['/plantillas', 'Plantillas', '📝'],
  ['/contactos', 'Contactos', '👥'],
  ['/automatizaciones', 'Automatizaciones', '⚡'],
  ['/eventos', 'Eventos de tienda', '🛒'],
  ['/sistema', 'Webhook y sistema', '🔧'],
]

export default function Layout() {
  const navegar = useNavigate()
  const { datos: sistema } = useApi('/sistema')
  const sandbox = sistema?.modo === 'sandbox'

  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      <aside className="md:w-60 md:min-h-screen md:sticky md:top-0 md:h-screen bg-wa-800 text-white flex flex-col shrink-0">
        <div className="px-5 py-4 font-bold text-lg flex items-center gap-2">
          <span className="text-2xl">💬</span> WhatsApp Ventas
        </div>
        <nav className="flex md:flex-col overflow-x-auto px-2 pb-2 gap-0.5 flex-1">
          {MENU.map(([ruta, nombre, icono]) => (
            <NavLink
              key={ruta}
              to={ruta}
              end={ruta === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm whitespace-nowrap transition ${
                  isActive ? 'bg-white/15 font-semibold' : 'text-wa-100 hover:bg-white/10'
                }`
              }
            >
              <span>{icono}</span> {nombre}
            </NavLink>
          ))}
        </nav>
        <button
          onClick={() => {
            sesion.cerrar()
            navegar('/login')
          }}
          className="hidden md:block m-3 text-left text-sm text-wa-100 hover:text-white px-3 py-2"
        >
          ⎋ Cerrar sesión
        </button>
      </aside>
      <div className="flex-1 min-w-0">
        {sistema && (
          <div
            className={`px-6 py-1.5 text-xs flex items-center gap-2 ${
              sandbox ? 'bg-amber-100 text-amber-900' : 'bg-emerald-100 text-emerald-900'
            }`}
          >
            <span className={`w-2 h-2 rounded-full shrink-0 ${sandbox ? 'bg-amber-500' : 'bg-emerald-500'}`} />
            {sandbox
              ? 'MODO SIMULACIÓN (sandbox): no se envía nada real. Los estados y respuestas se simulan con payloads idénticos a los webhooks de Meta.'
              : `MODO CLOUD API: los mensajes salen por la WhatsApp Business Cloud API oficial (${sistema.api_version}).`}
          </div>
        )}
        <main className="p-4 md:p-6 max-w-7xl mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
