const BASE = '/api'

export async function analyzeSelfie(file, gender = 'unisex', stylePref = 'casual', budget = 'midrange') {
  const form = new FormData()
  form.append('file', file)
  form.append('gender', gender)
  form.append('style_pref', stylePref)
  form.append('budget', budget)
  const res = await fetch(`${BASE}/analyze`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Analysis failed')
  }
  return res.json()
}

export async function generateOutfit(session_id, feedback = null) {
  const res = await fetch(`${BASE}/outfit/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id, feedback }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Generation failed')
  }
  return res.json()
}
