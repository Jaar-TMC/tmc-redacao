import { Component } from 'react';
import PropTypes from 'prop-types';
import { AlertCircle, RefreshCw } from 'lucide-react';

/**
 * Error boundary component to catch and handle React errors gracefully
 * Wraps child components and displays fallback UI on error
 * @example
 * <ErrorBoundary>
 *   <YourComponent />
 * </ErrorBoundary>
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log error details for debugging
    // eslint-disable-next-line no-console
    console.error('Error caught by ErrorBoundary:', error, errorInfo);
    this.setState({
      error,
      errorInfo
    });

    // You can also log the error to an error reporting service here
    // logErrorToService(error, errorInfo);
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default fallback UI
      return (
        <div className="min-h-screen bg-off-white flex items-center justify-center p-4">
          <div className="bg-white rounded-xl border border-light-gray shadow-sm p-8 max-w-lg w-full text-center">
            <div className="w-16 h-16 bg-error/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <AlertCircle size={32} className="text-error" />
            </div>

            <h2 className="text-2xl font-bold text-dark-gray mb-2">
              Oops! Algo deu errado
            </h2>

            <p className="text-medium-gray mb-6">
              Ocorreu um erro inesperado. Tente recarregar a página ou entre em contato com o suporte se o problema persistir.
            </p>

            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="text-left mb-6 p-4 bg-off-white rounded-lg">
                <summary className="cursor-pointer font-medium text-sm text-dark-gray mb-2">
                  Detalhes do erro (desenvolvimento)
                </summary>
                <pre className="text-xs text-error overflow-auto">
                  {this.state.error.toString()}
                  {this.state.errorInfo?.componentStack}
                </pre>
              </details>
            )}

            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleReset}
                className="px-6 py-2.5 border border-light-gray rounded-lg text-medium-gray hover:bg-off-white transition-colors font-medium"
              >
                Tentar novamente
              </button>
              <button
                onClick={() => window.location.href = '/'}
                className="px-6 py-2.5 bg-tmc-orange text-white rounded-lg font-semibold hover:bg-tmc-orange/90 transition-colors flex items-center gap-2"
              >
                <RefreshCw size={18} />
                Voltar ao início
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

ErrorBoundary.propTypes = {
  children: PropTypes.node.isRequired,
  fallback: PropTypes.node
};

export default ErrorBoundary;
