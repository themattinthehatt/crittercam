// onClick is a function passed in by the parent — the component calls it when
// clicked but has no knowledge of what it does. This is a callback pattern,
// identical in concept to passing a function as an argument in Python.
export default function Button({ label, onClick, variant = 'primary', size = 'md', disabled = false }) {
  const sizeClass = size === 'sm' ? 'btn-sm' : size === 'xs' ? 'btn-xs' : ''
  return (
    <button
      className={`btn ${sizeClass} ${variant === 'primary' ? 'btn-primary' : 'btn-ghost border border-base-content/20'}`}
      onClick={onClick}
      disabled={disabled}
    >
      {label}
    </button>
  )
}
