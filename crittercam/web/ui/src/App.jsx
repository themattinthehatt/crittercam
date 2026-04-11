import { useState } from 'react'
import StatsBar from './components/StatsBar.jsx'
import DetectionGrid from './components/DetectionGrid.jsx'
import RecentBySpecies from './components/RecentBySpecies.jsx'
import DetectionsOverTime from './components/DetectionsOverTime.jsx'
import './App.css'

// tab names drive both the nav buttons and the content switch below.
// keeping them in one array means adding a new tab is a one-line change.
const TABS = ['home', 'browse', 'analytics']

export default function App() {
  // activeTab lives here in App — the lowest common ancestor of the tab bar
  // and the tab content. neither the nav nor the content panels can own this
  // state themselves, because each needs to read what the other sets.
  const [activeTab, setActiveTab] = useState('home')

  return (
    <div className="app">
      <header>
        <h1>crittercam</h1>
        <p>Wildlife detection dashboard</p>
      </header>

      <nav className="tab-bar">
        {TABS.map(tab => (
          <button
            key={tab}
            className={`tab-button${activeTab === tab ? ' tab-button--active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </nav>

      <main>
        {activeTab === 'home' && (
          <>
            <StatsBar />
            <RecentBySpecies />
          </>
        )}
        {activeTab === 'browse' && <DetectionGrid />}
        {activeTab === 'analytics' && <DetectionsOverTime />}
      </main>
    </div>
  )
}
