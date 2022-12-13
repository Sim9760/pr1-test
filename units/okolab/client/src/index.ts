export const namespace = 'okolab';


export function createFeatures(options: any) {
  let segmentData = options.segment.data[namespace];

  return segmentData
    ? [{
      icon: 'thermostat',
      label: segmentData.value !== null ? `${segmentData.value}°C` : 'N/A'
    }]
    : [];
}


export default {
  createFeatures
}
