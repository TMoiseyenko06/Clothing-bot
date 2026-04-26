import OutfitCard from './OutfitCard'

export default function OutfitGrid({ outfit }) {
  if (!outfit) return null

  return (
    <div className="outfit-grid-container">
      <div className="outfit-concept">
        {outfit.outfit_concept}
        {outfit.pieces?.length > 0 && (
          <span className="piece-count"> — {outfit.pieces.length} pieces</span>
        )}
      </div>
      <div className="outfit-grid">
        {outfit.pieces?.map((piece, i) => (
          <OutfitCard key={i} piece={piece} />
        ))}
      </div>
    </div>
  )
}
