import { useState } from 'react'
import TabShell from './TabShell'

export default {
  title: 'Layout/TabShell',
  component: TabShell,
}

// TabShell is a controlled component — activeTab and onTabChange are owned
// by the parent. This wrapper adds local state so the story is interactive:
// clicking tabs actually switches them in Storybook.
function InteractiveShell({ initialTab }) {
  const [activeTab, setActiveTab] = useState(initialTab)
  return (
    <TabShell activeTab={activeTab} onTabChange={setActiveTab}>
      <p style={{ color: '#888', fontSize: '0.9rem' }}>
        content for <strong>{activeTab}</strong> tab
      </p>
    </TabShell>
  )
}

export const HomeActive = {
  render: () => <InteractiveShell initialTab="home" />,
}

export const BrowseActive = {
  render: () => <InteractiveShell initialTab="browse" />,
}

export const AnalyticsActive = {
  render: () => <InteractiveShell initialTab="analytics" />,
}
