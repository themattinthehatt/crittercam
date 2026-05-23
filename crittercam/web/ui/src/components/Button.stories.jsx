import Button from './Button'

export default {
  title: 'Primitives/Button',
  component: Button,
}

export const Primary = {
  args: {
    label: 'Save',
    variant: 'primary',
  },
}

export const Ghost = {
  args: {
    label: 'Cancel',
    variant: 'ghost',
  },
}

export const PrimaryDisabled = {
  args: {
    label: 'Save',
    variant: 'primary',
    disabled: true,
  },
}

export const GhostDisabled = {
  args: {
    label: 'Cancel',
    variant: 'ghost',
    disabled: true,
  },
}
