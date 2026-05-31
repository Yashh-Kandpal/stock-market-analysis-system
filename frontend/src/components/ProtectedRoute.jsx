import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Loader from './Loader'

export default function ProtectedRoute({ children }) {
  const { isLoggedIn, loading } = useAuth()

  if (loading) return <Loader text="Checking authentication..." />
  if (!isLoggedIn) return <Navigate to="/login" replace />

  return children
}
