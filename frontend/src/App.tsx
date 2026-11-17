import { Route, Routes } from 'react-router'
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/LoginPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="*" element={<p>Página não encontrada</p>} />
    </Routes>
  )
}

export default App