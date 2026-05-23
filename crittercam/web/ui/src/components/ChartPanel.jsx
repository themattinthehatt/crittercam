// ChartPanel is a layout shell — it knows nothing about charts.
// children is a special React prop that receives whatever JSX is nested
// inside the component tag, the same way a Python context manager receives
// the block body. Any chart (or anything else) can be dropped inside.
export default function ChartPanel({ title, children }) {
  return (
    <div className="card bg-base-200 border border-base-300 p-5">
      <h2 className="text-xs uppercase tracking-widest text-base-content/60 font-normal mb-4">{title}</h2>
      {children}
    </div>
  )
}
