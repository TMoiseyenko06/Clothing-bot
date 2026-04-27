import { useState } from 'react'
import SelfieUpload from './components/SelfieUpload'
import StyleProfile from './components/StyleProfile'
import OutfitGrid from './components/OutfitGrid'
import { analyzeSelfie, generateOutfit } from './api'
import './index.css'

const RATING_LABELS = { 1: 'Hate it', 2: 'Not great', 3: 'OK', 4: 'Like it', 5: 'Love it' }

export default function App() {
  const [session, setSession] = useState(null)
  const [outfit, setOutfit] = useState(null)
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState(null)
  const [rating, setRating] = useState(0)
  const [feedbackText, setFeedbackText] = useState('')

  const handleSelfie = async (file, gender, stylePref, budget) => {
    setLoading(true)
    setError(null)
    setOutfit(null)
    setRating(0)
    setFeedbackText('')
    try {
      const result = await analyzeSelfie(file, gender, stylePref, budget)
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

  const handleRegenerate = async () => {
    setGenerating(true)
    setError(null)
    const feedback = rating > 0 ? { rating, text: feedbackText.trim() } : null
    try {
      const gen = await generateOutfit(session.session_id, feedback)
      setOutfit(gen.outfit)
      setRating(0)
      setFeedbackText('')
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
        <OutfitGrid outfit={outfit} generating={generating} />

        {(outfit || generating) && (
          <div className="feedback-panel">
            <div className="feedback-header">
              <h3 className="feedback-title">Rate this outfit</h3>
              {rating > 0 && <span className="rating-label">{RATING_LABELS[rating]}</span>}
            </div>
            <div className="rating-row">
              {[1, 2, 3, 4, 5].map(n => (
                <button
                  key={n}
                  className={`rating-btn${rating === n ? ' rating-active' : ''}`}
                  onClick={() => setRating(r => r === n ? 0 : n)}
                  disabled={generating}
                >
                  {'★'.repeat(n)}{'☆'.repeat(5 - n)}
                </button>
              ))}
            </div>
            <textarea
              className="feedback-text"
              placeholder="Tell Claude what you like or don't like… (e.g. more colorful, cheaper shoes, no jacket)"
              value={feedbackText}
              onChange={e => setFeedbackText(e.target.value)}
              rows={2}
              disabled={generating}
            />
            <button
              className="btn-primary"
              style={{ alignSelf: 'flex-start' }}
              onClick={handleRegenerate}
              disabled={generating}
            >
              {generating ? 'Building outfit…' : '↺ Regenerate Outfit'}
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
