import { fn, userEvent, expect, within } from 'storybook/test'
import DetectionModal from './DetectionModal'

const SPECIES_LIST = [
  'domestic cat',
  'red fox',
  'virginia opossum',
  'vulpes vulpes',
  'white-tailed deer',
]

const INDIVIDUAL_LIST = [
  { id: 1, species_leaf: 'domestic cat', nickname: 'Mittens' },
  { id: 2, species_leaf: 'red fox', nickname: null },
  { id: 3, species_leaf: 'red fox', nickname: 'Bandit' },
]

export default {
  title: 'Domain/DetectionModal',
  component: DetectionModal,
  // modal uses fixed positioning so no width constraint is needed
  args: {
    isFavorite: false,
    speciesList: SPECIES_LIST,
    individualList: INDIVIDUAL_LIST,
  },
}

const BASE = {
  id: 1,
  label: 'abc123;animalia;chordata;mammalia;carnivora;canidae;vulpes;vulpes vulpes',
  confidence: 0.91,
  crop_url: 'https://placehold.co/300x200',
  image_url: 'https://placehold.co/800x600',
  captured_at: '2026-03-14T02:17:00',
  temperature_c: 4.2,
  individual_id: null,
  nickname: null,
  bbox: { x: 0.2, y: 0.25, w: 0.35, h: 0.45 },
}

const CALLBACKS = {
  onClose: () => {},
  onPrev: () => {},
  onNext: () => {},
  onFavorite: () => {},
  onDelete: () => {},
  onSave: () => {},
}

// middle of a list — both arrows visible, not favorited
export const Middle = {
  args: {
    detection: BASE,
    hasPrev: true,
    hasNext: true,
    isFavorite: false,
    ...CALLBACKS,
    onClose: fn(),
    onPrev: fn(),
    onNext: fn(),
  },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    // both nav arrows present
    await expect(canvas.getByText('‹')).toBeInTheDocument()
    await expect(canvas.getByText('›')).toBeInTheDocument()
    // clicking prev/next fires the right callbacks
    await userEvent.click(canvas.getByText('‹'))
    await expect(args.onPrev).toHaveBeenCalledOnce()
    await userEvent.click(canvas.getByText('›'))
    await expect(args.onNext).toHaveBeenCalledOnce()
    // close button fires onClose
    await userEvent.click(canvas.getByRole('button', { name: '✕' }))
    await expect(args.onClose).toHaveBeenCalledOnce()
  },
}

// same but favorited — star should appear solid yellow
export const Favorited = {
  args: {
    detection: BASE,
    hasPrev: true,
    hasNext: true,
    isFavorite: true,
    ...CALLBACKS,
  },
}

// first item in a list — only next arrow
export const First = {
  args: {
    detection: BASE,
    hasPrev: false,
    hasNext: true,
    ...CALLBACKS,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement)
    await expect(canvas.queryByText('‹')).not.toBeInTheDocument()
    await expect(canvas.getByText('›')).toBeInTheDocument()
  },
}

// last item in a list — only prev arrow
export const Last = {
  args: {
    detection: BASE,
    hasPrev: true,
    hasNext: false,
    ...CALLBACKS,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement)
    await expect(canvas.getByText('‹')).toBeInTheDocument()
    await expect(canvas.queryByText('›')).not.toBeInTheDocument()
  },
}

// clicking the star calls onFavorite
export const FavoriteToggle = {
  args: {
    detection: BASE,
    hasPrev: true,
    hasNext: true,
    isFavorite: false,
    ...CALLBACKS,
    onFavorite: fn(),
  },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    await userEvent.click(canvas.getByTitle('Favorite'))
    await expect(args.onFavorite).toHaveBeenCalledOnce()
  },
}

// clicking trash shows confirmation; clicking delete fires onDelete
export const DeleteConfirm = {
  args: {
    detection: BASE,
    hasPrev: true,
    hasNext: true,
    ...CALLBACKS,
    onDelete: fn(),
  },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    await userEvent.click(canvas.getByTitle('Delete'))
    await expect(canvas.getByText('Delete this observation?')).toBeInTheDocument()
    await userEvent.click(canvas.getByRole('button', { name: 'delete' }))
    await expect(args.onDelete).toHaveBeenCalledOnce()
  },
}

// clicking trash then cancel dismisses without calling onDelete
export const DeleteCancel = {
  args: {
    detection: BASE,
    hasPrev: true,
    hasNext: true,
    ...CALLBACKS,
    onDelete: fn(),
  },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    await userEvent.click(canvas.getByTitle('Delete'))
    await expect(canvas.getByText('Delete this observation?')).toBeInTheDocument()
    await userEvent.click(canvas.getByRole('button', { name: 'cancel' }))
    await expect(canvas.queryByText('Delete this observation?')).not.toBeInTheDocument()
    await expect(args.onDelete).not.toHaveBeenCalled()
  },
}

// clicking pencil enters edit mode — species and individual dropdowns appear
export const EditMode = {
  args: {
    detection: BASE,
    hasPrev: true,
    hasNext: true,
    ...CALLBACKS,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement)
    await userEvent.click(canvas.getByTitle('Edit'))
    await expect(canvas.getByText('editing')).toBeInTheDocument()
    // species dropdown pre-populated with current leaf
    const selects = canvas.getAllByRole('combobox')
    await expect(selects[0]).toHaveValue('vulpes vulpes')
    // individual dropdown defaults to — none — since detection has no individual
    await expect(selects[1]).toHaveValue('')
  },
}

// changing species and saving calls onSave with the new leaf and individual_id
export const EditSave = {
  args: {
    detection: BASE,
    hasPrev: true,
    hasNext: true,
    ...CALLBACKS,
    onSave: fn(),
  },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    await userEvent.click(canvas.getByTitle('Edit'))
    // change species to domestic cat
    await userEvent.selectOptions(canvas.getAllByRole('combobox')[0], 'domestic cat')
    // assign Mittens (id 1) as individual
    await userEvent.selectOptions(canvas.getAllByRole('combobox')[1], '1')
    await userEvent.click(canvas.getByRole('button', { name: 'save' }))
    await expect(args.onSave).toHaveBeenCalledWith('domestic cat', 1)
    // returns to view mode
    await expect(canvas.queryByText('editing')).not.toBeInTheDocument()
  },
}

// cancelling edit mode reverts without calling onSave
export const EditCancel = {
  args: {
    detection: BASE,
    hasPrev: true,
    hasNext: true,
    ...CALLBACKS,
    onSave: fn(),
  },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    await userEvent.click(canvas.getByTitle('Edit'))
    await userEvent.selectOptions(canvas.getAllByRole('combobox')[0], 'domestic cat')
    await userEvent.click(canvas.getByRole('button', { name: 'cancel' }))
    await expect(args.onSave).not.toHaveBeenCalled()
    // species label reverts to original value
    await expect(canvas.getByText('vulpes vulpes')).toBeInTheDocument()
  },
}

// detection with an existing individual — individual dropdown pre-populated
export const EditModeWithIndividual = {
  args: {
    detection: { ...BASE, individual_id: 3, nickname: 'Bandit' },
    hasPrev: true,
    hasNext: true,
    ...CALLBACKS,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement)
    await userEvent.click(canvas.getByTitle('Edit'))
    const selects = canvas.getAllByRole('combobox')
    await expect(selects[1]).toHaveValue('3')
  },
}

export const NoBbox = {
  args: {
    detection: { ...BASE, bbox: null },
    hasPrev: true,
    hasNext: true,
    ...CALLBACKS,
  },
}

export const WithIndividual = {
  args: {
    detection: {
      ...BASE,
      individual_id: 3,
      nickname: 'Mittens',
    },
    hasPrev: true,
    hasNext: true,
    ...CALLBACKS,
  },
}

export const NoTemperature = {
  args: {
    detection: { ...BASE, bbox: null, temperature_c: null },
    hasPrev: true,
    hasNext: true,
    ...CALLBACKS,
  },
}

export const Blank = {
  args: {
    detection: {
      ...BASE,
      label: 'abc123;;;;;blank',
      confidence: 0.98,
      crop_url: null,
      bbox: null,
      temperature_c: null,
    },
    hasPrev: true,
    hasNext: true,
    ...CALLBACKS,
  },
}
