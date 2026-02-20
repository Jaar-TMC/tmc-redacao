import { useState, useEffect, useRef } from 'react';
import { User, PenLine, Menu, X, HelpCircle, ChevronDown, FileText, Youtube, LogOut } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import LogoTMC from '../../assets/logo-tmc.svg?react';
import { useAuth } from '../../context/AuthContext';
import usePermissions from '../../hooks/usePermissions';
import { useOnboarding, TOUR_IDS } from '../onboarding';

/**
 * Header Component
 *
 * WCAG 2.1 Compliance:
 * - No Keyboard Trap (2.1.2): Mobile menu can be closed with Escape key and keyboard navigation
 * - Focus Order (2.4.3): Tab order follows visual order left to right
 * - Headings and Labels (2.4.6): All interactive elements have clear, descriptive labels
 * - Consistent Navigation (3.2.3): Navigation items maintain consistent order across pages
 */
const Header = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { isAdmin } = usePermissions();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [createMenuOpen, setCreateMenuOpen] = useState(false);
  const [helpMenuOpen, setHelpMenuOpen] = useState(false);
  const createMenuRef = useRef(null);
  const helpMenuRef = useRef(null);
  const { resetTour, startTour, resetAllTours } = useOnboarding();

  // Get user display name and role
  const displayName = user?.name || 'Usuário';
  const userRole = user?.role || 'user';

  const createOptions = [
    { path: '/criar', label: 'Nova Matéria', icon: FileText, description: 'Escolha sua fonte inicial' },
    { path: '/transcricao', label: 'Transcrever Vídeo', icon: Youtube, description: 'Crie a partir de um vídeo' }
  ];

  const navItems = [
    { path: '/', label: 'Redação' },
    { path: '/transcricao', label: 'Transcrição' },
    { path: '/minhas-materias', label: 'Minhas Matérias' },
    // Only show Configurações to admins
    ...(isAdmin ? [{ path: '/configuracoes', label: 'Configurações' }] : [])
  ];

  // Handle Escape key to close menus (WCAG 2.1.2 - No Keyboard Trap)
  useEffect(() => {
    const handleEscapeKey = (e) => {
      if (e.key === 'Escape') {
        if (mobileMenuOpen) setMobileMenuOpen(false);
        if (createMenuOpen) setCreateMenuOpen(false);
        if (helpMenuOpen) setHelpMenuOpen(false);
      }
    };

    document.addEventListener('keydown', handleEscapeKey);
    return () => document.removeEventListener('keydown', handleEscapeKey);
  }, [mobileMenuOpen, createMenuOpen, helpMenuOpen]);

  // Handle click outside to close menus
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (createMenuRef.current && !createMenuRef.current.contains(e.target)) {
        setCreateMenuOpen(false);
      }
      if (helpMenuRef.current && !helpMenuRef.current.contains(e.target)) {
        setHelpMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Map tour IDs to their corresponding routes
  const tourRoutes = {
    [TOUR_IDS.HOME]: '/',
    [TOUR_IDS.CRIAR]: '/criar',
    [TOUR_IDS.EDITOR]: '/criar/editor'
  };

  // Handle starting a tour from help menu
  const handleStartTour = (tourId) => {
    setHelpMenuOpen(false);
    resetTour(tourId);

    const targetRoute = tourRoutes[tourId];
    const isOnTargetPage = location.pathname === targetRoute;

    if (isOnTargetPage) {
      // Already on the correct page, just start the tour
      setTimeout(() => startTour(tourId), 100);
    } else {
      // Navigate to the correct page first, then start the tour
      navigate(targetRoute);
      // Longer delay to allow page to load
      setTimeout(() => startTour(tourId), 800);
    }
  };

  // Get current page tour ID
  const getCurrentTourId = () => {
    if (location.pathname === '/') return TOUR_IDS.HOME;
    if (location.pathname === '/criar') return TOUR_IDS.CRIAR;
    if (location.pathname === '/criar/editor') return TOUR_IDS.EDITOR;
    return null;
  };

  const headerClasses = "bg-tmc-dark-green text-white h-16 fixed top-0 left-0 right-0 z-50 shadow-lg";

  return (
    <header className={headerClasses} role="banner">
      <div className="h-full px-4 md:px-6 flex items-center justify-between">
        {/* Left: Logo + Desktop Navigation */}
        <div className="flex items-center gap-4 md:gap-8">
          <Link to="/" className="flex items-center gap-2 min-h-[44px]" aria-label="Página inicial TMC">
            <LogoTMC className="h-12 w-auto" aria-label="TMC - The Media Company" />
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex items-center gap-2" role="navigation" aria-label="Navegação principal">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                aria-current={location.pathname === item.path ? 'page' : undefined}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  location.pathname === item.path
                    ? 'bg-tmc-orange text-white'
                    : 'text-white/80 hover:text-white hover:bg-tmc-light-green/50'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>

        {/* Right: Actions + User */}
        <div className="flex items-center gap-2 md:gap-4">
          {/* Create Dropdown - Hidden on small mobile */}
          <div className="relative hidden sm:block" ref={createMenuRef} data-tour="create-button">
            <button
              type="button"
              onClick={() => setCreateMenuOpen(!createMenuOpen)}
              className="flex items-center gap-2 bg-tmc-orange hover:bg-tmc-orange/90 text-white px-3 md:px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
              aria-label="Abrir menu de criação"
              aria-expanded={createMenuOpen}
              aria-haspopup="true"
            >
              <PenLine size={18} aria-hidden="true" />
              <span className="hidden md:inline">Criar</span>
              <ChevronDown size={16} className={`transition-transform ${createMenuOpen ? 'rotate-180' : ''}`} aria-hidden="true" />
            </button>

            {/* Dropdown Menu */}
            {createMenuOpen && (
              <div className="absolute right-0 mt-2 w-64 bg-white rounded-xl shadow-xl border border-gray-100 py-2 z-50">
                {createOptions.map((option) => {
                  const Icon = option.icon;
                  return (
                    <Link
                      key={option.path}
                      to={option.path}
                      onClick={() => setCreateMenuOpen(false)}
                      className="flex items-start gap-3 px-4 py-3 hover:bg-gray-50 transition-colors"
                    >
                      <div className="w-8 h-8 rounded-lg bg-tmc-orange/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <Icon size={16} className="text-tmc-orange" aria-hidden="true" />
                      </div>
                      <div>
                        <span className="block text-sm font-medium text-gray-900">{option.label}</span>
                        <span className="block text-xs text-gray-500">{option.description}</span>
                      </div>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>

          {/* Help Menu - Tour Controls */}
          <div className="relative hidden md:block" ref={helpMenuRef}>
            <button
              type="button"
              onClick={() => setHelpMenuOpen(!helpMenuOpen)}
              className="flex items-center justify-center p-2 hover:bg-tmc-light-green/50 rounded-lg transition-colors min-h-[44px] min-w-[44px]"
              aria-label="Menu de ajuda"
              aria-expanded={helpMenuOpen}
              aria-haspopup="true"
              title="Ajuda"
            >
              <HelpCircle size={20} aria-hidden="true" />
            </button>

            {/* Help Dropdown Menu */}
            {helpMenuOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-xl border border-gray-100 py-2 z-50">
                <div className="px-4 py-2 border-b border-gray-100">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Tours Guiados</p>
                </div>

                {getCurrentTourId() && (
                  <button
                    onClick={() => handleStartTour(getCurrentTourId())}
                    className="w-full flex items-start gap-3 px-4 py-3 hover:bg-gray-50 transition-colors text-left"
                  >
                    <div className="w-8 h-8 rounded-lg bg-tmc-orange/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <HelpCircle size={16} className="text-tmc-orange" aria-hidden="true" />
                    </div>
                    <div>
                      <span className="block text-sm font-medium text-gray-900">Tour desta página</span>
                      <span className="block text-xs text-gray-500">Aprenda a usar esta tela</span>
                    </div>
                  </button>
                )}

                <button
                  onClick={() => handleStartTour(TOUR_IDS.HOME)}
                  className="w-full flex items-start gap-3 px-4 py-3 hover:bg-gray-50 transition-colors text-left"
                >
                  <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <FileText size={16} className="text-blue-600" aria-hidden="true" />
                  </div>
                  <div>
                    <span className="block text-sm font-medium text-gray-900">Tour da Redação</span>
                    <span className="block text-xs text-gray-500">Conheça a tela principal</span>
                  </div>
                </button>

                <button
                  onClick={() => handleStartTour(TOUR_IDS.CRIAR)}
                  className="w-full flex items-start gap-3 px-4 py-3 hover:bg-gray-50 transition-colors text-left"
                >
                  <div className="w-8 h-8 rounded-lg bg-green-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <PenLine size={16} className="text-green-600" aria-hidden="true" />
                  </div>
                  <div>
                    <span className="block text-sm font-medium text-gray-900">Tour de Criação</span>
                    <span className="block text-xs text-gray-500">Como criar matérias</span>
                  </div>
                </button>

                <div className="border-t border-gray-100 mt-2 pt-2">
                  <button
                    onClick={() => {
                      resetAllTours();
                      setHelpMenuOpen(false);
                    }}
                    className="w-full px-4 py-2 text-left text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    Reiniciar todos os tours
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Logout - Hidden on mobile */}
          <button
            type="button"
            onClick={logout}
            className="hidden md:flex items-center justify-center p-2 hover:bg-tmc-light-green/50 rounded-lg transition-colors min-h-[44px] min-w-[44px]"
            aria-label="Sair"
            title="Sair"
          >
            <LogOut size={20} aria-hidden="true" />
          </button>

          {/* User Info - Simplified on mobile */}
          <div className="hidden md:flex items-center gap-3 pl-4 border-l border-white/20" role="region" aria-label="Informações do usuário">
            <div className="text-right hidden lg:block">
              <p className="text-sm font-medium">{displayName}</p>
              <p className="text-xs text-white/60 capitalize">{userRole}</p>
            </div>
            <div className="w-9 h-9 bg-tmc-orange rounded-full flex items-center justify-center" aria-hidden="true">
              <span className="text-sm font-bold text-white">{displayName.charAt(0).toUpperCase()}</span>
            </div>
          </div>

          {/* Mobile Menu Button */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden p-2 hover:bg-tmc-light-green/50 rounded-lg transition-colors min-h-[44px] min-w-[44px]"
            aria-label={mobileMenuOpen ? "Fechar menu" : "Abrir menu"}
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-navigation"
          >
            {mobileMenuOpen ? <X size={24} aria-hidden="true" /> : <Menu size={24} aria-hidden="true" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div
          id="mobile-navigation"
          className="lg:hidden absolute top-16 left-0 right-0 bg-tmc-dark-green border-t border-tmc-light-green/30 shadow-lg"
        >
          <nav className="flex flex-col p-4 space-y-2" role="navigation" aria-label="Navegação móvel">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileMenuOpen(false)}
                aria-current={location.pathname === item.path ? 'page' : undefined}
                className={`px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                  location.pathname === item.path
                    ? 'bg-tmc-orange text-white'
                    : 'text-white/80 hover:text-white hover:bg-tmc-light-green/50'
                }`}
              >
                {item.label}
              </Link>
            ))}

            {/* Mobile-only links */}
            <div className="pt-2 border-t border-white/20 space-y-2">
              {/* Create options for mobile */}
              <div className="sm:hidden space-y-1">
                <p className="px-4 py-1 text-xs text-white/60 uppercase tracking-wide">Criar Matéria</p>
                {createOptions.map((option) => {
                  const Icon = option.icon;
                  return (
                    <Link
                      key={option.path}
                      to={option.path}
                      onClick={() => setMobileMenuOpen(false)}
                      className="flex items-center gap-3 px-4 py-3 hover:bg-tmc-light-green/50 rounded-lg text-sm"
                    >
                      <Icon size={18} aria-hidden="true" />
                      <span>{option.label}</span>
                    </Link>
                  );
                })}
              </div>

              <div className="md:hidden flex items-center gap-3 px-4 py-3 bg-tmc-light-green/20 rounded-lg" role="region" aria-label="Informações do usuário">
                <div className="w-9 h-9 bg-tmc-orange rounded-full flex items-center justify-center" aria-hidden="true">
                  <span className="text-sm font-bold text-white">{displayName.charAt(0).toUpperCase()}</span>
                </div>
                <div>
                  <p className="text-sm font-medium">{displayName}</p>
                  <p className="text-xs text-white/60 capitalize">{userRole}</p>
                </div>
              </div>

              {/* Mobile Logout Button */}
              <button
                onClick={() => { logout(); setMobileMenuOpen(false); }}
                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-red-500/20 rounded-lg text-sm text-red-300"
              >
                <LogOut size={18} aria-hidden="true" />
                <span>Sair</span>
              </button>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
};

export default Header;
