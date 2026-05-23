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

const INDIVIDUALS = [
  { id: 1, nickname: 'Mittens' },
  { id: 2, nickname: null },
  { id: 3, nickname: 'Bandit' },
]

export const SpeciesMode = {
  args: {
    browseMode: 'species',
    species: SPECIES,
    selectedSpecies: '',
    individuals: INDIVIDUALS,
    selectedIndividual: '',
    dateFrom: '',
    dateTo: '',
  },
}

export const SpeciesSelected = {
  args: {
    browseMode: 'species',
    species: SPECIES,
    selectedSpecies: 'raccoon',
    individuals: INDIVIDUALS,
    selectedIndividual: '',
    dateFrom: '',
    dateTo: '',
  },
}

export const IndividualMode = {
  args: {
    browseMode: 'individual',
    species: SPECIES,
    selectedSpecies: '',
    individuals: INDIVIDUALS,
    selectedIndividual: '',
    dateFrom: '',
    dateTo: '',
  },
}

export const IndividualSelected = {
  args: {
    browseMode: 'individual',
    species: SPECIES,
    selectedSpecies: '',
    individuals: INDIVIDUALS,
    selectedIndividual: '1',
    dateFrom: '',
    dateTo: '',
  },
}

export const WithDateRange = {
  args: {
    browseMode: 'species',
    species: SPECIES,
    selectedSpecies: '',
    individuals: INDIVIDUALS,
    selectedIndividual: '',
    dateFrom: '2026-03-01',
    dateTo: '2026-03-31',
  },
}
