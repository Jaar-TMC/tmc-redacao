import { useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { Newspaper, TrendingUp, User, Plug, Settings, Menu, X } from 'lucide-react';

const ConfiguracoesPage = () => {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const menuItems = [
    { path: '/configuracoes/buscador', label: 'Buscador de Notícias', icon: Newspaper },
    { path: '/configuracoes/trends', label: 'Google Trends', icon: TrendingUp },
    { path: '/configuracoes/perfil', label: 'Perfil', icon: User },
    { path: '/configuracoes/integracoes', label: 'Integrações', icon: Plug },
    { path: '/configuracoes/preferencias', label: 'Preferências', icon: Settings }
  ];

  const currentMenuItem = menuItems.find(item => item.path === location.pathname);

  return (
    <div className="min-h-screen pt-16 bg-off-white">
      {/* Mobile Header */}
      <div className="md:hidden bg-white border-b border-light-gray px-4 py-3 flex items-center justify-between">
        <h1 className="text-lg font-bold text-dark-gray">
          {currentMenuItem ? currentMenuItem.label : 'Configurações'}
        </h1>
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 hover:bg-off-white rounded-lg transition-colors"
        >
          <Menu size={24} className="text-dark-gray" />
        </button>
      </div>

      <div className="flex">
        {/* Mobile Overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-40 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Sidebar */}
        <aside className={`
          w-64 bg-white border-r border-light-gray min-h-[calc(100vh-4rem)] sticky top-16
          md:block
          ${sidebarOpen
            ? 'fixed top-16 left-0 bottom-0 z-50'
            : 'hidden'
          }
        `}>
          <div className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-dark-gray">Configurações</h2>
              <button
                onClick={() => setSidebarOpen(false)}
                className="md:hidden p-1 hover:bg-off-white rounded transition-colors"
              >
                <X size={20} className="text-medium-gray" />
              </button>
            </div>
            <nav className="space-y-1">
              {menuItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;

                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    onClick={() => setSidebarOpen(false)}
                    className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-tmc-orange text-white'
                        : 'text-medium-gray hover:bg-off-white hover:text-dark-gray'
                    }`}
                  >
                    <Icon size={20} />
                    <span className="text-sm font-medium">{item.label}</span>
                  </NavLink>
                );
              })}
            </nav>
          </div>
        </aside>

        {/* Content */}
        <main className="flex-1 p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default ConfiguracoesPage;
