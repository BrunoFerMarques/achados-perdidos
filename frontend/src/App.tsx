import { Route, Routes } from 'react-router'
import { RequireAuth } from './auth/RequireAuth'
import { RequireRole } from './auth/RequireRole'
import { CLAIMANTS, STAFF } from './auth/roles'
import { Header } from './components/Header'
import { Page } from './components/Page'
import { ClaimItemRoute } from './pages/ClaimItemPage'
import { HistoryPage } from './pages/HistoryPage'
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/LoginPage'
import { MyClaimsPage } from './pages/MyClaimsPage'
import { MyItemsPage } from './pages/MyItemsPage'
import { PickupPage } from './pages/PickupPage'
import { ReceiveItemsPage } from './pages/ReceiveItemsPage'
import { RegisterItemPage } from './pages/RegisterItemPage'
import { ReviewClaimsPage } from './pages/ReviewClaimsPage'
import { SignUpPage } from './pages/SignUpPage'
import { TransfersPage } from './pages/TransfersPage'

function App() {
  return (
    <>
      <Header />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/criar-conta" element={<SignUpPage />} />
        <Route
          path="/itens/novo"
          element={<RequireAuth><RegisterItemPage /></RequireAuth>}
        />
        <Route
          path="/itens/meus"
          element={<RequireAuth><MyItemsPage /></RequireAuth>}
        />
        <Route
          path="/itens/:id/reivindicar"
          element={<RequireRole roles={CLAIMANTS}><ClaimItemRoute /></RequireRole>}
        />
        <Route
          path="/reivindicacoes"
          element={<RequireRole roles={CLAIMANTS}><MyClaimsPage /></RequireRole>}
        />
        <Route
          path="/atendimento/recebimento"
          element={<RequireRole roles={STAFF}><ReceiveItemsPage /></RequireRole>}
        />
        <Route
          path="/atendimento/analise"
          element={<RequireRole roles={STAFF}><ReviewClaimsPage /></RequireRole>}
        />
        <Route
          path="/atendimento/retirada"
          element={<RequireRole roles={STAFF}><PickupPage /></RequireRole>}
        />
        <Route
          path="/atendimento/transferencias"
          element={<RequireRole roles={STAFF}><TransfersPage /></RequireRole>}
        />
        <Route
          path="/atendimento/historico"
          element={<RequireRole roles={STAFF}><HistoryPage /></RequireRole>}
        />
        <Route
          path="*"
          element={<Page title="Página não encontrada">Confira o endereço.</Page>}
        />
      </Routes>
    </>
  )
}

export default App
