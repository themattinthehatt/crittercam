import DetectionCard from './DetectionCard'

export default {
  title: 'Domain/DetectionCard',
  component: DetectionCard,
  // Decorators wrap every story in this file with extra markup.
  // This one constrains the card to a realistic grid-cell width so the
  // story reflects how the component actually appears in the app.
  decorators: [
    Story => (
      <div style={{ width: '160px' }}>
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
