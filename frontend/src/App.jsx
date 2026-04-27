import { useState } from 'react'
import SelfieUpload from './components/SelfieUpload'
import StyleProfile from './components/StyleProfile'
import OutfitGrid from './components/OutfitGrid'
import TryOnModal from './components/TryOnModal'
import { analyzeSelfie, refreshOutfit, swapItem, tryOn } from './api'
import './index.css'

export default function App() {
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [tryOnState, setTryOnState] = useState(null)

  const handleSelfie = async (file, gender, stylePref) => {
    setLoading(true)
    setError(null)
    try {
      const result = await analyzeSelfie(file, gender, stylePref)
      setSession(result)
    } catch (e) {
      setError(e.message || 'Failed to analyze photo')
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await refreshOutfit(session.session_id)
      setSession(s => ({ ...s, outfit: result.outfit }))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSwap = async (category) => {
    setError(null)
    try {
      const result = await swapItem(session.session_id, category)
      setSession(s => ({ ...s, outfit: { ...s.outfit, [category]: result.item } }))
    } catch (e) {
      setError(e.message)
    }
  }

  const handleTryOn = async (item) => {
    setTryOnState({ item, loading: true, result: null, error: null })
    try {
      const result = await tryOn(session.session_id, item.id, item.category)
      setTryOnState(s => ({ ...s, loading: false, result: result.result_url }))
    } catch (e) {
      setTryOnState(s => ({ ...s, loading: false, error: e.message }))
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
          onClick={() => { setSession(null); setError(null) }}
        >
          New Session
        </button>
      </nav>
      <main className="main">
        <StyleProfile profile={session.profile} selfieUrl={session.selfie_url} />
        {error && <p className="error" style={{ textAlign: 'left', marginBottom: 16 }}>{error}</p>}
        <OutfitGrid
          outfit={session.outfit}
          loading={loading}
          onRefresh={handleRefresh}
          onSwap={handleSwap}
          onTryOn={handleTryOn}
        />
      </main>
      {tryOnState && (
        <TryOnModal
          item={tryOnState.item}
          loading={tryOnState.loading}
          result={tryOnState.result}
          error={tryOnState.error}
          onClose={() => setTryOnState(null)}
        />
      )}
    </div>
  )
}
