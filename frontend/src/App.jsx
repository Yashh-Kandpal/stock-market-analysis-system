import { BrowserRouter, Routes, Route, NavLink, useNavigate } from 'react-router-dom'
import { BarChart, BarChart2, Star, Search, TrendingUp, Brain, LogOut } from 'lucide-react'
import { GoogleOAuthProvider } from '@react-oauth/google'

import { AuthProvider, useAuth } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'

import Dashboard    from './pages/Dashboard'
import StockDetail  from './pages/StockDetail'
import Watchlist    from './pages/Watchlist'
import SearchPage   from './pages/SearchPage'
import AnalysisPage from './pages/AnalysisPage'
import MLPage       from './pages/MLPage'
import LoginPage    from './pages/LoginPage'

import './App.css'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

function Sidebar() {
  const { user, logout, isLoggedIn } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <nav className="sidebar">
      <div className="sidebar-brand">
        <TrendingUp size={22} color="var(--accent)" />
        <span>StockIN</span>
      </div>

      <div className="sidebar-links">
        <NavLink to="/" end className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          <BarChart2 size={18} /> Dashboard
        </NavLink>
        <NavLink to="/search" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          <Search size={18} /> Search
        </NavLink>
        <NavLink to="/watchlist" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          <Star size={18} /> Watchlist
        </NavLink>
      </div>

      <div className="sidebar-bottom">
        {isLoggedIn && user ? (
          <div className="sidebar-user">
            {user.avatar_url
              ? <img src={user.avatar_url} alt={user.name} className="user-avatar" />
              : <div className="user-avatar-placeholder">{user.name?.[0]?.toUpperCase()}</div>
            }
            <div className="user-info">
              <div className="user-name">{user.name}</div>
              <div className="user-email">{user.email}</div>
            </div>
            <button className="logout-btn" onClick={handleLogout} title="Logout">
              <LogOut size={15} />
            </button>
          </div>
        ) : (
          <span className="badge-india">🇮🇳 Indian Markets</span>
        )}
      </div>
    </nav>
  )
}

function AppLayout() {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <Routes>
          {/* Public */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected */}
          <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/stock/:symbol" element={<ProtectedRoute><StockDetail /></ProtectedRoute>} />
          <Route path="/watchlist" element={<ProtectedRoute><Watchlist /></ProtectedRoute>} />
          <Route path="/search" element={<ProtectedRoute><SearchPage /></ProtectedRoute>} />
          <Route path="/analysis/:symbol" element={<ProtectedRoute><AnalysisPage /></ProtectedRoute>} />
          <Route path="/ml/:symbol" element={<ProtectedRoute><MLPage /></ProtectedRoute>} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AuthProvider>
        <BrowserRouter>
          <AppLayout />
        </BrowserRouter>
      </AuthProvider>
    </GoogleOAuthProvider>
  )
}
