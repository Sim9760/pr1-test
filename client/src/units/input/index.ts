import type { CreateFeaturesOptions, Features } from '..';


export const namespace = 'input';

export interface OperatorLocationData {

}

export interface Code {
  arguments: (number | null)[];
}

export interface SegmentData {
  message: string;
}


export function createFeatures(options: CreateFeaturesOptions): Features {
  let segmentData = options.segment.data[namespace];

  return segmentData
    ? [{
      icon: 'keyboard_command_key',
      label: segmentData.message
    }]
    : [];
}


export default {
  createFeatures
}
