export default function TryOnModal({ piece, loading, resultUrl, error, onClose }) {
  return (
    <div className="tryon-overlay" onClick={onClose}>
      <div className="tryon-modal" onClick={e => e.stopPropagation()}>
        <div className="tryon-header">
          <span>Virtual Try-On — {piece?.name}</span>
          <button className="tryon-close" onClick={onClose}>✕</button>
        </div>
        <div className="tryon-body">
          <div className="tryon-result-area">
            {loading && (
              <div className="loading">
                <div className="spinner" />
                <span>Running try-on model… this takes ~30s on GPU</span>
              </div>
            )}
            {!loading && error && (
              <p className="error" style={{ padding: 24 }}>{error}</p>
            )}
            {!loading && resultUrl && (
              <img className="tryon-result-img" src={resultUrl} alt="Try-on result" />
            )}
          </div>
          {piece?.image_url && (
            <div className="tryon-garment-panel">
              <p className="tryon-garment-label">Garment</p>
              <img className="tryon-garment-img" src={piece.image_url} alt={piece.name} />
              <p className="tryon-garment-desc">{piece.brand} — {piece.price}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
