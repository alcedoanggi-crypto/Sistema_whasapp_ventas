import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { post, sesion } from '../api'
import { Aviso, Boton, Campo, Input, useAccion } from '../components/ui'

export default function Login() {
  const navegar = useNavigate()
  const [email, setEmail] = useState('admin@demo.com')
  const [password, setPassword] = useState('')
  const [ejecutar, ocupado, error] = useAccion()

  async function entrar(e) {
    e.preventDefault()
    const r = await ejecutar(() => post('/auth/login', { email, password }))
    if (r) {
      sesion.guardar(r.token)
      navegar('/')
    }
  }

  return (
    <div className="min-h-screen grid place-items-center bg-gradient-to-br from-wa-800 to-wa-700 p-4">
      <form onSubmit={entrar} className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-8 space-y-4">
        <div className="text-center">
          <div className="text-5xl mb-2">💬</div>
          <h1 className="text-xl font-bold text-slate-900">WhatsApp Ventas</h1>
          <p className="text-sm text-slate-500">Automatización sobre la Cloud API oficial de Meta</p>
        </div>
        <Campo etiqueta="Email">
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </Campo>
        <Campo etiqueta="Contraseña" ayuda="Demo: admin@demo.com / admin123">
          <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoFocus />
        </Campo>
        <Aviso>{error}</Aviso>
        <Boton className="w-full" disabled={ocupado}>
          {ocupado ? 'Entrando…' : 'Entrar'}
        </Boton>
      </form>
    </div>
  )
}
