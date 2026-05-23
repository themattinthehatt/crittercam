// ChartPanel is a layout shell — it knows nothing about charts.
// children is a special React prop that receives whatever JSX is nested
// inside the component tag, the same way a Python context manager receives
// the block body. Any chart (or anything else) can be dropped inside.
export default function ChartPanel({ title, children }) {
  return (
    <div className="chart-panel">
      <h2 className="chart-panel__title">{title}</h2>
      {children}
    </div>
  )
}
