import { fn, userEvent, expect, within } from 'storybook/test'
import DetectionCard from './DetectionCard'

export default {
  title: 'Domain/DetectionCard',
  component: DetectionCard,
  // Decorators wrap every story in this file with extra markup.
  // This one constrains the card to a realistic grid-cell width so the
  // story reflects how the component actually appears in the app.
  decorators: [
    Story => (
      <div style={{ width: '240px' }}>
        <Story />
      </div>
    ),
  ],
}

export const Default = {
  args: {
    cropUrl: 'https://placehold.co/300x200',
    label: 'white-tailed deer',
    confidence: 0.91,
    capturedAt: '2026-03-14T02:17:00',
    onClick: fn(),
  },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    // clicking the card fires onClick
    await userEvent.click(canvas.getByRole('img'))
    await expect(args.onClick).toHaveBeenCalledOnce()
  },
}

export const LowConfidence = {
  args: {
    cropUrl: 'https://placehold.co/300x200',
    label: 'anatidae (family)',
    confidence: 0.34,
    capturedAt: '2026-03-14T02:17:00',
  },
}

export const Blank = {
  args: {
    cropUrl: null,
    label: 'blank',
    confidence: 0.98,
    capturedAt: '2026-03-14T02:17:00',
  },
}

export const Selected = {
  args: {
    cropUrl: 'https://placehold.co/300x200',
    label: 'white-tailed deer',
    confidence: 0.91,
    capturedAt: '2026-03-14T02:17:00',
    selected: true,
  },
}

export const LongLabel = {
  args: {
    cropUrl: 'https://placehold.co/300x200',
    label: 'procyon lotor (northern raccoon)',
    confidence: 0.76,
    capturedAt: '2026-03-14T02:17:00',
  },
}

// batch-selectable card — checkbox visible, not yet checked
export const BatchSelectable = {
  args: {
    cropUrl: 'https://placehold.co/300x200',
    label: 'white-tailed deer',
    confidence: 0.91,
    capturedAt: '2026-03-14T02:17:00',
    batchSelected: false,
    onClick: fn(),
    onBatchSelect: fn(),
  },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    const checkbox = canvas.getByRole('checkbox')
    // clicking checkbox fires onBatchSelect, not onClick
    await userEvent.click(checkbox)
    await expect(args.onBatchSelect).toHaveBeenCalledOnce()
    await expect(args.onClick).not.toHaveBeenCalled()
    // clicking the image fires onClick
    await userEvent.click(canvas.getByRole('img'))
    await expect(args.onClick).toHaveBeenCalledOnce()
  },
}

// card with batch selection active — primary ring + checked checkbox
export const BatchSelected = {
  args: {
    cropUrl: 'https://placehold.co/300x200',
    label: 'white-tailed deer',
    confidence: 0.91,
    capturedAt: '2026-03-14T02:17:00',
    batchSelected: true,
    onBatchSelect: fn(),
  },
}

export const Favorited = {
  args: {
    cropUrl: 'https://placehold.co/300x200',
    label: 'white-tailed deer',
    confidence: 0.91,
    capturedAt: '2026-03-14T02:17:00',
    isFavorite: true,
    onClick: fn(),
    onFavorite: fn(),
  },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    // clicking the star fires onFavorite but NOT onClick (stopPropagation)
    const star = canvas.getByRole('button')
    await userEvent.click(star)
    await expect(args.onFavorite).toHaveBeenCalledOnce()
    await expect(args.onClick).not.toHaveBeenCalled()
  },
}
