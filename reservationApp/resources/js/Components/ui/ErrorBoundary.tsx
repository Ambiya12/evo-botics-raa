import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: (error: Error, componentStack: string) => ReactNode;
}

interface State {
  error: Error | null;
  componentStack: string;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null, componentStack: "" };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("[ErrorBoundary] caught render crash:", error);
    console.error("[ErrorBoundary] component stack:", info.componentStack);
    this.setState({ componentStack: info.componentStack ?? "" });
  }

  render(): ReactNode {
    const { error, componentStack } = this.state;
    if (error) {
      if (this.props.fallback) {
        return this.props.fallback(error, componentStack);
      }
      return (
        <div className="panel" style={{ padding: "1rem", color: "red" }}>
          <strong>[Debug] Render crash:</strong> {error.message}
          <pre style={{ fontSize: "11px", marginTop: "0.5rem", whiteSpace: "pre-wrap" }}>
            {componentStack}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}
