import { useState } from 'react'
import { BrowserRouter, Routes, Route, Link, useNavigate } from 'react-router-dom'
import SelfieUpload from './components/SelfieUpload'
import OnboardingForm from './components/OnboardingForm'
import OutfitGrid from './components/OutfitGrid'
import FeedbackBar from './components/FeedbackBar'
import OutfitHistory from './components/OutfitHistory'
import { uploadSelfie, generateOutfit } from './api'
import './index.css'

function Builder() {
  const [session, setSession] = useState(null)
  const [currentOutfit, setCurrentOutfit] = useState(null)
  const [outfitIndex, setOutfitIndex] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [done, setDone] = useState(false)
  const navigate = useNavigate()

  const handleSelfie = async (file) => {
    setLoading(true)
    setError(null)
    try {
      const result = await uploadSelfie(file)
      setSession({
        session_id: result.session_id,
        style_profile: result.style_profile,
        outfits: [],
        feedbacks: [],
        onboarding: null,
      })
    } catch (e) {
      setError(e.message || 'Failed to analyze photo. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleOnboarding = async (answers) => {
    setLoading(true)
    setError(null)
    try {
      const result = await generateOutfit({
        session_id: session.session_id,
        onboarding: answers,
      })
      setCurrentOutfit(result.outfit)
      setOutfitIndex(result.outfit_index)
      setSession((s) => ({ ...s, onboarding: answers, outfits: [...s.outfits, result.outfit] }))
    } catch (e) {
      setError(e.message || 'Failed to generate outfit. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleFeedback = async (feedback) => {
    setLoading(true)
    setError(null)
    try {
      const result = await generateOutfit({
        session_id: session.session_id,
        feedback,
      })
      setCurrentOutfit(result.outfit)
      setOutfitIndex(result.outfit_index)
      setSession((s) => ({
        ...s,
        outfits: [...s.outfits, result.outfit],
        feedbacks: [...s.feedbacks, feedback],
      }))
    } catch (e) {
      setError(e.message || 'Failed to generate outfit. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setSession(null)
    setCurrentOutfit(null)
    setOutfitIndex(0)
    setDone(false)
    setError(null)
  }

  if (done) {
    return (
      <div className="done-screen">
        <h2>Outfit saved!</h2>
        <p>Your session has been saved and is available in history.</p>
        <div className="done-actions">
          <button className="btn-primary" onClick={handleReset}>
            Start new session
          </button>
          <button className="btn-secondary" onClick={() => navigate('/history')}>
            View history
          </button>
        </div>
      </div>
    )
  }

  if (!session) {
    return <SelfieUpload onUpload={handleSelfie} loading={loading} error={error} />
  }

  if (!session.onboarding) {
    return <OnboardingForm onSubmit={handleOnboarding} loading={loading} error={error} />
  }

  if (!currentOutfit) {
    return (
      <div className="loading">
        <div className="spinner" />
        Generating your outfit...
      </div>
    )
  }

  return (
    <div className="builder">
      <div className="builder-header">
        <h2>Outfit #{outfitIndex}</h2>
        <button className="btn-secondary" onClick={handleReset}>
          Start over
        </button>
      </div>
      <OutfitGrid outfit={currentOutfit} />
      {error && <p className="error">{error}</p>}
      <FeedbackBar loading={loading} onFeedback={handleFeedback} onDone={() => setDone(true)} />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <nav className="nav">
        <Link to="/" className="nav-brand">AI Outfit Builder</Link>
        <Link to="/history" className="nav-link">History</Link>
      </nav>
      <main className="main">
        <Routes>
          <Route path="/" element={<Builder />} />
          <Route path="/history" element={<OutfitHistory />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
