import OutfitCard from './OutfitCard'

const CATEGORY_ORDER = ['Top', 'Bottom', 'Shoes', 'Outerwear']

export default function OutfitGrid({ outfit, loading, onRefresh, onSwap, onTryOn }) {
  const items = CATEGORY_ORDER.map(cat => outfit[cat]).filter(Boolean)

  return (
    <div className="outfit-grid-container">
      <div className="outfit-grid-header">
        <h2 className="outfit-title">Your Outfit</h2>
        <button className="btn-secondary" onClick={onRefresh} disabled={loading}>
          {loading ? 'Finding...' : '↺ Regenerate'}
        </button>
      </div>
      <div className="outfit-grid">
        {items.map(item => (
          <OutfitCard
            key={item.id}
            item={item}
            onSwap={() => onSwap(item.category)}
            onTryOn={() => onTryOn(item)}
          />
        ))}
        {items.length === 0 && (
          <p className="empty-outfit">No items found. Try regenerating.</p>
        )}
      </div>
    </div>
  )
}
