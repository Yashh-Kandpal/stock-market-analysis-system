import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { GoogleLogin } from '@react-oauth/google'
import { TrendingUp, BarChart2, Brain, Star } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import api from '../api/client'
import './LoginPage.css'

export default function LoginPage() {
  const { login, isLoggedIn } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (isLoggedIn) navigate('/')
  }, [isLoggedIn])

  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      const res = await api.post('/auth/google', {
        token: credentialResponse.credential,
      })
      login(res.data.access_token, res.data.user)
      navigate('/')
    } catch (e) {
      console.error('Login failed:', e)
      alert('Login failed. Please try again.')
    }
  }

  const handleGoogleError = () => {
    alert('Google sign-in failed. Please try again.')
  }

  return (
    <div className="login-page">
      <div className="login-card">
        {/* Brand */}
        <div className="login-brand">
          <TrendingUp size={36} color="var(--accent)" />
          <h1>StockIN</h1>
          <p>Indian Stock Market Analysis & ML Predictions</p>
        </div>

        {/* Features list */}
        <div className="login-features">
          <div className="lf-item">
            <BarChart2 size={16} color="var(--accent)" />
            <span>Real-time BSE/NSE prices</span>
          </div>
          <div className="lf-item">
            <TrendingUp size={16} color="var(--green)" />
            <span>Statistical analysis — RSI, MACD, Bollinger Bands</span>
          </div>
          <div className="lf-item">
            <Brain size={16} color="#a78bfa" />
            <span>ML predictions — ARIMA, XGBoost, Isolation Forest</span>
          </div>
          <div className="lf-item">
            <Star size={16} color="var(--yellow)" />
            <span>Personal watchlist & search history</span>
          </div>
        </div>

        {/* Google login */}
        <div className="login-action">
          <p className="login-prompt">Sign in to save your watchlist and search history</p>
          <div className="google-btn-wrap">
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={handleGoogleError}
              theme="filled_black"
              shape="rectangular"
              size="large"
              text="signin_with_google"
              width="320"
            />
          </div>
        </div>

        <p className="login-disclaimer">
          By signing in you agree that this is a student project for educational purposes only.
          Not financial advice.
        </p>
      </div>
    </div>
  )
}
