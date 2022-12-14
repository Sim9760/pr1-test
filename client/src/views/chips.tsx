import * as React from 'react';

import type { Host, Route } from '../application';
import { ChipId } from '../backends/common';
import { Icon } from '../components/icon';
import { Units } from '../units';
import { Pool } from '../util';


export interface ViewChipsProps {
  host: Host;
  setRoute(route: Route): void;
}

export class ViewChips extends React.Component<ViewChipsProps> {
  pool = new Pool();
  chipIdAwaitingRedirect: ChipId | null = null;

  componentDidUpdate() {
    if (this.chipIdAwaitingRedirect && (this.chipIdAwaitingRedirect in this.props.host.state.chips)) {
      this.props.setRoute(['chip', this.chipIdAwaitingRedirect, 'settings']);
    }
  }

  render() {
    let chips = Object.values(this.props.host.state.chips);

    return (
      <main>
        <div className="header header--1">
          <h1>Chips</h1>
        </div>

        <div className="header header--2">
          <h2>Current chips</h2>
          <button type="button" className="btn" onClick={() => {
            this.pool.add(async () => {
              let result = await this.props.host.backend.createChip();
              this.chipIdAwaitingRedirect = result.chipId;
            });
          }}>
            <div>New chip</div>
          </button>
        </div>

        {(chips.length > 0)
          ? (
            <div className="card-list">
              {chips.map((chip) => {
                let previewUrl = null;

                for (let [_namespace, unit] of Units) {
                  previewUrl ??= unit.providePreview?.({ chip, host: this.props.host }) ?? null;

                  if (previewUrl) {
                    break;
                  }
                }

                return (
                  <Card
                    previewUrl={previewUrl}
                    title={chip.name}
                    status={chip.master
                      ? { icon: 'receipt_long', label: (chip.master.protocol.name ?? 'Running') }
                      : { icon: 'dark_mode', label: 'Idle' }}
                    key={chip.id}
                    onClick={() => {
                      this.props.setRoute(['chip', chip.id, 'settings']);
                    }} />
                );
              })}
            </div>
          )
          : (
            <div className="card-blank">
              <p>No chip running</p>
            </div>
          )}

        {/* + Completed chips */}
      </main>
    );
  }
}


function Card(props: {
  onClick(event: React.SyntheticEvent<HTMLButtonElement, MouseEvent>): void;
  previewUrl: string | null;
  title: string;
  subtitle?: string;
  status?: {
    icon: string;
    label: string;
  };
}) {
  return (
    <button type="button" className="card-item" onClick={props.onClick}>
      <div className="card-image">
        {props.previewUrl
          ? <img src={props.previewUrl} />
          : (
            <div className="card-image-placeholder">
              <Icon name="image_not_supported" />
              <div>No preview</div>
            </div>
          )}
      </div>
      <div className="card-body">
        <div className="card-title">{props.title}</div>
        {props.subtitle && <div className="card-subtitle">{props.subtitle}</div>}
        {props.status && (
          <div className="card-status">
            <Icon name={props.status.icon} />
            <div>{props.status.label}</div>
          </div>
        )}
      </div>
    </button>
  );
}
