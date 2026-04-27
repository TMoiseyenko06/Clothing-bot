import { useState, useRef } from 'react'

export default function SelfieUpload({ onUpload, loading, error }) {
  const [preview, setPreview] = useState(null)
  const [file, setFile] = useState(null)
  const [drag, setDrag] = useState(false)
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
    e.stopPropagation()
    setPreview(null)
    setFile(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div className="selfie-upload">
      <h1>AI Outfit Builder</h1>
      <p className="subtitle">
        Upload a photo of yourself and get a personalized outfit recommendation
        based on your coloring, style, and preferences.
      </p>

      <div
        className={`upload-zone ${drag ? 'drag-over' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={handleDrop}
        onClick={() => !preview && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          onChange={(e) => handleFile(e.target.files[0])}
          style={{ display: 'none' }}
        />

        {preview ? (
          <div className="upload-preview">
            <img src={preview} alt="Your photo" />
            <p className="file-name">{file?.name}</p>
            <button
              className="btn-secondary"
              style={{ marginTop: 12, fontSize: '0.82rem', padding: '8px 16px' }}
              onClick={clearPhoto}
            >
              Change photo
            </button>
          </div>
        ) : (
          <>
            <div className="upload-icon">📷</div>
            <p>Click or drag to upload a photo</p>
            <p className="hint">JPG, PNG, or WEBP — your face and outfit are most helpful</p>
          </>
        )}
      </div>

      {error && <p className="error">{error}</p>}

      {preview && (
        <button
          className="btn-primary"
          style={{ marginTop: 24, width: '100%' }}
          onClick={() => !loading && onUpload(file)}
          disabled={loading}
        >
          {loading ? 'Analyzing your style...' : 'Analyze My Style →'}
        </button>
      )}
    </div>
  )
}
