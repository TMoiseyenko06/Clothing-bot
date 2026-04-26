import { useState } from 'react'

const CATEGORY_EMOJI = {
  Top: '👕',
  Bottom: '👖',
  Shoes: '👟',
  Outerwear: '🧥',
  Accessory: '⌚',
}

export default function OutfitCard({ piece }) {
  const [imgError, setImgError] = useState(false)

  const imgSrc = !imgError
    ? (piece.cached_image || piece.image_url)
    : piece.cached_image && piece.cached_image !== piece.image_url
      ? piece.image_url  // fallback to remote if cached failed
      : null

  return (
    <div className="outfit-card">
      {imgSrc ? (
        <img
          className="outfit-card-image"
          src={imgSrc}
          alt={piece.name}
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
        <div className="outfit-card-price">{piece.price}</div>
        <div className="outfit-card-why">{piece.why}</div>
        {piece.link && (
          <a
            href={piece.link}
            target="_blank"
            rel="noopener noreferrer"
            className="outfit-card-link"
          >
            Shop Now →
          </a>
        )}
      </div>
    </div>
  )
}
