import * as React from 'react';

import type { DraftEntry as DraftDatabaseEntry } from '../app-backend';
import type { Host, Route } from '../application';
import type { Draft, DraftId, DraftPrimitive } from '../draft';
import { ContextMenuArea, ContextMenuAreaProps } from '../components/context-menu-area';
import { Icon } from '../components/icon';
import * as util from '../util';
import { Pool } from '../util';
import { analyzeProtocol } from '../analysis';
import { formatDuration } from '../format';


const rtf = new Intl.RelativeTimeFormat('en', {
  localeMatcher: 'best fit',
  numeric: 'auto',
  style: 'long'
});


export interface ViewProtocolsProps {
  drafts: Record<DraftId, Draft>;
  host: Host;

  createDraft(location: DraftDatabaseEntry['location']): Promise<DraftId>;
  deleteDraft(draftId: DraftId): Promise<void>;
  setDraft(draft: DraftPrimitive): Promise<void>;
  setRoute(route: Route): void;
}

export class ViewProtocols extends React.Component<ViewProtocolsProps> {
  pool = new Pool();

  render() {
    let drafts = Object.values(this.props.drafts);

    return (
      <main>
        <header className="header header--1">
          <h1>Protocols</h1>
        </header>

        <div className="lproto-container">
          <header className="header header--2">
            <h2>All protocols</h2>
            <div>
              <button type="button" className="btn" onClick={() => {
                this.pool.add(async () => {
                  let draftId = await this.props.createDraft({
                    type: 'app',
                    source: `name: Untitled protocol\n\nstages:\n  - name: First stage\n    steps:\n      - duration: 20 min`,
                  });

                  this.props.setRoute(['protocol', draftId]);
                });
              }}>
                New protocol
              </button>
              <button type="button" className="btn" onClick={() => {
                this.pool.add(async () => {
                  let handles = await util.wrapAbortable(window.showOpenFilePicker({
                    types: [
                      { accept: { 'text/yml': ['.yml', '.yaml'] } }
                    ]
                  }));

                  if (handles && (handles.length > 0)) {
                    await this.props.createDraft({
                      type: 'filesystem',
                      handle: handles[0]
                    });
                  }
                });
              }}>Use file</button>
            </div>
          </header>

          <div className="lproto-list">
            {drafts.map((draft) => {
              let analysis = draft.compiled?.protocol && analyzeProtocol(draft.compiled.protocol);

              return (
                <DraftEntry
                  name={draft.entry.name ?? '[Untitled]'}
                  properties={[
                    { id: 'lastModified', label: 'Last modified ' + rtf.format(Math.round((draft.entry.lastModified - Date.now()) / 3600e3 / 24), 'day'), icon: 'calendar_today' },
                    ...(draft.compiled
                      ? [analysis
                        ? { id: 'display', label: formatDuration(analysis.done.time), icon: 'schedule' }
                        : { id: 'status', label: 'Error', icon: 'error' }]
                      : []),
                    ...((draft.entry.location.type === 'filesystem')
                      ? [{ id: 'file', label: draft.entry.location.handle.name, icon: 'description' }]
                      : [])
                  ]}
                  createMenu={() => [
                    // { id: 'chip', name: 'Open chip', icon: 'memory' },
                    { id: 'duplicate', name: 'Duplicate', icon: 'file_copy' },
                    { id: '_divider', type: 'divider' },
                    { id: 'archive', name: 'Archive', icon: 'archive' },
                    { id: 'delete', name: 'Delete', icon: 'delete' }
                  ]}
                  onClick={() => {
                    this.props.setRoute(['protocol', draft.id]);
                  }}
                  onSelect={(path) => {
                    switch (path.first()) {
                      case 'delete': {
                        this.props.setRoute(['protocol']);

                        this.pool.add(async () => {
                          await this.props.deleteDraft(draft.id);
                        });
                      }
                    }
                  }}
                  key={draft.id} />
              );
            })}
          </div>
        </div>
      </main>
    );
  }
}


export function DraftEntry(props: ContextMenuAreaProps & {
  name: string;
  properties: {
    id: string;
    label: string;
    icon: string;
  }[];
  onClick?(event: React.SyntheticEvent): void;
}) {
  return (
    <ContextMenuArea
      createMenu={props.createMenu}
      onSelect={props.onSelect}>
      <button type="button" className="lproto-entry" onClick={props.onClick}>
        <div className="lproto-label">{props.name}</div>
        <div className="lproto-property-list">
          {props.properties.map((property) => (
            <div className="lproto-property-item" key={property.id}>
              <Icon name={property.icon} />
              <div className="lproto-property-label">{property.label}</div>
            </div>
          ))}
        </div>
        <div className="lproto-action-item">
          {/* <div className="proto-action-label">Edit</div> */}
          <Icon name="arrow_forward" />
        </div>
      </button>
    </ContextMenuArea>
  );
}
