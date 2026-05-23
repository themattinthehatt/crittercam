// onClick is a function passed in by the parent — the component calls it when
// clicked but has no knowledge of what it does. This is a callback pattern,
// identical in concept to passing a function as an argument in Python.
export default function Button({ label, onClick, variant = 'primary', disabled = false }) {
  return (
    <button
      className={`btn ${variant === 'primary' ? 'btn-primary' : 'btn-ghost'}`}
      onClick={onClick}
      disabled={disabled}
    >
      {label}
    </button>
  )
}
