const ATTR_LABELS = {
  gender: 'Gender',
  style_pref: 'Style',
  coloring: 'Skin Tone',
  undertone: 'Undertone',
  build: 'Body Type',
  hair: 'Hair Color',
}

function cleanLabel(str) {
  return str
    .replace(/ (style|skin tone|body type|undertones?|hair)$/i, '')
    .replace(/\b(everyday|free-spirited|clean|light|medium|dark|lean|muscular|petite|curvy)\b/gi, s => s)
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
              <span className="profile-attr-value">{cleanLabel(profile[key])}</span>
            </div>
          ) : null
        )}
      </div>
    </div>
  )
}
