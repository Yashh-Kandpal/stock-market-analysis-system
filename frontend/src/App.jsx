import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { BarChart, BarChart2, Star, Search, TrendingUp } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import StockDetail from './pages/StockDetail'
import Watchlist from './pages/Watchlist'
import SearchPage from './pages/SearchPage'
import './App.css'
import AnalysisPage from './pages/AnalysisPage'
import MLPage from './pages/MLPage'
import { Brain } from 'lucide-react'

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
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
            <NavLink to="/analysis" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              <BarChart size={18} /> Analysis
            </NavLink>
            <NavLink to="/ml" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              <Brain size={18} /> ML
            </NavLink>
            <NavLink to="/watchlist" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              <Star size={18} /> Watchlist
            </NavLink>
          </div>
          <div className="sidebar-footer">
            <span className="badge-india">🇮🇳 Indian Markets</span>
          </div>
        </nav>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/stock/:symbol" element={<StockDetail />} />
            <Route path="/watchlist" element={<Watchlist />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/analysis/:symbol" element={<AnalysisPage />} />
            <Route path="/ml/:symbol" element={<MLPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
