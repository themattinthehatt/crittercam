import StatsBar from './components/StatsBar.jsx'
import DetectionGrid from './components/DetectionGrid.jsx'
import './App.css'

export default function App() {
  return (
    <div className="app">
      <header>
        <h1>crittercam</h1>
        <p>Wildlife detection dashboard</p>
      </header>
      <main>
        <StatsBar />
        <DetectionGrid />
      </main>
    </div>
  )
}
