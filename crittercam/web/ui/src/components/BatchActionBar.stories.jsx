import { fn, userEvent, expect, within } from 'storybook/test'
import BatchActionBar from './BatchActionBar'

export default {
  title: 'Domain/BatchActionBar',
  component: BatchActionBar,
  args: {
    onClear: fn(),
    onDelete: fn(),
    onFavorite: fn(),
    onEdit: fn(),
    onDeleteConfirm: fn(),
    onDeleteCancel: fn(),
    showDeleteConfirm: false,
  },
}

export const Default = {
  args: { count: 3, allFavorited: false },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    await expect(canvas.getByText('3 selected')).toBeInTheDocument()
    await userEvent.click(canvas.getByRole('button', { name: 'clear' }))
    await expect(args.onClear).toHaveBeenCalledOnce()
  },
}

export const AllFavorited = {
  args: { count: 2, allFavorited: true },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement)
    await expect(canvas.getByTitle('Unfavorite selected')).toBeInTheDocument()
  },
}

export const SingleSelected = {
  args: { count: 1, allFavorited: false },
}

export const ActionButtons = {
  args: {
    count: 4,
    allFavorited: false,
    onDelete: fn(),
    onFavorite: fn(),
    onEdit: fn(),
  },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    await userEvent.click(canvas.getByTitle('Delete selected'))
    await expect(args.onDelete).toHaveBeenCalledOnce()
    await userEvent.click(canvas.getByTitle('Favorite selected'))
    await expect(args.onFavorite).toHaveBeenCalledOnce()
    await userEvent.click(canvas.getByTitle('Edit selected'))
    await expect(args.onEdit).toHaveBeenCalledOnce()
  },
}

// clicking trash shows confirmation bar
export const DeleteConfirm = {
  args: { count: 3, allFavorited: false, showDeleteConfirm: true, onDeleteConfirm: fn(), onDeleteCancel: fn() },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    await expect(canvas.getByText('Delete 3 observations?')).toBeInTheDocument()
    await userEvent.click(canvas.getByRole('button', { name: 'delete' }))
    await expect(args.onDeleteConfirm).toHaveBeenCalledOnce()
  },
}

// cancel dismisses the confirmation without deleting
export const DeleteCancel = {
  args: { count: 3, allFavorited: false, showDeleteConfirm: true, onDeleteConfirm: fn(), onDeleteCancel: fn() },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    await expect(canvas.getByText('Delete 3 observations?')).toBeInTheDocument()
    await userEvent.click(canvas.getByRole('button', { name: 'cancel' }))
    await expect(args.onDeleteCancel).toHaveBeenCalledOnce()
    await expect(args.onDeleteConfirm).not.toHaveBeenCalled()
  },
}

// singular copy for a single observation
export const DeleteConfirmSingular = {
  args: { count: 1, allFavorited: false, showDeleteConfirm: true },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement)
    await expect(canvas.getByText('Delete 1 observation?')).toBeInTheDocument()
  },
}
