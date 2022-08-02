import type { CreateFeaturesOptions, Features } from '..';


export const namespace = 'rotary_valve';

export interface OperatorLocationData {

}

export interface SegmentData {
  valve: number;
}


export function createFeatures(options: CreateFeaturesOptions): Features {
  let segmentData = options.segment.data[namespace];

  return segmentData
    ? [{
      icon: '360',
      label: `Valve ${segmentData.valve}`
    }]
    : [];
}


export default {
  createFeatures
}
