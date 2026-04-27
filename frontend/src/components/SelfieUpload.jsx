import { useState, useRef } from 'react'

const GENDERS = ['Men', 'Women', 'Unisex']
const STYLES = ['Casual', 'Formal', 'Streetwear', 'Minimalist', 'Sporty', 'Vintage', 'Bohemian', 'Smart Casual']
const BUDGETS = [
  { label: 'Budget  <$50', value: 'budget' },
  { label: 'Mid  $50–$150', value: 'midrange' },
  { label: 'Premium  $150–$300', value: 'premium' },
  { label: 'Luxury  $300+', value: 'luxury' },
]

function Chips({ options, value, onChange }) {
  return (
    <div className="chip-group">
      {options.map(opt => {
        const label = typeof opt === 'string' ? opt : opt.label
        const val = typeof opt === 'string' ? opt.toLowerCase() : opt.value
        return (
          <button
            key={val}
            type="button"
            className={`chip ${value === val ? 'chip-active' : ''}`}
            onClick={() => onChange(val)}
          >
            {label}
          </button>
        )
      })}
    </div>
  )
}

export default function SelfieUpload({ onUpload, loading, error }) {
  const [preview, setPreview] = useState(null)
  const [file, setFile] = useState(null)
  const [drag, setDrag] = useState(false)
  const [gender, setGender] = useState('unisex')
  const [stylePref, setStylePref] = useState('casual')
  const [budget, setBudget] = useState('midrange')
  const inputRef = useRef()

  const handleFile = (f) => {
    if (!f || !f.type.startsWith('image/')) return
    setFile(f)
    setPreview(URL.createObjectURL(f))
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDrag(false)
    handleFile(e.dataTransfer.files[0])
  }

  const clearPhoto = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setPreview(null)
    setFile(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div className="selfie-upload">
      <h1>AI Outfit Builder</h1>
      <p className="subtitle">
        Upload a photo and get a personalized outfit recommendation with real, shoppable products.
      </p>

      <label
        className={`upload-zone ${drag ? 'drag-over' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={handleDrop}
        style={{ cursor: 'pointer', display: 'block' }}
      >
        <input
          ref={inputRef}
          id="selfie-input"
          type="file"
          accept="image/*"
          onChange={(e) => handleFile(e.target.files[0])}
          style={{ display: 'none' }}
        />
        {preview ? (
          <div className="upload-preview">
            <img src={preview} alt="Your photo" />
            <p className="file-name">{file?.name}</p>
            <button className="btn-secondary" style={{ marginTop: 12, fontSize: '0.82rem', padding: '8px 16px' }} onClick={clearPhoto}>
              Change photo
            </button>
          </div>
        ) : (
          <>
            <div className="upload-icon">📷</div>
            <p>Click or drag to upload a photo</p>
            <p className="hint">JPG, PNG, or WEBP</p>
          </>
        )}
      </label>

      <div className="prefs">
        <div className="pref-group">
          <label className="pref-label">Gender</label>
          <Chips options={GENDERS} value={gender} onChange={setGender} />
        </div>
        <div className="pref-group">
          <label className="pref-label">Style</label>
          <Chips options={STYLES} value={stylePref} onChange={setStylePref} />
        </div>
        <div className="pref-group">
          <label className="pref-label">Budget</label>
          <Chips options={BUDGETS} value={budget} onChange={setBudget} />
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      {preview && (
        <button
          className="btn-primary"
          style={{ marginTop: 24, width: '100%' }}
          onClick={() => !loading && onUpload(file, gender, stylePref, budget)}
          disabled={loading}
        >
          {loading ? 'Analyzing your style...' : 'Analyze My Style →'}
        </button>
      )}
    </div>
  )
}
