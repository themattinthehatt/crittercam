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
