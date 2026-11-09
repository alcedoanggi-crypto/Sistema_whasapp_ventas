import { Navigate, Route, Routes } from 'react-router-dom'
import { sesion } from './api'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Contactos from './pages/Contactos'
import Plantillas from './pages/Plantillas'
import PlantillaEditor from './pages/PlantillaEditor'
import Campanas from './pages/Campanas'
import CampanaNueva from './pages/CampanaNueva'
import CampanaDetalle from './pages/CampanaDetalle'
import Conversaciones from './pages/Conversaciones'
import Automatizaciones from './pages/Automatizaciones'
import Eventos from './pages/Eventos'
import Sistema from './pages/Sistema'

function Protegido({ children }) {
  return sesion.token() ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Protegido><Layout /></Protegido>}>
        <Route index element={<Dashboard />} />
        <Route path="contactos" element={<Contactos />} />
        <Route path="plantillas" element={<Plantillas />} />
        <Route path="plantillas/nueva" element={<PlantillaEditor />} />
        <Route path="plantillas/:id" element={<PlantillaEditor />} />
        <Route path="campanas" element={<Campanas />} />
        <Route path="campanas/nueva" element={<CampanaNueva />} />
        <Route path="campanas/:id" element={<CampanaDetalle />} />
        <Route path="conversaciones" element={<Conversaciones />} />
        <Route path="conversaciones/:id" element={<Conversaciones />} />
        <Route path="automatizaciones" element={<Automatizaciones />} />
        <Route path="eventos" element={<Eventos />} />
        <Route path="sistema" element={<Sistema />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
