import { useState } from 'react'

export default function FeedbackBar({ onFeedback, onDone, loading }) {
  const [rating, setRating] = useState(0)
  const [hover, setHover] = useState(0)
  const [text, setText] = useState('')

  const handleSubmit = () => {
    if (rating === 0 || loading) return
    onFeedback({ rating, text })
    setRating(0)
    setHover(0)
    setText('')
  }

  return (
    <div className="feedback-bar">
      <h3>How's this outfit? Tell us what to improve.</h3>

      <div className="star-rating">
        {[1, 2, 3, 4, 5].map((n) => (
          <span
            key={n}
            className={`star ${n <= (hover || rating) ? 'active' : ''}`}
            onClick={() => setRating(n)}
            onMouseEnter={() => setHover(n)}
            onMouseLeave={() => setHover(0)}
            role="button"
            aria-label={`Rate ${n} star${n !== 1 ? 's' : ''}`}
          >
            ★
          </span>
        ))}
      </div>

      <textarea
        className="feedback-input"
        placeholder="e.g. Love the pants, but the shirt is too formal. Want something more casual and add more color."
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={loading}
      />

      <div className="feedback-actions">
        <button className="btn-secondary" onClick={onDone} disabled={loading}>
          Save &amp; Done
        </button>
        <button
          className="btn-primary"
          onClick={handleSubmit}
          disabled={rating === 0 || loading}
        >
          {loading ? 'Generating...' : 'Try Another Outfit →'}
        </button>
      </div>
    </div>
  )
}
