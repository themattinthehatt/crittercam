import DetectionModal from './DetectionModal'

export default {
  title: 'Domain/DetectionModal',
  component: DetectionModal,
  // modal uses fixed positioning so no width constraint is needed
  args: {
    onClose: () => {},
    onPrev: () => {},
    onNext: () => {},
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

// middle of a list — both arrows visible
export const Middle = {
  args: {
    detection: BASE,
    hasPrev: true,
    hasNext: true,
  },
}

// first item in a list — only next arrow
export const First = {
  args: {
    detection: BASE,
    hasPrev: false,
    hasNext: true,
  },
}

// last item in a list — only prev arrow
export const Last = {
  args: {
    detection: BASE,
    hasPrev: true,
    hasNext: false,
  },
}

export const NoBbox = {
  args: {
    detection: { ...BASE, bbox: null },
    hasPrev: true,
    hasNext: true,
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
  },
}

export const NoTemperature = {
  args: {
    detection: { ...BASE, bbox: null, temperature_c: null },
    hasPrev: true,
    hasNext: true,
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
  },
}
