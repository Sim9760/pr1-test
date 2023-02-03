import { ProtocolBlock, ProtocolState, BlockUnit, React, UnitNamespace, HeadUnit } from 'pr1';


export interface Block extends ProtocolBlock {
  child: ProtocolBlock;
  state: ProtocolState;
}

export interface BlockMetrics {

}

export interface Location {
  children: { 0?: unknown; };
  mode: LocationMode;
  state: Record<UnitNamespace, unknown>;
}

export enum LocationMode {
  Halted = 6,
  Halting = 0,
  Normal = 1,
  PausingChild = 2,
  PausingState = 3,
  Paused = 4
}

export type Key = null;


export default {
  namespace: 'state',

  graphRenderer: {
    computeMetrics(block, ancestors, location, options, context) {
      return options.computeMetrics(block.child, [...ancestors, block], location?.children[0] ?? null);
    },

    render(block, path, metrics, position, location, options, context) {
      return options.render(block.child, [...path, null], metrics, position, location?.children[0] ?? null, options);
    }
  },

  HeadComponent(props) {
    if (!props.location) {
      return null;
    }

    return (
      <div>{LocationMode[props.location.mode]}</div>
    );
  },

  createActiveBlockMenu(block, location, options) {
    let busy = false;

    return location.mode === LocationMode.Normal
      ? [{ id: 'pause', name: 'Pause', icon: 'pause_circle', disabled: (location.mode !== LocationMode.Normal) || busy }]
      : [{ id: 'resume', name: 'Resume', icon: 'play_circle', disabled: busy }];
  },
  getBlockClassLabel(block) {
    return 'State';
  },
  getActiveChildLocation(location, key) {
    return location.children[0];
  },
  getChildrenExecutionKeys(block, location) {
    return location.children[0]
      ? [0]
      : null;
  },
  getChildBlock(block, key) {
    return block.child;
  },
  isBlockPaused(block, location, options) {
    return location.mode == LocationMode.Paused;
  },
  onSelectBlockMenu(block, location, path) {
    switch (path.first()) {
      case 'pause': return { type: 'pause' };
      case 'resume': return { type: 'resume' };
    }
  },
} satisfies BlockUnit<Block, BlockMetrics, Location, Key> & HeadUnit<Block, Location>
