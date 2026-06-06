import FilterSidebar from './FilterSidebar'

export default {
  title: 'Domain/FilterSidebar',
  component: FilterSidebar,
  decorators: [
    Story => (
      // FilterSidebar is absolutely positioned to the left of its relative
      // parent, so the parent needs left margin to bring the sidebar on-screen.
      <div style={{ position: 'relative', marginLeft: '200px', height: '300px' }}>
        <Story />
      </div>
    ),
  ],
}

const SPECIES = [
  'white-tailed deer',
  'domestic cat',
  'raccoon',
  'virginia opossum',
  'red fox',
]

const INDIVIDUALS = [
  { id: 1, nickname: 'Mittens' },
  { id: 2, nickname: null },
  { id: 3, nickname: 'Bandit' },
]

const DEPLOYMENTS = [
  { id: 1, deployment_name: 'Backyard feeder' },
  { id: 2, deployment_name: 'Trail cam east' },
  { id: 3, deployment_name: null },
]

const BASE = {
  species: SPECIES,
  individuals: INDIVIDUALS,
  deployments: DEPLOYMENTS,
  selectedSpecies: '',
  selectedIndividual: '',
  selectedDeployment: '',
  dateFrom: '',
  dateTo: '',
}

export const SpeciesMode = {
  args: { ...BASE, browseMode: 'species' },
}

export const SpeciesSelected = {
  args: { ...BASE, browseMode: 'species', selectedSpecies: 'raccoon' },
}

export const IndividualMode = {
  args: { ...BASE, browseMode: 'individual' },
}

export const IndividualSelected = {
  args: { ...BASE, browseMode: 'individual', selectedIndividual: '1' },
}

export const FavoritedMode = {
  args: { ...BASE, browseMode: 'favorited', onChange: () => {} },
}

export const DeploymentSelected = {
  args: { ...BASE, browseMode: 'species', selectedDeployment: '1' },
}

export const WithDateRange = {
  args: { ...BASE, browseMode: 'species', dateFrom: '2026-03-01', dateTo: '2026-03-31' },
}
