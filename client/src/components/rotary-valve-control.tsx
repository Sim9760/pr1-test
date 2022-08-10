import * as React from 'react';

import * as Form from './standard-form';
import type { Host } from '../host';
import { Chip, ChipId, ControlNamespace } from '../backends/common';
import { namespace } from '../units/rotary-valve';
import { Pool } from '../util';
import * as util from '../util';


export interface RotaryValveControlProps {
  chipId: ChipId;
  host: Host;
}

export interface RotaryValveControlState {

}

export class RotaryValveControl extends React.Component<RotaryValveControlProps, RotaryValveControlState> {
  pool = new Pool();

  constructor(props: RotaryValveControlProps) {
    super(props);
    this.state = {};
  }

  get chip(): Chip {
    return this.props.host.state.chips[this.props.chipId];
  }

  render() {
    let executor = this.props.host.state.executors[namespace];

    return (
      <div className="blayout-contents">
        <div className="header header--2">
          <h2>Manual control</h2>
        </div>

        <Form.Form>
          <Form.Select
            label="Position"
            onInput={(value) => {
              this.pool.add(async () => {
                this.props.host.backend.command(this.chip.id, {
                  [namespace]: {
                    "valve": value
                  }
                })
              });
            }}
            options={new Array(executor.valveCount).fill(0).map((_, index) => ({
              id: index + 1,
              label: `${index + 1}`
            }))}
            value={executor.valve} />
        </Form.Form>
      </div>
    );
  }
}
