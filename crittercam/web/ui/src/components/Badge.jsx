export default function Badge({ label, variant, confidence }) {
  let className = 'badge badge-sm'

  if (variant === 'confidence') {
    if (confidence >= 0.7) className += ' badge-success'
    else if (confidence >= 0.4) className += ' badge-warning'
    else className += ' badge-error'
  } else if (variant === 'species') {
    className += ' badge-primary'
  } else if (variant === 'blank') {
    className += ' badge-neutral'
  }

  return <span className={className}>{label}</span>
}
