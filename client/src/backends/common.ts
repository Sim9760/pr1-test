import type { BaseBackend } from './base';
import type { Draft as AppDraft } from '../draft';
import type { Codes, ExecutorStates, Matrices, OperatorLocationData, ProtocolData, SegmentData } from '../units';


export abstract class BackendCommon implements BaseBackend {
  private _listeners: Set<() => void> = new Set();

  abstract closed: Promise<void>;
  abstract state: HostState;

  async close(): Promise<void> { }
  async sync(): Promise<void> { }
  async start(): Promise<void> { }

  onUpdate(listener: () => void, options?: { signal?: AbortSignal; }) {
    this._listeners.add(listener);

    options?.signal?.addEventListener('abort', () => {
      this._listeners.delete(listener);
    });
  }

  protected _update() {
    for (let listener of this._listeners) {
      listener();
    }
  }

  abstract command(chipId: ChipId, command: RunnerCommand): Promise<void>;
  abstract compileDraft(draftId: string, source: string): Promise<NonNullable<AppDraft['compiled']>>;
  abstract createChip(): Promise<{ chipId: ChipId; }>;
  abstract deleteChip(chipId: ChipId): Promise<void>;
  abstract createDraftSample(): Promise<string>;
  abstract pause(chipId: ChipId, options: { neutral: boolean; }): Promise<void>;
  abstract resume(chipId: ChipId): Promise<void>;
  abstract setChipMetadata(chipId: ChipId, value: Partial<Chip['metadata']>): Promise<void>;
  abstract setLocation(chipId: ChipId, location: ProtocolLocation): Promise<void>;
  abstract setMatrix(chipId: ChipId, update: Partial<Chip['matrices']>): Promise<void>;
  abstract skipSegment(chipId: ChipId, segmentIndex: number, processState?: object): Promise<void>;
  abstract startPlan(options: {
    chipId: ChipId;
    data: Codes;
    location: ProtocolLocation;
    source: string;
  }): Promise<void>;
}

export type BackendAuthAgentSpec = {
  type: 'password';
  description: string;
};


export type ChipId = string;
export type DeviceId = string;
export type DraftId = string;
export type HostId = string;

export interface Device {
  id: DeviceId;
  name: string;
}

export interface Chip {
  id: ChipId;
  master: Master | null;
  matrices: Matrices;
  metadata: {
    description: string | null;
    name: string;
  };
  name: string;
  runners: {
    control: ControlNamespace.Runner;
  };
}

export interface Draft {
  id: DraftId;
  errors: {
    message: string;
    range: [number, number];
  }[];
  protocol: Protocol | null;
  source: string;
}


export interface Master {
  entries: MasterEntry[];
  protocol: Protocol;
}

export interface MasterEntry {
  error: string | null;
  paused: boolean;
  processState: { progress: number; };
  segmentIndex: number;
  time: number;
}


export interface Protocol {
  name: string | null;
  segments: ProtocolSegment[];
  stages: ProtocolStage[];
  data: ProtocolData;
}

export interface ProtocolStage {
  name: string;
  seq: ProtocolSeq;
  steps: ProtocolStep[];
}

export interface ProtocolStep {
  name: string;
  seq: ProtocolSeq;
}

export interface ProtocolSegment {
  processNamespace: Namespace;
  data: SegmentData;
}

export type ProtocolSeq = [number, number];


export interface ProtocolLocation {
  segmentIndex: number;
  state: OperatorLocationData[keyof OperatorLocationData] | null;
}


export interface HostState {
  info: {
    id: HostId;
    name: string;
    startTime: number;

    hardware: string | null;
    software: string | null;
  };

  chips: Record<ChipId, Chip>;
  drafts: Record<DraftId, Draft>;
  devices: Record<DeviceId, Device>;

  executors: ExecutorStates;
}

export type Namespace = 'control' | 'input' | 'timer';
export type RunnerCommand = ControlNamespace.RunnerCommand;


// -- Deprecated ------------------------------------------

export namespace ControlNamespace {
  export type Signal = string;

  export interface Code {
    arguments: (number | null)[];
  }

  export interface ExecutorState {
    valves: Record<string, number>;
  }

  export interface Matrix {
    valves: {
      aliases: string[];
      hostValveIndex: number;
    }[];
  }

  export interface Runner {
    signal: Signal;
    valves: {
      error: RunnerValveError | null;
    }[];
  }

  export interface Sheet {
    diagram: string | null;

    groups: {
      name: string;
    }[];

    valves: {
      diagramRef: [number, number] | null;
      group: number;
      id: string;
      idLabel: string;
      inverse: true;
      name: string;
      repr: 'barrier' | 'flow' | 'isolate' | 'move' | 'push';
    }[];
  }

  export enum RunnerValveError {
    Unbound = 0,
    Unresponsive = 1
  }

  export interface RunnerCommand {
    control: {
      type: 'signal';
      signal: Signal;
    };
  }

  export interface ProtocolData {
    parameters: {
      defaultValveIndices: Record<ChipId, number> | null;
      display: ('delta' | 'hidden' | 'visible') | null;
      label: string;
      repr: ('flow' | 'push' | 'unpush' | 'waves') | null;
    }[];
  }

  export interface SegmentData {
    valves: number[];
  }
}


export namespace InputNamespace {
  export interface SegmentData {
    message: string;
  }
}


export namespace TimerNamespace {
  export interface SegmentData {
    duration: number;
  }
}
