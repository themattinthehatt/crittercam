import DetailPanel from './DetailPanel'

export default {
  title: 'Domain/DetailPanel',
  component: DetailPanel,
  decorators: [
    Story => (
      <div style={{ width: '300px' }}>
        <Story />
      </div>
    ),
  ],
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
}

export const WithBbox = {
  args: {
    detection: { ...BASE, bbox: { x: 0.2, y: 0.25, w: 0.35, h: 0.45 } },
  },
}

export const NoBbox = {
  args: {
    detection: { ...BASE, bbox: null },
  },
}

export const WithIndividual = {
  args: {
    detection: {
      ...BASE,
      bbox: { x: 0.2, y: 0.25, w: 0.35, h: 0.45 },
      individual_id: 3,
      nickname: 'Mittens',
    },
  },
}

export const NoTemperature = {
  args: {
    detection: { ...BASE, bbox: null, temperature_c: null },
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
  },
}
