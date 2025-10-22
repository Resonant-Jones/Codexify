import React from "react";

type Props = { children: React.ReactNode };
type State = { hasError: boolean };

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: any, info: any) {
    // eslint-disable-next-line no-console
    console.error("ErrorBoundary caught", { error, info });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-4 text-sm">
          Something went wrong in this section. Please reload.
        </div>
      );
    }
    return this.props.children as any;
  }
}

export default ErrorBoundary;

