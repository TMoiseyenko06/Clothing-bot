import { useState, useEffect } from 'react'
import { getSessions } from '../api'
import OutfitGrid from './OutfitGrid'

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function SessionDetail({ session, onBack }) {
  return (
    <div className="session-detail">
      <button className="btn-secondary" style={{ marginBottom: 28 }} onClick={onBack}>
        ← Back to history
      </button>

      <div className="session-detail-header">
        <img
          src={`/files/${session.session_id}/selfie.jpg`}
          alt="Selfie"
          onError={(e) => { e.target.style.display = 'none' }}
        />
        <div className="session-detail-info">
          <h2>Session — {formatDate(session.created_at)}</h2>
          <p>
            {session.outfits?.length || 0} outfit
            {(session.outfits?.length || 0) !== 1 ? 's' : ''} generated
          </p>
          {session.onboarding && (
            <p style={{ marginTop: 4 }}>
              {session.onboarding.occasion} · {session.onboarding.fit} fit · {session.onboarding.budget}
            </p>
          )}
        </div>
      </div>

      {session.outfits?.map((outfit, i) => (
        <div key={i} className="outfit-iteration">
          <h3>Outfit #{i + 1}</h3>
          <OutfitGrid outfit={outfit} />
          {session.feedbacks?.[i] && (
            <div className="feedback-display">
              <strong>Feedback ({session.feedbacks[i].rating}/5):</strong>{' '}
              {session.feedbacks[i].text || <em>No written feedback</em>}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export default function OutfitHistory() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    getSessions()
      .then(setSessions)
      .catch(() => setSessions([]))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
        Loading history...
      </div>
    )
  }

  if (selected) {
    return <SessionDetail session={selected} onBack={() => setSelected(null)} />
  }

  return (
    <div className="history">
      <h2>Outfit History</h2>
      <p className="history-subtitle">
        {sessions.length} saved session{sessions.length !== 1 ? 's' : ''}
      </p>

      {sessions.length === 0 ? (
        <div className="empty-history">
          <p>No sessions yet — upload a photo on the home page to get started.</p>
        </div>
      ) : (
        <div className="session-list">
          {sessions.map((s) => {
            const lastOutfit = s.outfits?.[s.outfits.length - 1]
            return (
              <div
                key={s.session_id}
                className="session-card"
                onClick={() => setSelected(s)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && setSelected(s)}
              >
                <img
                  className="session-selfie"
                  src={`/files/${s.session_id}/selfie.jpg`}
                  alt="Selfie"
                  onError={(e) => { e.target.style.visibility = 'hidden' }}
                />
                <div className="session-info">
                  <div className="session-date">{formatDate(s.created_at)}</div>
                  <div className="session-iterations">
                    {s.outfits?.length || 0} outfit
                    {(s.outfits?.length || 0) !== 1 ? 's' : ''} generated
                  </div>
                  {lastOutfit?.outfit_concept && (
                    <div className="session-concept">
                      Last: "{lastOutfit.outfit_concept}"
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
