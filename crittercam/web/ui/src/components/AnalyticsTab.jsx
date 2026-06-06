import { useState, useEffect } from 'react'
import FilterSidebar from './FilterSidebar.jsx'
import DetectionsOverTime from './DetectionsOverTime.jsx'
import ActivityByHour from './ActivityByHour.jsx'

// AnalyticsTab owns the filter state for the analytics view (deployment + date range only)
// and passes the active filters down to each chart so they re-fetch on change.
export default function AnalyticsTab() {
  const [filters, setFilters] = useState({
    selectedDeployment: '',
    dateFrom: '',
    dateTo: '',
  })
  const [deploymentList, setDeploymentList] = useState([])

  useEffect(() => {
    fetch('/api/deployments')
      .then(r => r.json())
      .then(data => setDeploymentList(data))
  }, [])

  const handleFilterChange = ({ selectedDeployment, dateFrom, dateTo }) => {
    setFilters({ selectedDeployment, dateFrom, dateTo })
  }

  return (
    <div className="flex gap-6 items-start relative">
      <FilterSidebar
        showBrowseControls={false}
        deployments={deploymentList}
        selectedDeployment={filters.selectedDeployment}
        dateFrom={filters.dateFrom}
        dateTo={filters.dateTo}
        onChange={handleFilterChange}
      />
      <div className="flex-1 min-w-0 flex flex-col gap-6">
        <DetectionsOverTime
          deploymentId={filters.selectedDeployment}
          dateFrom={filters.dateFrom}
          dateTo={filters.dateTo}
        />
        <ActivityByHour
          deploymentId={filters.selectedDeployment}
          dateFrom={filters.dateFrom}
          dateTo={filters.dateTo}
        />
      </div>
    </div>
  )
}
