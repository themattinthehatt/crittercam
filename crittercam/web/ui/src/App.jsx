import StatsBar from './components/StatsBar.jsx'
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
      </main>
    </div>
  )
}
