import type { AnyDurationTerm, Experiment, ExperimentId, MasterBlockLocation, OrdinaryId, PluginName, ProtocolBlock, ProtocolBlockName } from 'pr1-shared';
import type { ComponentType, ReactNode } from 'react';

import type { Application } from '../application';
import type { Host } from '../host';
import type { ProtocolBlockGraphPair, ProtocolBlockGraphRenderer } from './graph';
import type { FeatureDef } from '../libraries/features';
import type { Pool } from '../util';
import type { StoreConsumer, StoreEntries } from '../store/types';
import type { ShortcutCode } from '../shortcuts';


export interface PluginSettingsComponentProps<Context extends AnyPluginContext> {
  app: Application;
  context: Context;
}

export interface PluginViewEntry<Context extends AnyPluginContext> {
  id: OrdinaryId;
  icon: string;
  label: string;

  Component: ComponentType<PluginViewComponentProps<Context>>;
}

export interface PluginExecutionPanel<Context extends AnyPluginContext> {
  id: OrdinaryId;
  label: string;
  shortcut?: ShortcutCode;
  Component: ComponentType<PluginExecutionPanelComponentProps<Context>>;
}

export interface PluginExecutionPanelComponentProps<Context extends AnyPluginContext> {
  context: Context;
  experiment: Experiment;
}

export interface PluginViewComponentProps<Context extends AnyPluginContext> {
  context: Context;
}

export interface Plugin<PersistentStoreEntries extends StoreEntries = [], SessionStoreEntries extends StoreEntries = []> {
  namespace: PluginName;
  styleSheets?: CSSStyleSheet[];

  blocks: Record<ProtocolBlockName, UnknownPluginBlockImpl>;
  persistentStoreDefaults?: PersistentStoreEntries;
  sessionStoreDefaults?: SessionStoreEntries;

  SettingsComponent?: ComponentType<PluginSettingsComponentProps<PluginContext<PersistentStoreEntries, SessionStoreEntries>>>;

  executionPanels?: PluginExecutionPanel<PluginContext<PersistentStoreEntries, SessionStoreEntries>>[];
  views?: PluginViewEntry<PluginContext<PersistentStoreEntries, SessionStoreEntries>>[];
}

export type UnknownPlugin = Plugin<StoreEntries, StoreEntries>;
export type Plugins = Record<PluginName, UnknownPlugin>;


export interface GlobalContext {
  app: Application;
  host: Host;
  pool: Pool;
}

export interface PluginContext<PersistentStoreEntries extends StoreEntries = [], SessionStoreEntries extends StoreEntries = []> extends GlobalContext {
  requestToExecutor(request: unknown): Promise<unknown>;
  requestToRunner(request: unknown, experimentId: ExperimentId): Promise<unknown>;
  store: StoreConsumer<PersistentStoreEntries, SessionStoreEntries>;
}

export type AnyPluginContext = PluginContext<any, any>;

export interface BlockContext extends GlobalContext {
  experiment: Experiment;
  sendMessage(message: unknown): Promise<void>;
}


export interface PluginBlockImplComponentProps<Block extends ProtocolBlock, Location> {
  block: Block;
  context: BlockContext;
  location: Location;
}

export interface PluginBlockImplReportComponentProps<Block extends ProtocolBlock, Location> {
  block: Block;
  context: GlobalContext;
  eventDate: number;
  location: Location;
}

export interface PluginBlockImplAction {
  id: OrdinaryId;
  icon: string;
  label?: string;
  onTrigger(): void;
}

export interface PluginBlockImplCommand {
  id: OrdinaryId;
  disabled?: unknown;
  label: string;
  onTrigger(): void;
  shortcut?: string;
}


export interface PluginBlockImpl<Block extends ProtocolBlock, Location extends MasterBlockLocation> {
  Component?: ComponentType<PluginBlockImplComponentProps<Block, Location>>;
  ReportComponent?: ComponentType<PluginBlockImplReportComponentProps<Block, Location>>;

  computeGraph?: ProtocolBlockGraphRenderer<Block, Location>;
  createActions?(block: Block, location: Location, context: BlockContext): PluginBlockImplAction[];
  createCommands?(block: Block, location: Location, context: BlockContext): PluginBlockImplCommand[];
  createFeatures?(block: Block, location: Location | null, descendantPairs: ProtocolBlockGraphPair[], context: GlobalContext): FeatureDef[];

  // Missing -> inherits child's point
  // Returns null -> point is null
  createPoint?(block: Block, location: Location | null, child: { key: number; point: unknown; } | null, context: GlobalContext): unknown | null;

  getChildren?(block: Block, context: GlobalContext): {
    block: ProtocolBlock;
    delay: AnyDurationTerm;
  }[];
  getChildrenExecution?(block: Block, location: Location, context: GlobalContext): (PluginBlockExecutionRef | null)[] | null;
  getLabel?(block: Block): ReactNode | null;
}

export interface PluginBlockExecutionRef {
  location: MasterBlockLocation;
}

export type UnknownPluginBlockImpl = PluginBlockImpl<any, any>;
