export default function Badge({ label, variant, confidence }) {
  let className = `badge badge--${variant}`

  if (variant === 'confidence') {
    if (confidence >= 0.7) className += ' badge--high'
    else if (confidence >= 0.4) className += ' badge--medium'
    else className += ' badge--low'
  }

  return <span className={className}>{label}</span>
}
