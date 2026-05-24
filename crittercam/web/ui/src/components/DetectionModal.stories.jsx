import { fn, userEvent, expect, within } from 'storybook/test'
import DetectionModal from './DetectionModal'

export default {
  title: 'Domain/DetectionModal',
  component: DetectionModal,
  // modal uses fixed positioning so no width constraint is needed
  args: {
    isFavorite: false,
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

// middle of a list — both arrows visible, not favorited
export const Middle = {
  args: {
    detection: BASE,
    hasPrev: true,
    hasNext: true,
    isFavorite: false,
    onClose: fn(),
    onPrev: fn(),
    onNext: fn(),
    onFavorite: fn(),
    onDelete: fn(),
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
    onClose: () => {},
    onPrev: () => {},
    onNext: () => {},
    onFavorite: () => {},
    onDelete: () => {},
  },
}

// first item in a list — only next arrow
export const First = {
  args: {
    detection: BASE,
    hasPrev: false,
    hasNext: true,
    onClose: () => {},
    onPrev: () => {},
    onNext: () => {},
    onFavorite: () => {},
    onDelete: () => {},
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
    onClose: () => {},
    onPrev: () => {},
    onNext: () => {},
    onFavorite: () => {},
    onDelete: () => {},
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
    onClose: () => {},
    onPrev: () => {},
    onNext: () => {},
    onFavorite: fn(),
    onDelete: () => {},
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
    onClose: () => {},
    onPrev: () => {},
    onNext: () => {},
    onFavorite: () => {},
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
    onClose: () => {},
    onPrev: () => {},
    onNext: () => {},
    onFavorite: () => {},
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

export const NoBbox = {
  args: {
    detection: { ...BASE, bbox: null },
    hasPrev: true,
    hasNext: true,
    onClose: () => {},
    onPrev: () => {},
    onNext: () => {},
    onFavorite: () => {},
    onDelete: () => {},
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
    onClose: () => {},
    onPrev: () => {},
    onNext: () => {},
    onFavorite: () => {},
    onDelete: () => {},
  },
}

export const NoTemperature = {
  args: {
    detection: { ...BASE, bbox: null, temperature_c: null },
    hasPrev: true,
    hasNext: true,
    onClose: () => {},
    onPrev: () => {},
    onNext: () => {},
    onFavorite: () => {},
    onDelete: () => {},
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
    onClose: () => {},
    onPrev: () => {},
    onNext: () => {},
    onFavorite: () => {},
    onDelete: () => {},
  },
}
