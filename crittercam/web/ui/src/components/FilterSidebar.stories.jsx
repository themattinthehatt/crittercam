import FilterSidebar from './FilterSidebar'

export default {
  title: 'Domain/FilterSidebar',
  component: FilterSidebar,
  decorators: [
    Story => (
      <div style={{ width: '220px' }}>
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

export const NoFilters = {
  args: {
    species: SPECIES,
    selectedSpecies: '',
    dateFrom: '',
    dateTo: '',
  },
}

export const SpeciesSelected = {
  args: {
    species: SPECIES,
    selectedSpecies: 'raccoon',
    dateFrom: '',
    dateTo: '',
  },
}

export const DateRangeOnly = {
  args: {
    species: SPECIES,
    selectedSpecies: '',
    dateFrom: '2026-03-01',
    dateTo: '2026-03-31',
  },
}

export const AllFilters = {
  args: {
    species: SPECIES,
    selectedSpecies: 'domestic cat',
    dateFrom: '2026-03-01',
    dateTo: '2026-03-31',
  },
}
