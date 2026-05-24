import { fn, userEvent, expect, within } from 'storybook/test'
import BatchEditPanel from './BatchEditPanel'

const SPECIES_LIST = ['domestic cat', 'red fox', 'vulpes vulpes', 'white-tailed deer']
const INDIVIDUAL_LIST = [
  { id: 1, species_leaf: 'domestic cat', nickname: 'Mittens' },
  { id: 2, species_leaf: 'red fox', nickname: null },
  { id: 3, species_leaf: 'red fox', nickname: 'Bandit' },
]

export default {
  title: 'Domain/BatchEditPanel',
  component: BatchEditPanel,
  args: {
    count: 4,
    speciesList: SPECIES_LIST,
    individualList: INDIVIDUAL_LIST,
    onSave: fn(),
    onCancel: fn(),
  },
}

// default state — both dropdowns on "no change", save disabled
export const Default = {
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    await expect(canvas.getByRole('button', { name: 'save' })).toBeDisabled()
    await userEvent.click(canvas.getByRole('button', { name: 'cancel' }))
    await expect(args.onCancel).toHaveBeenCalledOnce()
  },
}

// selecting a species enables save and calls onSave with correct args
export const SpeciesSelected = {
  args: { onSave: fn() },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    const selects = canvas.getAllByRole('combobox')
    await userEvent.selectOptions(selects[0], 'red fox')
    await expect(canvas.getByRole('button', { name: 'save' })).not.toBeDisabled()
    await userEvent.click(canvas.getByRole('button', { name: 'save' }))
    await expect(args.onSave).toHaveBeenCalledWith('red fox', 'no-change')
  },
}

// selecting an individual enables save
export const IndividualSelected = {
  args: { onSave: fn() },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    const selects = canvas.getAllByRole('combobox')
    await userEvent.selectOptions(selects[1], '3')
    await expect(canvas.getByRole('button', { name: 'save' })).not.toBeDisabled()
    await userEvent.click(canvas.getByRole('button', { name: 'save' }))
    await expect(args.onSave).toHaveBeenCalledWith('', '3')
  },
}

// clearing individual (none) is a valid change
export const ClearIndividual = {
  args: { onSave: fn() },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    const selects = canvas.getAllByRole('combobox')
    await userEvent.selectOptions(selects[1], 'none')
    await userEvent.click(canvas.getByRole('button', { name: 'save' }))
    await expect(args.onSave).toHaveBeenCalledWith('', 'none')
  },
}

// both fields changed — onSave receives both values
export const BothSelected = {
  args: { onSave: fn() },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement)
    const selects = canvas.getAllByRole('combobox')
    await userEvent.selectOptions(selects[0], 'domestic cat')
    await userEvent.selectOptions(selects[1], '1')
    await userEvent.click(canvas.getByRole('button', { name: 'save' }))
    await expect(args.onSave).toHaveBeenCalledWith('domestic cat', '1')
  },
}

export const SingleSelected = {
  args: { count: 1 },
}
