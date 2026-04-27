import { useState } from 'react'
import SelfieUpload from './components/SelfieUpload'
import StyleProfile from './components/StyleProfile'
import OutfitGrid from './components/OutfitGrid'
import { analyzeSelfie, generateOutfit } from './api'
import './index.css'

export default function App() {
  const [session, setSession] = useState(null)
  const [outfit, setOutfit] = useState(null)
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState(null)
  const [showFeedback, setShowFeedback] = useState(false)
  const [feedback, setFeedback] = useState({ rating: 3, text: '' })

  const handleSelfie = async (file, gender, stylePref) => {
    setLoading(true)
    setError(null)
    setOutfit(null)
    try {
      const result = await analyzeSelfie(file, gender, stylePref)
      setSession(result)
      setGenerating(true)
      const gen = await generateOutfit(result.session_id)
      setOutfit(gen.outfit)
    } catch (e) {
      setError(e.message || 'Something went wrong')
    } finally {
      setLoading(false)
      setGenerating(false)
    }
  }

  const handleRegenerate = async (fb = null) => {
    setGenerating(true)
    setError(null)
    setShowFeedback(false)
    try {
      const gen = await generateOutfit(session.session_id, fb)
      setOutfit(gen.outfit)
      setFeedback({ rating: 3, text: '' })
    } catch (e) {
      setError(e.message || 'Generation failed')
    } finally {
      setGenerating(false)
    }
  }

  if (!session) {
    return (
      <div className="app">
        <nav className="nav">
          <span className="nav-brand">AI Outfit Builder</span>
        </nav>
        <main className="main">
          <SelfieUpload onUpload={handleSelfie} loading={loading} error={error} />
        </main>
      </div>
    )
  }

  return (
    <div className="app">
      <nav className="nav">
        <span className="nav-brand">AI Outfit Builder</span>
        <button
          className="btn-secondary"
          style={{ fontSize: '0.85rem', padding: '8px 16px' }}
          onClick={() => { setSession(null); setOutfit(null); setError(null) }}
        >
          New Session
        </button>
      </nav>
      <main className="main">
        <StyleProfile profile={session.profile} selfieUrl={session.selfie_url} />
        {error && <p className="error" style={{ marginBottom: 16 }}>{error}</p>}
        <OutfitGrid
          outfit={outfit}
          generating={generating}
          onRegenerate={() => setShowFeedback(true)}
        />
        {showFeedback && !generating && (
          <div className="feedback-panel">
            <h3 className="feedback-title">How was that outfit?</h3>
            <div className="rating-row">
              {[1, 2, 3, 4, 5].map(n => (
                <button
                  key={n}
                  className={`rating-btn${feedback.rating === n ? ' rating-active' : ''}`}
                  onClick={() => setFeedback(f => ({ ...f, rating: n }))}
                >
                  {n}
                </button>
              ))}
            </div>
            <textarea
              className="feedback-text"
              placeholder="Any comments? (e.g. more colorful, less formal…)"
              value={feedback.text}
              onChange={e => setFeedback(f => ({ ...f, text: e.target.value }))}
              rows={2}
            />
            <div className="feedback-actions">
              <button className="btn-primary" onClick={() => handleRegenerate(feedback)}>
                Regenerate with Feedback
              </button>
              <button className="btn-secondary" onClick={() => handleRegenerate(null)}>
                Skip — Just Regenerate
              </button>
              <button className="btn-secondary" onClick={() => setShowFeedback(false)}>
                Cancel
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
