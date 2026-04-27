import { useState, useRef } from 'react'

const CATEGORY_EMOJI = {
  Top: '👕',
  Bottom: '👖',
  Shoes: '👟',
  Outerwear: '🧥',
  Accessory: '👜',
}

export default function OutfitCard({ piece, onTryOn, onImageUpdate }) {
  const [imgError, setImgError] = useState(false)
  const [showReplace, setShowReplace] = useState(false)
  const [urlInput, setUrlInput] = useState('')
  const fileRef = useRef()

  const handleFile = (e) => {
    const f = e.target.files[0]
    if (f) {
      onImageUpdate(piece.category, f, null)
      setShowReplace(false)
    }
  }

  const handleUrl = () => {
    if (urlInput.trim()) {
      onImageUpdate(piece.category, null, urlInput.trim())
      setUrlInput('')
      setShowReplace(false)
    }
  }

  return (
    <div className="outfit-card">
      <div className="outfit-card-img-wrap">
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
        <button
          className="btn-replace-img"
          title="Replace image"
          onClick={() => setShowReplace(s => !s)}
        >
          📷
        </button>
      </div>

      {showReplace && (
        <div className="replace-panel">
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={handleFile}
          />
          <button className="replace-opt" onClick={() => fileRef.current.click()}>
            Upload file
          </button>
          <div className="replace-url-row">
            <input
              className="replace-url-input"
              type="url"
              placeholder="Or paste image URL…"
              value={urlInput}
              onChange={e => setUrlInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleUrl()}
            />
            <button className="replace-url-go" onClick={handleUrl}>→</button>
          </div>
          <button className="replace-cancel" onClick={() => setShowReplace(false)}>Cancel</button>
        </div>
      )}

      <div className="outfit-card-body">
        <div className="outfit-card-category">{piece.category}</div>
        <div className="outfit-card-name">{piece.name}</div>
        <div className="outfit-card-brand">{piece.brand}</div>
        {piece.why && <div className="outfit-card-why">{piece.why}</div>}
        <div className="outfit-card-footer">
          {piece.price && <span className="outfit-card-price">{piece.price}</span>}
          <div className="outfit-card-actions-row">
            {piece.link && (
              <a className="btn-shop" href={piece.link} target="_blank" rel="noopener noreferrer">
                Shop
              </a>
            )}
            <button
              className="btn-tryon"
              onClick={() => onTryOn(piece)}
              title="Virtual try-on"
            >
              Try On
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
