import { Route, Routes } from 'react-router'
import { RequireAuth } from './auth/RequireAuth'
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/LoginPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<RequireAuth><HomePage /></RequireAuth>} />
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/itens/novo"
        element={<RequireAuth><p>Registrar item (em breve)</p></RequireAuth>}
      />
      <Route path="*" element={<p>Página não encontrada</p>} />
    </Routes>
  )
}

export default App