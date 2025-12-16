import { ChevronRight, Home } from 'lucide-react';
import { Link } from 'react-router-dom';

const Breadcrumb = ({ items }) => {
  return (
    <nav aria-label="Navegação estrutural" className="mb-4">
      <ol className="flex items-center flex-wrap gap-2 text-sm">
        <li>
          <Link
            to="/"
            className="flex items-center gap-1 text-medium-gray hover:text-tmc-orange transition-colors min-h-[44px] min-w-[44px] justify-center"
            aria-label="Página inicial"
          >
            <Home size={16} aria-hidden="true" />
            <span className="sr-only">Início</span>
          </Link>
        </li>

        {items.map((item, index) => {
          const isLast = index === items.length - 1;

          return (
            <li key={index} className="flex items-center gap-2">
              <ChevronRight size={16} className="text-light-gray" aria-hidden="true" />

              {isLast ? (
                <span
                  className="text-dark-gray font-medium"
                  aria-current="page"
                >
                  {item.label}
                </span>
              ) : (
                <Link
                  to={item.path || item.href}
                  className="text-medium-gray hover:text-tmc-orange transition-colors min-h-[44px] flex items-center px-2"
                >
                  {item.label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
};

export default Breadcrumb;
