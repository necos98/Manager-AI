import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "@/shared/components/ui/button";

interface Props {
  children: ReactNode;
  /** Optional custom fallback. When omitted a default message is shown. */
  fallback?: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error("ErrorBoundary caught:", error, info);
  }

  reset = () => this.setState({ error: null });

  render() {
    if (!this.state.error) return this.props.children;
    if (this.props.fallback) return this.props.fallback;
    return (
      <div
        role="alert"
        className="flex min-h-[40vh] flex-col items-center justify-center gap-4 p-6"
      >
        <h2 className="text-lg font-semibold">Something went wrong</h2>
        <p className="max-w-md text-center text-sm text-muted-foreground">
          {this.state.error.message}
        </p>
        <Button
          onClick={this.reset}
          aria-label="Retry rendering this section"
        >
          Try again
        </Button>
      </div>
    );
  }
}
