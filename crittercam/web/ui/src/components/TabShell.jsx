const TABS = ['home', 'browse', 'analytics']

export default function TabShell({ activeTab, onTabChange, children }) {
  return (
    <div className="max-w-5xl mx-auto px-8 py-8">
      <header className="mb-8 text-center">
        <h1 className="text-3xl font-bold mb-1">crittercam</h1>
        <p className="text-base-content/60">Wildlife detection dashboard</p>
      </header>

      <div className="tabs tabs-border mb-8">
        {TABS.map(tab => (
          <button
            key={tab}
            className={`tab capitalize ${activeTab === tab ? 'tab-active' : ''}`}
            onClick={() => onTabChange(tab)}
          >
            {tab}
          </button>
        ))}
      </div>

      <main>{children}</main>
    </div>
  )
}
