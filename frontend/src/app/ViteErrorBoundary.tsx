import { Component, type ReactNode } from 'react';

import { AppErrorFallback } from '@/app/AppErrorFallback';

interface ViteErrorBoundaryProps {
  children: ReactNode;
}

interface ViteErrorBoundaryState {
  error: Error | null;
}

export class ViteErrorBoundary extends Component<ViteErrorBoundaryProps, ViteErrorBoundaryState> {
  state: ViteErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ViteErrorBoundaryState {
    return { error };
  }

  private reset = (): void => {
    this.setState({ error: null });
  };

  render(): ReactNode {
    if (this.state.error !== null) {
      return <AppErrorFallback error={this.state.error} reset={this.reset} />;
    }

    return this.props.children;
  }
}
