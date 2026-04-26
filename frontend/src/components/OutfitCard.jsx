import { useState } from 'react'

const CATEGORY_EMOJI = {
  Top: '👕',
  Bottom: '👖',
  Shoes: '👟',
  Outerwear: '🧥',
}

export default function OutfitCard({ item, onSwap, onTryOn }) {
  const [imgError, setImgError] = useState(false)

  return (
    <div className="outfit-card">
      {item.image_url && !imgError ? (
        <img
          className="outfit-card-image"
          src={item.image_url}
          alt={item.description || item.category}
          onError={() => setImgError(true)}
          loading="lazy"
        />
      ) : (
        <div className="outfit-card-placeholder">
          {CATEGORY_EMOJI[item.category] || '👗'}
        </div>
      )}
      <div className="outfit-card-body">
        <div className="outfit-card-category">{item.category}</div>
        <div className="outfit-card-desc">{item.description || 'Fashion item'}</div>
        <div className="outfit-card-actions">
          <button className="btn-swap" onClick={onSwap} title="Find a different item">
            ↺ Swap
          </button>
          <button className="btn-tryon" onClick={onTryOn} title="See this on you">
            Try On
          </button>
        </div>
      </div>
    </div>
  )
}
