import { useState, useEffect, useRef } from 'react';
import { Bell, Settings, User, PenLine, Menu, X, HelpCircle, ChevronDown, FileText, Sparkles, Youtube } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import logo from '../../assets/logo-tmc.svg';

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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [createMenuOpen, setCreateMenuOpen] = useState(false);
  const createMenuRef = useRef(null);

  const createOptions = [
    { path: '/criar', label: 'Do Zero', icon: FileText, description: 'Comece uma matéria em branco' },
    { path: '/criar-inspiracao', label: 'Com Inspiração', icon: Sparkles, description: 'Use matérias como base' },
    { path: '/transcricao', label: 'Transcrever Vídeo', icon: Youtube, description: 'Crie a partir de um vídeo' }
  ];

  const navItems = [
    { path: '/', label: 'Redação' },
    { path: '/transcricao', label: 'Transcrição' },
    { path: '/minhas-materias', label: 'Minhas Matérias' },
    { path: '/configuracoes', label: 'Configurações' }
  ];

  // Handle Escape key to close menus (WCAG 2.1.2 - No Keyboard Trap)
  useEffect(() => {
    const handleEscapeKey = (e) => {
      if (e.key === 'Escape') {
        if (mobileMenuOpen) setMobileMenuOpen(false);
        if (createMenuOpen) setCreateMenuOpen(false);
      }
    };

    document.addEventListener('keydown', handleEscapeKey);
    return () => document.removeEventListener('keydown', handleEscapeKey);
  }, [mobileMenuOpen, createMenuOpen]);

  // Handle click outside to close create menu
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (createMenuRef.current && !createMenuRef.current.contains(e.target)) {
        setCreateMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="bg-tmc-dark-green text-white h-16 fixed top-0 left-0 right-0 z-50 shadow-lg" role="banner">
      <div className="h-full px-4 md:px-6 flex items-center justify-between">
        {/* Left: Logo + Desktop Navigation */}
        <div className="flex items-center gap-4 md:gap-8">
          <Link to="/" className="flex items-center gap-2 min-h-[44px]" aria-label="Página inicial TMC">
            <img src={logo} alt="TMC - The Media Company" className="h-7 md:h-8" />
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
          <div className="relative hidden sm:block" ref={createMenuRef}>
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

          {/* Help Link - Consistent location */}
          <a
            href="#ajuda"
            className="hidden md:flex items-center justify-center p-2 hover:bg-tmc-light-green/50 rounded-lg transition-colors min-h-[44px] min-w-[44px]"
            aria-label="Central de ajuda"
            title="Ajuda"
          >
            <HelpCircle size={20} aria-hidden="true" />
          </a>

          {/* Notifications - Hidden on mobile */}
          <button
            type="button"
            className="hidden md:flex items-center justify-center p-2 hover:bg-tmc-light-green/50 rounded-lg transition-colors relative min-h-[44px] min-w-[44px]"
            aria-label="Notificações - 1 nova notificação"
          >
            <Bell size={20} aria-hidden="true" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-live-red rounded-full" aria-hidden="true"></span>
          </button>

          {/* Settings - Hidden on mobile */}
          <button
            type="button"
            className="hidden md:flex items-center justify-center p-2 hover:bg-tmc-light-green/50 rounded-lg transition-colors min-h-[44px] min-w-[44px]"
            aria-label="Configurações"
          >
            <Settings size={20} aria-hidden="true" />
          </button>

          {/* User Info - Simplified on mobile */}
          <div className="hidden md:flex items-center gap-3 pl-4 border-l border-white/20" role="region" aria-label="Informações do usuário">
            <div className="text-right hidden lg:block">
              <p className="text-sm font-medium">João Silva</p>
              <p className="text-xs text-white/60">Redator</p>
            </div>
            <div className="w-9 h-9 bg-tmc-orange rounded-full flex items-center justify-center" aria-hidden="true">
              <User size={20} />
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
                  <User size={20} />
                </div>
                <div>
                  <p className="text-sm font-medium">João Silva</p>
                  <p className="text-xs text-white/60">Redator</p>
                </div>
              </div>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
};

export default Header;
