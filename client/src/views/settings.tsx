import * as React from 'react';

import { Application, Route } from '../application';
import { Icon } from '../components/icon';
import * as Form from '../components/standard-form';
import { Host } from '../host';
import { UnitInfo } from '../units';


export interface ViewSettingsProps {
  app: Application;
  host: Host;
  setRoute(route: Route): void;
}

export interface ViewSettingsState {

}

export class ViewSettings extends React.Component<ViewSettingsProps, ViewSettingsState> {
  render() {
    return (
      <main className="slayout">
        <div className="header header--1">
          <h1>Modules</h1>
        </div>

        <div className="usettings-root">
          <div className="usettings-list">
            {Object.values(this.props.host.state.info.units).map((unitInfo) => (
              <UnitInfoEntry unitInfo={unitInfo} key={unitInfo.namespace} />
            ))}
            <UnitInfoEntry unitInfo={{
              namespace: 'foo',
              metadata: {
                icon: 'biotech',
                title: 'Microscope'
              }
            }} />
            <UnitInfoEntry unitInfo={{
              namespace: 'bar',
              metadata: {
                icon: 'biotech',
                title: 'Nikon Ti2 Eclipse Elements macro runner'
              }
            }} />
            <UnitInfoEntry unitInfo={{
              namespace: 'terminal',
              metadata: {
                icon: 'terminal',
                title: 'Terminal sessions'
              }
            }} />
          </div>
          <div className="usettings-panel upanel-root">
            <div className="upanel-header">
              <h2 className="upanel-title">Voice reports</h2>
              {/* <div className="upanel-actions">
                <button type="button" className="upanel-action">Disable</button>
              </div> */}
              <label className="upanel-checkbox">
                <input type="checkbox" />
                <div>Enabled</div>
              </label>
            </div>

            <div className="upanel-info">
              <p className="upanel-description">Voice reports powered by the built-in macOS voice synthesis command `say`.</p>
              <dl className="upanel-data">
                <dt>Namespace</dt>
                <dd><code>say</code></dd>
                <dt>License</dt>
                <dd>MIT license</dd>
                <dt>Version</dt>
                <dd>0.1.0</dd>
                <dt>Source module</dt>
                <dd><code>pr1_builtin</code></dd>
              </dl>
            </div>

            <div className="upanel-settings">
              <h3>Settings</h3>

              {/* <div className="upanel-status">This module's settings can only be edited in the setup configuration file.</div> */}

              <Form.Form>
                <Form.TextField label="Voice report interval" placeholder="e.g. 12 sec" />
                <Form.Actions>
                  <Form.Action label="Reset" />
                  <Form.Action type="submit" label="Apply" />
                </Form.Actions>
              </Form.Form>
            </div>
          </div>
        </div>
      </main>
    );
  }
}


function UnitInfoEntry({ unitInfo }: { unitInfo: UnitInfo; }) {
  return (
    <button type="button" className="usettings-entry" key={unitInfo.namespace} style={{ '--angle': `${hash(unitInfo.metadata.title) * 360}deg` }}>
      <div className="usettings-icon">
        <Icon name={unitInfo.metadata.icon ?? 'mic'} />
        {/* <svg xmlns="http://www.w3.org/2000/svg" viewBox="15 19.334 160 45.331"><g fill="#fff"><path d="M175 33.117v3.142c0 1.346-.645 2.211-2.124 3.287-1.481 1.077-4.948 1.896-7.192 1.896h-8.887c-2.288 0-4.779-.402-6.552-.773-1.772-.37-3.534-1.638-3.95-2.054-.415-.414-1.097-1.704-1.097-2.401v-6.799c0-1.212.67-2.603 2.331-3.546a14.238 14.238 0 0 1 4.544-1.649c1.38-.256 2.637-.351 3.299-.351h10.657c1.057 0 4.443.386 6.127 1.295S175 27.497 175 28.855v4.262zm-4.816 2.895v-6.868c0-.627-.875-1.278-1.75-1.582-.875-.303-2.502-.444-3.647-.444h-9.515c-1.101 0-3.187.476-3.961.792-.772.314-1.312 1.055-1.312 1.828v6.318c0 .706 1.369 1.47 2.222 1.682.852.213 2.086.369 3.424.369h9.826c.967 0 2.244-.234 3.299-.682 1.054-.45 1.414-.977 1.414-1.413zM154.952 49.366h19.606v15.299h-19.606zM130.537 49.366h19.607v15.299h-19.607zM141.882 25.543c0 1.04-.543 1.575-1.603 1.575h-3.574c-.854 0-1.331.044-2.046.225-.716.182-2.202.896-2.202 1.693v11.008c0 .779-.559 1.396-2.523 1.396-1.963 0-2.352-.796-2.352-1.06V28.938c0-1.058.842-2.547 1.871-3.175 1.029-.629 2.49-1.137 3.259-1.316.771-.184 3.097-.581 4.328-.581h3.294c.652.001 1.548.635 1.548 1.677zM106.732 49.366h19.608v15.299h-19.608zM88.756 20.634c0-1.299 1.137-1.299 1.634-1.299h21.815c1.964 0 4.748.193 7.018.898 2.271.706 3.547 1.983 3.758 2.46.209.477.361 1.622.361 3.298 0 1.678-.172 2.67-.324 3.166-.151.497-.705 1.469-1.83 2.212-1.125.743-2.213 1.145-3.377 1.431-1.162.286-4.099.687-5.738.687h-18.31v6.617c0 .438-.189 1.335-2.513 1.335-2.328 0-2.492-.936-2.492-1.165-.002-.494-.002-18.34-.002-19.64zm29.474 7.094v-3.527c0-.533-1.221-1.145-1.963-1.354-.744-.21-2.119-.347-3.566-.347h-18.94v7.611h19.321c.953 0 2.613-.284 3.566-.705.954-.42 1.582-1.277 1.582-1.678zM82.7 49.366h19.608v15.299H82.7zM60.165 27.938c-.516.229-1.296.858-1.296 1.583v6.466c0 .628 1.01 1.276 1.659 1.524s2.135.596 3.546.596h10.527c1.011 0 2.744-.634 3.26-.825.515-.192 1.105-.591 1.105-1.296v-7.133c0-.44-1.009-1.068-1.849-1.355-.838-.286-2.097-.38-3.339-.38H63.692c-1.184 0-3.013.59-3.527.82zm19.316 12.624c-1.373.477-4.349.879-5.11.879h-10.05c-1.641 0-3.473-.365-5.035-.747-1.562-.38-2.937-1.011-3.758-1.734-.819-.725-1.489-1.602-1.489-2.364v-7.418c0-1.257 1.356-2.975 2.483-3.472 1.125-.495 2.23-1.028 3.395-1.296 1.163-.267 3.032-.543 3.946-.543h10.928c1.716 0 3.395.314 4.861.811 1.47.495 2.615 1.105 3.146 1.772.535.667 1.044 1.563 1.044 2.327v7.818c0 1.067-.699 1.888-1.29 2.383-.593.498-1.698 1.106-3.071 1.584zM47.426 39.207c-1.145.916-3.013 1.508-3.911 1.736-.898.23-2.594.498-3.737.498H25.667c-1.813 0-3.529-.231-5.054-.574-1.528-.344-3.071-1.087-3.817-1.641-.74-.553-1.796-1.714-1.796-2.617V24.403c0-1.186 1.015-2.244 1.994-2.888 1.001-.657 1.748-1.008 2.948-1.31a49.38 49.38 0 0 1 2.064-.459c1.097-.219 2.253-.412 2.883-.412h6.49c.918 0 1.962.393 1.962 1.608 0 1.217-.614 1.556-1.486 1.556h-4.75c-.917 0-2.407.109-3.593.328-1.149.211-1.78.314-2.28.587-.501.272-1.187.75-1.187 1.485v11.087c0 1.398 3.063 2.121 4.36 2.121h14.038c1.773 0 2.764-.292 3.7-.558.934-.267 2.017-.924 2.017-1.374v-2.688h-7.472c-1.048 0-1.316-.765-1.316-1.471 0-.705.05-1.907 1.68-1.907h10.945c1.167 0 1.167.66 1.167 1.05v5.168c0 .847-.595 1.967-1.738 2.881z"/></g></svg> */}
      </div>
      <div className="usettings-title">{unitInfo.metadata.title}</div>
      <div className="usettings-subtitle">0.1.0</div>
      {/* <div className="usettings-description">{unitInfo.metadata.description}</div> */}
    </button>
  );
}


function hash(input: string): number {
  let output = 0;

  for (let i = 0; i < input.length; i += 1) {
    output ^= input.charCodeAt(i);
  }

  return output / 0xff;
}
