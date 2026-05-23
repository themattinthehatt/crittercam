import Badge from './Badge'

export default {
  title: 'Primitives/Badge',
  component: Badge,
}

export const HighConfidence = {
  args: {
    label: '91%',
    variant: 'confidence',
    confidence: 0.91,
  },
}

export const MediumConfidence = {
  args: {
    label: '55%',
    variant: 'confidence',
    confidence: 0.55,
  },
}

export const LowConfidence = {
  args: {
    label: '28%',
    variant: 'confidence',
    confidence: 0.28,
  },
}

export const Species = {
  args: {
    label: 'white-tailed deer',
    variant: 'species',
  },
}

export const Blank = {
  args: {
    label: 'blank',
    variant: 'blank',
  },
}
