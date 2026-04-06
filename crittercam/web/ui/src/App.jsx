import { useState, useEffect } from 'react'
import StatsBar from './components/StatsBar.jsx'
import DetectionViewer from './components/DetectionViewer.jsx'
import './App.css'

export default function App() {
  // firstId is fetched once on mount so we know where DetectionViewer should start.
  // We keep it in App state so it can be passed down as a prop.
  const [firstId, setFirstId] = useState(null)

  useEffect(() => {
    fetch('/api/detections/first')
      .then(response => response.json())
      .then(data => setFirstId(data.id))
  }, [])

  return (
    <div className="app">
      <header>
        <h1>crittercam</h1>
        <p>Wildlife detection dashboard</p>
      </header>
      <main>
        <StatsBar />
        {/* Only render DetectionViewer once we have a valid id.
            The && operator is React's standard way to conditionally render:
            if firstId is null (falsy), nothing renders;
            once it has a value, DetectionViewer appears. */}
        {firstId && <DetectionViewer firstId={firstId} />}
      </main>
    </div>
  )
}
