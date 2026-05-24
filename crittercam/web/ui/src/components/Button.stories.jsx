import { fn, userEvent, expect, within } from 'storybook/test'
import Button from './Button'

export default {
  title: 'Primitives/Button',
  component: Button,
}

export const Primary = {
  args: {
    label: 'Save',
    variant: 'primary',
    onClick: fn(),
  },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    await userEvent.click(canvas.getByRole('button'))
    await expect(args.onClick).toHaveBeenCalledOnce()
  },
}

export const Ghost = {
  args: {
    label: 'Cancel',
    variant: 'ghost',
    onClick: fn(),
  },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    await userEvent.click(canvas.getByRole('button'))
    await expect(args.onClick).toHaveBeenCalledOnce()
  },
}

export const PrimaryDisabled = {
  args: {
    label: 'Save',
    variant: 'primary',
    disabled: true,
    onClick: fn(),
  },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    // disabled button should not be clickable — verify the attribute is set
    await expect(canvas.getByRole('button')).toBeDisabled()
    await expect(args.onClick).not.toHaveBeenCalled()
  },
}

export const GhostDisabled = {
  args: {
    label: 'Cancel',
    variant: 'ghost',
    disabled: true,
  },
}
