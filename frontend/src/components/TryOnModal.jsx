export default function TryOnModal({ item, loading, result, error, onClose }) {
  return (
    <div className="tryon-overlay" onClick={onClose}>
      <div className="tryon-modal" onClick={e => e.stopPropagation()}>
        <div className="tryon-header">
          <span>Virtual Try-On — {item.category}</span>
          <button className="tryon-close" onClick={onClose}>✕</button>
        </div>

        <div className="tryon-content">
          <div className="tryon-result-area">
            {loading && (
              <div className="loading" style={{ padding: '60px 0' }}>
                <div className="spinner" />
                <span>Generating (~30 sec on GPU)...</span>
              </div>
            )}
            {error && <p className="error" style={{ padding: 24 }}>{error}</p>}
            {result && (
              <img className="tryon-result-img" src={result} alt="Try-on result" />
            )}
            {!loading && !result && !error && (
              <div className="loading" style={{ padding: '60px 0' }}>
                <div className="spinner" />
              </div>
            )}
          </div>

          <div className="tryon-garment-panel">
            <p className="tryon-garment-label">Garment</p>
            {item.image_url && (
              <img className="tryon-garment-img" src={item.image_url} alt="Garment" />
            )}
            <p className="tryon-garment-desc">{item.description || item.category}</p>
          </div>
        </div>
      </div>
    </div>
  )
}
