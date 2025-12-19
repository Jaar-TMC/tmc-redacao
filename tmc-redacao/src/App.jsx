import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useEffect, lazy, Suspense } from 'react';
import Header from './components/layout/Header';
import ErrorBoundary from './components/ui/ErrorBoundary';
import Spinner from './components/ui/Spinner';
import { ArticlesProvider, FiltersProvider, UIProvider, CriarProvider } from './context';
import PropTypes from 'prop-types';

// Lazy load page components for code splitting
const RedacaoPage = lazy(() => import('./pages/RedacaoPage'));
const SelecionarTemaPage = lazy(() => import('./pages/SelecionarTemaPage'));
const CriarPostPage = lazy(() => import('./pages/CriarPostPage'));
const CriarInspiracaoPage = lazy(() => import('./pages/CriarInspiracaoPage'));
const TranscricaoPage = lazy(() => import('./pages/transcricao/TranscricaoPage'));
const MinhasMaterias = lazy(() => import('./pages/MinhasMaterias'));
const ConfiguracoesPage = lazy(() => import('./pages/ConfiguracoesPage'));
const BuscadorPage = lazy(() => import('./pages/config/BuscadorPage'));
const TrendsPage = lazy(() => import('./pages/config/TrendsPage'));

// Novo fluxo de criação de matéria (Rework)
const SelecionarFontePage = lazy(() => import('./pages/criar/index'));
const TextoBasePage = lazy(() => import('./pages/criar/TextoBasePage'));
const ConfigurarPage = lazy(() => import('./pages/criar/ConfigurarPage'));
const RevisarPage = lazy(() => import('./pages/criar/RevisarPage'));

// Component to handle document title updates on route changes
function DocumentTitleUpdater() {
  const location = useLocation();

  useEffect(() => {
    const titles = {
      '/': 'Redação',
      '/criar': 'Selecionar Fonte',
      '/criar/texto-base': 'Texto-Base',
      '/criar/configurar': 'Configurações da Matéria',
      '/criar/revisar': 'Revisar Matéria',
      '/criar/editor': 'Editor de Matéria',
      '/selecionar-tema': 'Selecionar Tema',
      '/criar-inspiracao': 'Criar com Inspiração',
      '/transcricao': 'Transcrever Vídeo',
      '/minhas-materias': 'Minhas Matérias',
      '/configuracoes': 'Configurações',
      '/configuracoes/buscador': 'Buscador de Notícias - Configurações',
      '/configuracoes/trends': 'Google Trends - Configurações',
      '/configuracoes/perfil': 'Perfil - Configurações',
      '/configuracoes/integracoes': 'Integrações - Configurações',
      '/configuracoes/preferencias': 'Preferências - Configurações'
    };

    const pageTitle = titles[location.pathname] || 'TMC Redação';
    document.title = pageTitle === 'TMC Redação' ? pageTitle : `${pageTitle} | TMC Redação`;
  }, [location]);

  return null;
}

/**
 * Loading fallback component for Suspense
 */
const PageLoadingFallback = () => (
  <div className="flex items-center justify-center min-h-screen bg-off-white">
    <Spinner size="lg" />
  </div>
);

/**
 * App Component
 *
 * WCAG 2.1 Compliance - Multiple Ways (2.4.5):
 * The application provides multiple ways to find and navigate content:
 *
 * 1. Main Navigation Menu (Header):
 *    - Consistent navigation links to all major sections
 *    - Available on every page via the header
 *    - Keyboard accessible and clearly labeled
 *
 * 2. Search Functionality (FilterBar):
 *    - Text search to find articles by title or content
 *    - Filter by category, source, and time period
 *    - Available on main content pages
 *
 * 3. Skip Navigation Links:
 *    - Direct keyboard access to main content
 *    - Skip to search functionality
 *    - Improves keyboard navigation efficiency
 *
 * 4. Breadcrumbs (where applicable):
 *    - Show current location in hierarchy
 *    - Allow quick navigation to parent sections
 *
 * 5. Direct Links:
 *    - Article cards link to source content
 *    - Configuration pages provide direct access to settings
 *
 * Future Enhancements:
 * - Consider adding a sitemap page
 * - Consider adding an index/glossary for larger content
 */
function App() {
  return (
    <ErrorBoundary>
      <Router>
        <ArticlesProvider>
          <FiltersProvider>
            <UIProvider>
              <CriarProvider>
              <DocumentTitleUpdater />
              <div className="min-h-screen bg-off-white">
                {/* Skip Navigation Links - Multiple ways to navigate content */}
                <a
                  href="#main-content"
                  className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-tmc-orange focus:text-white focus:rounded-lg focus:font-semibold min-h-[44px] min-w-[44px]"
                >
                  Pular para o conteúdo principal
                </a>
                <a
                  href="#site-search"
                  className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-64 focus:z-50 focus:px-4 focus:py-2 focus:bg-tmc-orange focus:text-white focus:rounded-lg focus:font-semibold min-h-[44px] min-w-[44px]"
                >
                  Ir para busca
                </a>

                <Header />

                {/* Site-wide Search - Placeholder for multiple ways to find content */}
                <div id="site-search" className="sr-only" role="search" aria-label="Busca no site">
                  <p>
                    Busca do site: Use a barra de filtros na página principal para buscar matérias.
                    Use o menu de navegação para acessar diferentes seções do sistema.
                  </p>
                </div>

                <main id="main-content" role="main">
                  <Suspense fallback={<PageLoadingFallback />}>
                    <Routes>
                      {/* Main Pages */}
                      <Route path="/" element={<RedacaoPage />} />

                      {/* Novo Fluxo de Criação de Matéria */}
                      <Route path="/criar" element={<SelecionarFontePage />} />
                      <Route path="/criar/texto-base" element={<TextoBasePage />} />
                      <Route path="/criar/configurar" element={<ConfigurarPage />} />
                      <Route path="/criar/revisar" element={<RevisarPage />} />
                      <Route path="/criar/editor" element={<CriarPostPage />} />

                      {/* Fluxo Antigo (manter temporariamente para compatibilidade) */}
                      <Route path="/selecionar-tema" element={<SelecionarTemaPage />} />
                      <Route path="/criar-inspiracao" element={<CriarInspiracaoPage />} />

                      {/* Other Pages */}
                      <Route path="/transcricao" element={<TranscricaoPage />} />
                      <Route path="/minhas-materias" element={<MinhasMaterias />} />

                      {/* Configuration Pages */}
                      <Route path="/configuracoes" element={<ConfiguracoesPage />}>
                        <Route index element={<Navigate to="/configuracoes/buscador" replace />} />
                        <Route path="buscador" element={<BuscadorPage />} />
                        <Route path="trends" element={<TrendsPage />} />
                        <Route path="perfil" element={<PlaceholderPage title="Perfil" />} />
                        <Route path="integracoes" element={<PlaceholderPage title="Integrações" />} />
                        <Route path="preferencias" element={<PlaceholderPage title="Preferências" />} />
                      </Route>
                    </Routes>
                  </Suspense>
                </main>
              </div>
              </CriarProvider>
            </UIProvider>
          </FiltersProvider>
        </ArticlesProvider>
      </Router>
    </ErrorBoundary>
  );
}

// Placeholder for pages not yet implemented
function PlaceholderPage({ title }) {
  return (
    <div className="flex items-center justify-center h-96">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-dark-gray mb-2">{title}</h2>
        <p className="text-medium-gray">Esta página está em desenvolvimento.</p>
      </div>
    </div>
  );
}

PlaceholderPage.propTypes = {
  title: PropTypes.string.isRequired,
};

export default App;
