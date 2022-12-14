import * as React from 'react';

import type { Host, Route } from '../application';
import { Chip, ChipId } from '../backends/common';
import { BarNav } from '../components/bar-nav';
import { ChipControl } from '../components/chip-control';
import { ChipProtocol } from '../components/chip-protocol';
import { ChipSettings } from '../components/chip-settings';
import { RotaryValveControl } from '../components/rotary-valve-control';
import { Pool } from '../util';
import * as util from '../util';


export type ViewChipMode = 'control' | 'protocol' | 'rotary-valve-control' | 'settings';

export interface ViewChipProps {
  chipId: ChipId;
  host: Host;
  mode: ViewChipMode;
  setRoute(route: Route): void;
}

export interface ViewChipState {

}

export class ViewChip extends React.Component<ViewChipProps, ViewChipState> {
  pool = new Pool();

  constructor(props: ViewChipProps) {
    super(props);

    this.state = {
      targetValveIndex: null
    };
  }

  get chip(): Chip {
    return this.props.host.state.chips[this.props.chipId];
  }

  componentDidUpdate() {
    if ((this.props.mode === 'protocol') && !this.chip.master) {
      this.props.setRoute(['chip', this.chip.id, 'settings']);
    }
  }

  shouldComponentUpdate(nextProps: ViewChipProps, nextState: ViewChipState) {
    return (nextState !== this.state)
      || (nextProps.host.state !== this.props.host.state)
      || (nextProps.chipId !== this.props.chipId)
      || (nextProps.mode !== this.props.mode);
  }

  render() {
    let component = (() => {
      switch (this.props.mode) {
        case 'control': return (
          <ChipControl
            chipId={this.props.chipId}
            host={this.props.host} />
        );
        case 'protocol': return (
          <ChipProtocol
            chipId={this.props.chipId}
            host={this.props.host} />
        );
        case 'rotary-valve-control': return (
          <RotaryValveControl
            chipId={this.props.chipId}
            host={this.props.host} />
        );
        case 'settings': return (
          <ChipSettings
            chipId={this.props.chipId}
            host={this.props.host} />
        );
      }
    })();

    return (
      <main className="blayout-container">
        <div className="blayout-header">
          <h1>{this.chip.name}</h1>
          <BarNav
            entries={[
              { id: 'protocol', label: 'Protocol', icon: 'receipt_long', disabled: !this.chip.master },
              { id: 'control', label: 'Valve control', icon: 'tune' },
              { id: 'rotary-valve-control', label: 'Rotary valve', icon: '360' },
              { id: 'settings', label: 'Settings', icon: 'settings' }
            ]}
            selectEntry={(mode) => {
              this.props.setRoute(['chip', this.props.chipId, mode]);
            }}
            selectedEntryId={this.props.mode} />
        </div>

        {component}
      </main>
    );
  }
}
