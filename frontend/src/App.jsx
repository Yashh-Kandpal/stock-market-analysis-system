import { BrowserRouter, Routes, Route, NavLink, useNavigate } from 'react-router-dom'
import {
  BarChart, BarChart2, Star, Search, TrendingUp,
  Brain, LogOut, Sun, Moon, ChevronLeft, ChevronRight,
  Activity
} from 'lucide-react'
import { GoogleOAuthProvider } from '@react-oauth/google'

import { AuthProvider, useAuth }       from './context/AuthContext'
import { ThemeProvider, useTheme }     from './context/ThemeContext'
import { SidebarProvider, useSidebar } from './context/SidebarContext'
import ProtectedRoute from './components/ProtectedRoute'

import Dashboard       from './pages/Dashboard'
import StockDetail     from './pages/StockDetail'
import Watchlist       from './pages/Watchlist'
import SearchPage      from './pages/SearchPage'
import AnalysisPage    from './pages/AnalysisPage'
import MLPage          from './pages/MLPage'
import LoginPage       from './pages/LoginPage'
import PerformancePage from './pages/PerformancePage'

import './App.css'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

function Sidebar() {
  const { user, logout, isLoggedIn } = useAuth()
  const { theme, toggle: toggleTheme, isDark } = useTheme()
  const { expanded, toggle: toggleSidebar }    = useSidebar()
  const navigate = useNavigate()

  const handleLogout = () => { logout(); navigate('/login') }

  const navLink = (to, Icon, label, end = false) => (
    <NavLink to={to} end={end}
      className={({ isActive }) => `nav-link ${isActive ? 'active' : ''} ${!expanded ? 'collapsed' : ''}`}
      title={!expanded ? label : undefined}
    >
      <Icon size={18} className="nav-icon" />
      {expanded && <span className="nav-label">{label}</span>}
    </NavLink>
  )

  return (
    <nav className={`sidebar ${expanded ? 'expanded' : 'collapsed'}`}>

      {/* Brand */}
      <div className="sidebar-brand">
        <TrendingUp size={22} color="var(--accent)" className="brand-icon" />
        {expanded && <span className="brand-text">StockIN</span>}
      </div>

      {/* Nav links */}
      <div className="sidebar-links">
        {navLink('/',            BarChart2,  'Dashboard',   true)}
        {navLink('/search',      Search,     'Search')}
        {navLink('/watchlist',   Star,       'Watchlist')}
        {navLink('/performance', Activity,   'Performance')}
      </div>

      {/* Bottom controls */}
      <div className="sidebar-bottom">
        {/* Theme toggle */}
        <button
          className={`sidebar-icon-btn ${!expanded ? 'center' : ''}`}
          onClick={toggleTheme}
          title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {isDark ? <Sun size={16} /> : <Moon size={16} />}
          {expanded && <span>{isDark ? 'Light mode' : 'Dark mode'}</span>}
        </button>

        {/* User section */}
        {isLoggedIn && user && (
          <div className={`sidebar-user ${!expanded ? 'center' : ''}`}>
            {user.avatar_url
              ? <img src={user.avatar_url} alt={user.name} className="user-avatar" />
              : <div className="user-avatar-placeholder">{user.name?.[0]?.toUpperCase()}</div>
            }
            {expanded && (
              <div className="user-info">
                <div className="user-name">{user.name}</div>
                <div className="user-email">{user.email}</div>
              </div>
            )}
            {expanded && (
              <button className="logout-btn" onClick={handleLogout} title="Logout">
                <LogOut size={15} />
              </button>
            )}
            {!expanded && (
              <button className="logout-btn collapsed-logout" onClick={handleLogout} title="Logout">
                <LogOut size={14} />
              </button>
            )}
          </div>
        )}

        {/* Collapse/expand toggle */}
        <button className="sidebar-toggle-btn" onClick={toggleSidebar}
          title={expanded ? 'Collapse sidebar' : 'Expand sidebar'}>
          {expanded ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
          {expanded && <span>Collapse</span>}
        </button>
      </div>
    </nav>
  )
}

function AppLayout() {
  const { expanded } = useSidebar()

  return (
    <div className={`app-layout ${expanded ? 'sidebar-expanded' : 'sidebar-collapsed'}`}>
      <Sidebar />
      <main className="main-content">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/"                  element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/stock/:symbol"     element={<ProtectedRoute><StockDetail /></ProtectedRoute>} />
          <Route path="/watchlist"         element={<ProtectedRoute><Watchlist /></ProtectedRoute>} />
          <Route path="/search"            element={<ProtectedRoute><SearchPage /></ProtectedRoute>} />
          <Route path="/analysis/:symbol"  element={<ProtectedRoute><AnalysisPage /></ProtectedRoute>} />
          <Route path="/ml/:symbol"        element={<ProtectedRoute><MLPage /></ProtectedRoute>} />
          <Route path="/performance"       element={<ProtectedRoute><PerformancePage /></ProtectedRoute>} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <ThemeProvider>
        <AuthProvider>
          <SidebarProvider>
            <BrowserRouter>
              <AppLayout />
            </BrowserRouter>
          </SidebarProvider>
        </AuthProvider>
      </ThemeProvider>
    </GoogleOAuthProvider>
  )
}
