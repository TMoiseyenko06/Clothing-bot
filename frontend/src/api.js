const BASE = '/api'

export async function analyzeSelfie(file, gender = 'unisex', stylePref = 'casual') {
  const form = new FormData()
  form.append('file', file)
  form.append('gender', gender)
  form.append('style_pref', stylePref)
  const res = await fetch(`${BASE}/analyze`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Analysis failed')
  }
  return res.json()
}

export async function refreshOutfit(session_id) {
  const res = await fetch(`${BASE}/outfit/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Refresh failed')
  }
  return res.json()
}

export async function swapItem(session_id, category) {
  const res = await fetch(`${BASE}/outfit/swap`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id, category }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Swap failed')
  }
  return res.json()
}

export async function tryOn(session_id, item_id, category) {
  const res = await fetch(`${BASE}/tryon`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id, item_id, category }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Try-on failed')
  }
  return res.json()
}
