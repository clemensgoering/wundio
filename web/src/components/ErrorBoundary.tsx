import { Component, type ReactNode } from "react";

interface Props  { children: ReactNode; fallback?: ReactNode; }
interface State  { error: Error | null; }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    if (this.state.error) {
      return this.props.fallback ?? (
        <div className="flex flex-col items-center justify-center h-full gap-4 p-8 text-center">
          <p className="text-muted text-sm">Seite konnte nicht geladen werden.</p>
          <p className="text-xs font-mono text-muted/50">{this.state.error.message}</p>
          <button
            onClick={() => this.setState({ error: null })}
            className="text-xs text-teal border border-teal/30 rounded-xl px-4 py-2 hover:bg-teal/10 transition-colors"
          >
            Neu laden
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}