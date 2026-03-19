import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useEffect, lazy, Suspense } from 'react';
import Header from './components/layout/Header';
import ErrorBoundary from './components/ui/ErrorBoundary';
import Spinner from './components/ui/Spinner';
import { ArticlesProvider, FiltersProvider, UIProvider, CriarProvider, AuthProvider, useAuth, AiStatusProvider } from './context';
import { ArticlesCacheProvider } from './context/ArticlesCacheContext';
import { OnboardingProvider, OnboardingTour } from './components/onboarding';
import ProtectedRoute from './components/auth/ProtectedRoute';
import AuthLoadingScreen from './components/auth/AuthLoadingScreen';

// Lazy load page components for code splitting
const RedacaoPage = lazy(() => import('./pages/RedacaoPage'));
const CriarPostPage = lazy(() => import('./pages/CriarPostPage'));
const TranscricaoPage = lazy(() => import('./pages/transcricao/TranscricaoPage'));
const MinhasMaterias = lazy(() => import('./pages/MinhasMaterias'));
const ConfiguracoesPage = lazy(() => import('./pages/ConfiguracoesPage'));
const BuscadorPage = lazy(() => import('./pages/config/BuscadorPage'));
const UsuariosPage = lazy(() => import('./pages/config/UsuariosPage'));
const SistemaPage = lazy(() => import('./pages/SistemaPage'));
const CustosPage = lazy(() => import('./pages/config/CustosPage'));

// Novo fluxo de criação de matéria (Rework)
const SelecionarFontePage = lazy(() => import('./pages/criar/index'));
const TextoBasePage = lazy(() => import('./pages/criar/TextoBasePage'));
const ConfigurarPage = lazy(() => import('./pages/criar/ConfigurarPage'));
const RevisarPage = lazy(() => import('./pages/criar/RevisarPage'));

// Auth page
const LoginPage = lazy(() => import('./pages/auth/LoginPage'));

// 404 page
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));

// Component to handle document title updates on route changes
function DocumentTitleUpdater() {
  const location = useLocation();

  useEffect(() => {
    const titles = {
      '/': 'Redação',
      '/login': 'Login',
      '/criar': 'Selecionar Fonte',
      '/criar/texto-base': 'Texto-Base',
      '/criar/configurar': 'Configurações da Matéria',
      '/criar/revisar': 'Revisar Matéria',
      '/criar/editor': 'Editor de Matéria',
      '/transcricao': 'Transcrever Vídeo',
      '/minhas-materias': 'Minhas Matérias',
      '/editar': 'Editar Matéria',
      '/configuracoes': 'Configurações',
      '/configuracoes/buscador': 'Buscador de Notícias - Configurações',
      '/configuracoes/usuarios': 'Usuários - Configurações',
      '/configuracoes/sistema': 'Sistema - Configurações',
      '/configuracoes/custos': 'Custos - Configurações'
    };

    const pageTitle = titles[location.pathname] || 'TMC Redação';
    document.title = pageTitle === 'TMC Redação' ? pageTitle : `${pageTitle} | TMC Redação`;
  }, [location]);

  return null;
}

/**
 * Loading fallback component for Suspense
 * Uses skeleton layout instead of full-page spinner for better perceived performance
 */
const PageLoadingFallback = () => (
  <div className="min-h-screen pt-16 bg-off-white">
    <div className="flex">
      {/* Skeleton sidebar */}
      <div className="hidden lg:block w-72 shrink-0 h-[calc(100vh-4rem)] bg-white border-r border-light-gray p-4">
        <div className="h-10 bg-light-gray animate-pulse rounded mb-4" />
        <div className="space-y-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-8 bg-light-gray/60 animate-pulse rounded" />
          ))}
        </div>
      </div>
      {/* Skeleton main content */}
      <div className="flex-1 p-4 md:p-6">
        <div className="bg-white rounded-xl border border-light-gray p-4 mb-6">
          <div className="h-10 bg-light-gray animate-pulse rounded w-full" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white rounded-xl border border-light-gray p-4 space-y-3">
              <div className="h-6 bg-light-gray animate-pulse rounded w-3/4" />
              <div className="h-4 bg-light-gray/60 animate-pulse rounded w-full" />
              <div className="h-4 bg-light-gray/60 animate-pulse rounded w-2/3" />
            </div>
          ))}
        </div>
      </div>
    </div>
  </div>
);

/**
 * AppContent - Inner component that uses useAuth() for user data
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
function AppContent() {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <AuthLoadingScreen />;

  return (
    <AiStatusProvider>
    <ArticlesProvider>
      <FiltersProvider>
        <ArticlesCacheProvider>
        <UIProvider>
          <CriarProvider>
            <OnboardingProvider userId={user?.id}>
              <DocumentTitleUpdater />
              <OnboardingTour />
              <div className="min-h-screen bg-off-white">
              {/* Skip Navigation Links - Multiple ways to navigate content */}
              {isAuthenticated && (
                <>
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
                </>
              )}

              <main id="main-content" role="main">
                <Suspense fallback={<PageLoadingFallback />}>
                  <Routes>
                    {/* Public Route */}
                    <Route path="/login" element={<LoginPage />} />

                    {/* Protected Routes - Main Pages */}
                    <Route path="/" element={<ProtectedRoute><RedacaoPage /></ProtectedRoute>} />

                    {/* Novo Fluxo de Criação de Matéria */}
                    <Route path="/criar" element={<ProtectedRoute><SelecionarFontePage /></ProtectedRoute>} />
                    <Route path="/criar/texto-base" element={<ProtectedRoute><TextoBasePage /></ProtectedRoute>} />
                    <Route path="/criar/configurar" element={<ProtectedRoute><ConfigurarPage /></ProtectedRoute>} />
                    <Route path="/criar/revisar" element={<ProtectedRoute><RevisarPage /></ProtectedRoute>} />
                    <Route path="/criar/editor" element={<ProtectedRoute><CriarPostPage /></ProtectedRoute>} />

                    {/* Redirects para rotas antigas (compatibilidade) */}
                    <Route path="/selecionar-tema" element={<Navigate to="/criar" replace />} />
                    <Route path="/criar-inspiracao" element={<Navigate to="/criar" replace />} />

                    {/* Other Pages */}
                    <Route path="/transcricao" element={<ProtectedRoute><TranscricaoPage /></ProtectedRoute>} />
                    <Route path="/minhas-materias" element={<ProtectedRoute><MinhasMaterias /></ProtectedRoute>} />
                    <Route path="/editar/:articleId" element={<ProtectedRoute><CriarPostPage /></ProtectedRoute>} />

                    {/* Configuration Pages */}
                    <Route path="/configuracoes" element={<ProtectedRoute><ConfiguracoesPage /></ProtectedRoute>}>
                      <Route index element={<Navigate to="/configuracoes/buscador" replace />} />
                      <Route path="buscador" element={<BuscadorPage />} />
                      <Route path="usuarios" element={<ProtectedRoute permission="manage_users"><UsuariosPage /></ProtectedRoute>} />
                      <Route path="sistema" element={<ProtectedRoute permission="manage_users"><SistemaPage /></ProtectedRoute>} />
                      <Route path="custos" element={<ProtectedRoute permission="manage_users"><CustosPage /></ProtectedRoute>} />
                    </Route>

                    {/* Catch-all: show 404 for authenticated users, redirect to login otherwise */}
                    <Route path="*" element={isAuthenticated ? <NotFoundPage /> : <Navigate to="/login" replace />} />
                  </Routes>
                </Suspense>
              </main>
            </div>
            </OnboardingProvider>
          </CriarProvider>
        </UIProvider>
        </ArticlesCacheProvider>
      </FiltersProvider>
    </ArticlesProvider>
    </AiStatusProvider>
  );
}

function App() {
  return (
    <AuthProvider>
      <ErrorBoundary>
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
      </ErrorBoundary>
    </AuthProvider>
  );
}

export default App;
