import type { HostBackendOptions, HostSettings, HostSettingsData, HostSettingsRecord } from '../host';
import type { DraftId, DraftPrimitive } from '../draft';
import { BaseBackend } from '../backends/base';


export interface DraftItem {
  id: DraftId;
  name: string | null;
  kind: 'own' | 'ref';
  lastModified: number | null;
  locationInfo: {
    type: 'directory' | 'file';
    name: string;
  } | null;
  mainFilePath: string;
  readable: boolean;
  readonly: boolean;
  revision: number;
  source: string | null;
  volumeInfo: {
    type: 'disk' | 'network';
    name: string;
  } | null;
  writable: boolean;

  openFile?(filePath?: string): Promise<void>;
  request?(): Promise<void>;
  revealFile?(filePath?: string): Promise<void>;
  watch(handler: () => void, options: { signal: AbortSignal; }): Promise<void>;
  write(primitive: DraftPrimitive): Promise<void>;
}

export interface AppBackend {
  initialize(): Promise<void>;

  deleteHostSettings(settingsId: string): Promise<void>;
  getHostSettingsData(): Promise<HostSettingsData>;
  setDefaultHostSettings(settingsId: string | null): Promise<void>;
  setHostSettings(settings: HostSettings): Promise<void>;

  createDraft(options: { directory: boolean; source: string; }): Promise<DraftItem | null>;
  deleteDraft(draftId: DraftId): Promise<void>;
  listDrafts(): Promise<DraftItem[]>;
  loadDraft(options: { directory: boolean; }): Promise<DraftItem | null>;
  requestDraft?(draftId: DraftId): Promise<void>;

  notify(message: string): Promise<void>;

  createBackend?(options: HostBackendOptions): Promise<BaseBackend | null>;
}

export interface AppBackendClass {
  new(): AppBackend;
}
