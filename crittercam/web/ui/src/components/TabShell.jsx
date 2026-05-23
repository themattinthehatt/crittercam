// tab names drive both the nav buttons and the active highlight.
// adding a new tab is a one-line change here.
const TABS = ['home', 'browse', 'analytics']

// TabShell owns the chrome (header + tab bar) but not the state.
// activeTab and onTabChange are lifted up to App so that both the tab bar
// and the content area can read and set the same value — neither can own it
// alone because each needs to observe what the other does.
export default function TabShell({ activeTab, onTabChange, children }) {
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
            onClick={() => onTabChange(tab)}
          >
            {tab}
          </button>
        ))}
      </nav>

      <main>{children}</main>
    </div>
  )
}
