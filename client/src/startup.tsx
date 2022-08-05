import '@fontsource/space-mono';
import * as React from 'react';

import { HostCreator } from './startup/host-creator';
import type { HostId } from './backends/common';
import * as util from './util';
import { type HostSettings, type HostSettingsRecord, formatHostSettings } from './host';
import { ContextMenuArea } from './components/context-menu-area';


interface StartupProps {
  createHostSettings(options: { settings: HostSettings; }): void;
  deleteHostSettings(settingsId: string): void;
  launchHost(settingsId: string): void;
  hostSettings: HostSettingsRecord;
}

interface StartupState {
  fullDisplay: boolean;
  hostCreatorIndex: number;
  hostCreatorOpen: boolean;
  hostCreatorVisible: boolean;
}

export class Startup extends React.Component<StartupProps, StartupState> {
  controller = new AbortController();

  constructor(props: StartupProps) {
    super(props);

    this.state = {
      fullDisplay: false,
      hostCreatorIndex: 0,
      hostCreatorOpen: false,
      hostCreatorVisible: false
    };
  }

  componentDidMount() {
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Alt') {
        this.setState({ fullDisplay: true });
      }
    }, { signal: this.controller.signal });

    document.addEventListener('keyup', (event) => {
      if ((event.key === 'Alt') && this.state.fullDisplay) {
        this.setState({ fullDisplay: false });
      }
    }, { signal: this.controller.signal });

    window.addEventListener('blur', () => {
      if (this.state.fullDisplay) {
        this.setState({ fullDisplay: false });
      }
    }, { signal: this.controller.signal });
  }

  componentWillUnmount() {
    this.controller.abort();
  }

  resetHostCreator() {
    this.setState((state) => ({
      hostCreatorIndex: (state.hostCreatorIndex + 1),
      hostCreatorOpen: false,
      hostCreatorVisible: false
    }));
  }

  render() {
    return (
      <div className="startup-container">
        <div className={util.formatClass('startup-root', { '_transitioning': this.state.hostCreatorOpen })}>
          <div className="startup-editor-root">
            <div className="startup-editor-indicator" onTransitionEnd={(event) => {
              if ((event.currentTarget === event.target) && this.state.hostCreatorOpen) {
                this.setState({ hostCreatorVisible: true });
              }
            }} />
            <div className="startup-editor-holder">
              {this.state.hostCreatorVisible && (
                <HostCreator
                  onCancel={() => {
                    this.resetHostCreator();
                  }}
                  onDone={({ settings }) => {
                    this.resetHostCreator();
                    this.props.createHostSettings({ settings });
                  }}
                  key={this.state.hostCreatorIndex} />
              )}
            </div>
          </div>

          <div className="startup-home">
            <div className="startup-left-root">
              <div className="startup-left-header">
                <img src="static/logo.jpeg" width="330" height="300" className="startup-left-logo" />
                <div className="startup-left-title">Universal Lab Experience</div>
              </div>
              <div className="startup-left-bar">
                <div>Version 1.0</div>
                {this.state.fullDisplay && (
                  <div>License no. <code>CF 59 AF 6E</code></div>
                )}
              </div>
            </div>
            <div className="startup-right-root">
              <div className="startup-right-entry-list">
                {Object.values(this.props.hostSettings).map((hostSettings) => (
                  <ContextMenuArea
                    createMenu={(_event) => [
                      { id: 'delete', name: 'Delete', icon: 'delete', disabled: hostSettings.builtin }
                    ]}
                    onSelect={(path) => {
                      if (path.first()! === 'delete') {
                        this.props.deleteHostSettings(hostSettings.id);
                      }
                    }}
                    key={hostSettings.id}>
                    <button type="button" className="startup-right-entry-item" onClick={() => {
                      this.props.launchHost(hostSettings.id);
                    }}>
                      <div className="startup-right-entry-title">{hostSettings.label ?? 'Untitled host'}</div>
                      <div className="startup-right-entry-path">{formatHostSettings(hostSettings)}</div>
                      <svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 0 24 24" width="24px" fill="currentColor"><path d="M0 0h24v24H0V0z" fill="none" /><path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6-6-6z" /></svg>
                    </button>
                  </ContextMenuArea>
                ))}
              </div>
              <div className="startup-right-entry-list">
                <button type="button" className="startup-right-entry-item" onClick={() => {
                  this.setState({ hostCreatorOpen: true });
                }}>
                  <div className="startup-right-entry-title">New setup</div>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }
}
