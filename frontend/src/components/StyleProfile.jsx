const ATTR_LABELS = {
  gender: 'Gender',
  style_pref: 'Style',
  budget: 'Budget',
  coloring: 'Skin Tone',
  undertone: 'Undertone',
  build: 'Body Type',
  hair: 'Hair Color',
}

const BUDGET_DISPLAY = {
  budget: 'Under $50',
  midrange: '$50–$150',
  premium: '$150–$300',
  luxury: '$300+',
}

function cleanLabel(key, str) {
  if (key === 'budget') return BUDGET_DISPLAY[str] || str
  return str
    .replace(/ (style|skin tone|body type|undertones?|hair)$/i, '')
    .trim()
}

export default function StyleProfile({ profile, selfieUrl }) {
  return (
    <div className="style-profile">
      {selfieUrl && (
        <img className="profile-selfie" src={selfieUrl} alt="Your photo" />
      )}
      <div className="profile-attrs">
        {Object.entries(ATTR_LABELS).map(([key, label]) =>
          profile[key] ? (
            <div key={key} className="profile-attr">
              <span className="profile-attr-label">{label}</span>
              <span className="profile-attr-value">{cleanLabel(key, profile[key])}</span>
            </div>
          ) : null
        )}
      </div>
    </div>
  )
}
