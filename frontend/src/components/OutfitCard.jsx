import { useState } from 'react'

const CATEGORY_EMOJI = {
  Top: '👕',
  Bottom: '👖',
  Shoes: '👟',
  Outerwear: '🧥',
  Accessory: '👜',
}

export default function OutfitCard({ piece }) {
  const [imgError, setImgError] = useState(false)

  return (
    <div className="outfit-card">
      {piece.image_url && !imgError ? (
        <img
          className="outfit-card-image"
          src={piece.image_url}
          alt={piece.name || piece.category}
          onError={() => setImgError(true)}
          loading="lazy"
        />
      ) : (
        <div className="outfit-card-placeholder">
          {CATEGORY_EMOJI[piece.category] || '👗'}
        </div>
      )}
      <div className="outfit-card-body">
        <div className="outfit-card-category">{piece.category}</div>
        <div className="outfit-card-name">{piece.name}</div>
        <div className="outfit-card-brand">{piece.brand}</div>
        {piece.why && <div className="outfit-card-why">{piece.why}</div>}
        <div className="outfit-card-footer">
          {piece.price && <span className="outfit-card-price">{piece.price}</span>}
          {piece.link && (
            <a
              className="btn-shop"
              href={piece.link}
              target="_blank"
              rel="noopener noreferrer"
            >
              Shop
            </a>
          )}
        </div>
      </div>
    </div>
  )
}
