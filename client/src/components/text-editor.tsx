import * as monaco from 'monaco-editor';
import * as React from 'react';
import * as ReactDOM from 'react-dom';

import { Icon } from './icon';
import { Draft } from '../draft';
import * as util from '../util';


window.MonacoEnvironment = {
	getWorkerUrl: function (_moduleId, label) {
		if (label === 'json') {
			return './dist/vs/language/json/json.worker.js';
		}
		if (label === 'css' || label === 'scss' || label === 'less') {
			return './dist/vs/language/css/css.worker.js';
		}
		if (label === 'html' || label === 'handlebars' || label === 'razor') {
			return './dist/vs/language/html/html.worker.js';
		}
		if (label === 'typescript' || label === 'javascript') {
			return './dist/vs/language/typescript/ts.worker.js';
		}
		return './dist/vs/editor/editor.worker.js';
	}
};


export interface TextEditorProps {
  draft: Draft;
  onSave(source: string): void;
}

export class TextEditor extends React.Component<TextEditorProps> {
  controller = new AbortController();
  editor!: monaco.editor.IStandaloneCodeEditor;
  model!: monaco.editor.IModel;
  pool = new util.Pool();
  ref = React.createRef<HTMLDivElement>();
  refWidgetContainer = React.createRef<HTMLDivElement>();
  triggerCompilation = util.debounce(400, () => {
    // TODO: compile without saving
    this.props.onSave(this.model.getValue());
  }, { signal: this.controller.signal });

  componentDidMount() {
    this.pool.add(async () => {
      let blob = await this.props.draft.item.getMainFile();

      if (!blob) {
        return;
      }

      let source = await blob.text();

      if (source === null) {
        return;
      }

      this.editor = monaco.editor.create(this.ref.current!, {
        value: source,
        automaticLayout: true,
        // contextmenu: false,
        language: 'yaml',
        minimap: { enabled: false },
        occurrencesHighlight: false,
        renderWhitespace: 'trailing',
        // scrollBeyondLastLine: false,
        selectionHighlight: false,
        tabSize: 2,
        overflowWidgetsDomNode: this.refWidgetContainer.current!,
        fixedOverflowWidgets: true
        // readOnly: true
      });

      this.model = this.editor.getModel()!;

      this.model.onDidChangeContent(() => {
        monaco.editor.setModelMarkers(this.model, 'main', []);
        this.triggerCompilation();
      });

      this.updateErrors();
    });
  }

  componentDidUpdate() {
    this.updateErrors({ reveal: true });
  }

  componentWillUnmount() {
    this.controller.abort();
  }

  updateErrors(options?: { reveal?: boolean; }) {
    let compiled = this.props.draft.compiled;

    if (compiled) {
      monaco.editor.setModelMarkers(this.model, 'main', compiled.errors.map((error) => {
        // TODO: show error somewhere else
        let [startIndex, endIndex] = error.range ?? [0, this.model.getValueLength()];
        let start = this.model.getPositionAt(startIndex);
        let end = this.model.getPositionAt(endIndex);

        if (options?.reveal && (compiled!.errors.length === 1)) {
          this.editor.revealLines(start.lineNumber, end.lineNumber);
        }

        return {
          startColumn: start.column,
          startLineNumber: start.lineNumber,

          endColumn: end.column,
          endLineNumber: end.lineNumber,

          message: error.message,
          severity: monaco.MarkerSeverity.Error
        };
      }));

      // console.log(monaco.editor.getModelMarkers(this.model));
      // console.log(this.editor.getSupportedActions());
    }
  }

  undo() {
    this.editor.trigger(undefined, 'undo', undefined);
  }

  render() {
    return (
      <div className="teditor-outer">
        <div className="teditor-inner">
          <div ref={this.ref} onKeyDown={(event) => {
            if (event.metaKey && (event.key === 's')) {
              event.preventDefault();
              this.props.onSave(this.model.getValue());
            }
          }}/>
          {ReactDOM.createPortal((<div className="monaco-editor" ref={this.refWidgetContainer} />), document.body)}
        </div>
        {((this.props.draft.compiled?.errors.length ?? 0) > 0) && <div className="teditor-views-root">
          <div className="teditor-views-nav-root">
            <nav className="teditor-views-nav-list">
              <button className="teditor-views-nav-entry _selected">Problems</button>
            </nav>
          </div>
          <div className="teditor-views-problem-list">
            {this.props.draft.compiled?.errors.map((error, index) => (
              <button type="button" className="teditor-views-problem-entry" key={index} onClick={() => {
                if (this.props.draft.compiled?.errors.length === 1) {
                  this.editor.trigger('anystring', 'editor.action.marker.next', {});
                }
              }}>
                <Icon name="error" />
                <div className="teditor-views-problem-label">{error.message}</div>
              </button>
            ))}
          </div>
        </div>}
      </div>
    );
  }
}
