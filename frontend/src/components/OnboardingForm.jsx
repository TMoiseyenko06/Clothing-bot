import { useState } from 'react'

const QUESTIONS = [
  {
    key: 'gender',
    label: 'How do you want to dress?',
    options: ["Men's", "Women's", 'Gender-neutral'],
  },
  {
    key: 'fit',
    label: 'Fit preference',
    options: ['Slim', 'Regular', 'Relaxed', 'Oversized'],
  },
  {
    key: 'budget',
    label: 'Budget range',
    options: ['Budget', 'Mid-range', 'Luxury'],
  },
  {
    key: 'occasion',
    label: 'Occasion',
    options: ['Everyday', 'Going out', 'Work', 'Streetwear', 'Formal'],
  },
]

export default function OnboardingForm({ onSubmit, loading, error }) {
  const [answers, setAnswers] = useState({ gender: '', fit: '', budget: '', occasion: '' })

  const isComplete = Object.values(answers).every(Boolean)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (isComplete && !loading) onSubmit(answers)
  }

  return (
    <div className="onboarding">
      <h2>Tell us about your style</h2>
      <p className="subtitle">
        A few quick answers help us build an outfit that actually fits your life.
      </p>

      <form onSubmit={handleSubmit}>
        {QUESTIONS.map(({ key, label, options }) => (
          <div key={key} className="form-group">
            <label>{label}</label>
            <div className="option-grid">
              {options.map((opt) => (
                <button
                  key={opt}
                  type="button"
                  className={`option-btn ${answers[key] === opt ? 'selected' : ''}`}
                  onClick={() => setAnswers((a) => ({ ...a, [key]: opt }))}
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>
        ))}

        {error && <p className="error">{error}</p>}

        <div className="onboarding-actions">
          <button type="submit" className="btn-primary" disabled={!isComplete || loading}>
            {loading ? 'Building your outfit...' : 'Generate My Outfit →'}
          </button>
        </div>
      </form>
    </div>
  )
}
