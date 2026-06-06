import { useState } from 'react'
import TabShell from './components/TabShell.jsx'
import StatsBar from './components/StatsBar.jsx'
import DetectionGrid from './components/DetectionGrid.jsx'
import RecentBySpecies from './components/RecentBySpecies.jsx'
import AnalyticsTab from './components/AnalyticsTab.jsx'
import './App.css'

export default function App() {
  // activeTab lives here in App — the lowest common ancestor of the tab bar
  // and the tab content. neither the nav nor the content panels can own this
  // state themselves, because each needs to read what the other sets.
  const [activeTab, setActiveTab] = useState('home')

  return (
    <TabShell activeTab={activeTab} onTabChange={setActiveTab}>
      {activeTab === 'home' && (
        <>
          <StatsBar />
          <RecentBySpecies />
        </>
      )}
      {activeTab === 'browse' && <DetectionGrid />}
      {activeTab === 'analytics' && <AnalyticsTab />}
    </TabShell>
  )
}
