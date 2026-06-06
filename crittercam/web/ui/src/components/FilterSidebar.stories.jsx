import { expect, fn, userEvent, within } from 'storybook/test'
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

export const AnalyticsMode = {
  args: {
    showBrowseControls: false,
    deployments: DEPLOYMENTS,
    selectedDeployment: '',
    dateFrom: '',
    dateTo: '',
  },
}

export const WithDateRange = {
  args: { ...BASE, browseMode: 'species', dateFrom: '2026-03-01', dateTo: '2026-03-31' },
}

// ---------------------------------------------------------------------------
// Interaction tests
// ---------------------------------------------------------------------------

// Selecting a deployment calls onChange with the chosen deployment id.
export const DeploymentSelectionCallsOnChange = {
  args: { ...BASE, browseMode: 'species', onChange: fn() },
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement)
    await userEvent.selectOptions(
      canvas.getByRole('combobox', { name: 'deployment' }),
      '1',
    )
    await expect(args.onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ selectedDeployment: '1' }),
    )
  },
}

// Switching browse mode must preserve the active deployment in the onChange payload.
export const BrowseModeChangePreservesDeployment = {
  args: { ...BASE, browseMode: 'species', selectedDeployment: '1', onChange: fn() },
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement)
    await userEvent.selectOptions(
      canvas.getByRole('combobox', { name: 'browse by' }),
      'individual',
    )
    await expect(args.onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ browseMode: 'individual', selectedDeployment: '1' }),
    )
  },
}

// Clear button resets selectedDeployment along with all other filters.
export const ClearResetsDeployment = {
  args: { ...BASE, browseMode: 'species', selectedDeployment: '1', onChange: fn() },
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement)
    await userEvent.click(canvas.getByRole('button', { name: /clear filters/i }))
    await expect(args.onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ selectedDeployment: '' }),
    )
  },
}

// Clear button must appear whenever only selectedDeployment is set (hasFilters logic).
export const ClearVisibleWithDeploymentOnly = {
  args: { ...BASE, browseMode: 'favorited', selectedDeployment: '2', onChange: fn() },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement)
    await expect(canvas.getByRole('button', { name: /clear filters/i })).toBeTruthy()
  },
}
