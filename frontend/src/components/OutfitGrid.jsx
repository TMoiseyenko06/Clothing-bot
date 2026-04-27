import OutfitCard from './OutfitCard'

export default function OutfitGrid({ outfit, generating, onRegenerate }) {
  if (generating) {
    return (
      <div className="loading" style={{ minHeight: 320 }}>
        <div className="spinner" />
        <span>Building your outfit…</span>
      </div>
    )
  }

  if (!outfit) return null

  const pieces = outfit.pieces || []

  return (
    <div className="outfit-grid-container">
      <div className="outfit-grid-header">
        <div>
          <h2 className="outfit-title">Your Outfit</h2>
          {outfit.outfit_concept && (
            <p className="outfit-concept">{outfit.outfit_concept}</p>
          )}
        </div>
        <button className="btn-secondary" onClick={onRegenerate}>
          ↺ Regenerate
        </button>
      </div>
      <div className="outfit-grid">
        {pieces.map((piece, i) => (
          <OutfitCard key={`${piece.category}-${i}`} piece={piece} />
        ))}
        {pieces.length === 0 && (
          <p className="empty-outfit">No items found. Try regenerating.</p>
        )}
      </div>
    </div>
  )
}
