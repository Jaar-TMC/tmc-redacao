import { useState, useRef, useEffect, useMemo } from 'react';
import PropTypes from 'prop-types';
import { Search, ChevronDown, X } from 'lucide-react';

/**
 * SearchableSelect - Dropdown com campo de busca
 *
 * Permite filtrar opções digitando no campo de busca
 */
const SearchableSelect = ({
  value,
  onChange,
  options,
  placeholder = 'Selecione...',
  allLabel = 'Todos',
  className = ''
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const containerRef = useRef(null);
  const inputRef = useRef(null);

  // Fechar dropdown ao clicar fora
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
        setSearchQuery('');
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Focar no input quando abrir
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Filtrar opções baseado na busca
  const filteredOptions = useMemo(() => {
    if (!searchQuery.trim()) return options;
    const query = searchQuery.toLowerCase();
    return options.filter(opt =>
      opt.label.toLowerCase().includes(query) ||
      opt.value.toLowerCase().includes(query)
    );
  }, [options, searchQuery]);

  // Encontrar label do valor selecionado
  const selectedLabel = useMemo(() => {
    if (value === 'all') return allLabel;
    const option = options.find(opt => opt.value === value);
    return option?.label || value;
  }, [value, options, allLabel]);

  const handleSelect = (optionValue) => {
    onChange(optionValue);
    setIsOpen(false);
    setSearchQuery('');
  };

  const handleClear = (e) => {
    e.stopPropagation();
    onChange('all');
    setSearchQuery('');
  };

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full px-3 py-2 pr-8 border rounded-lg text-sm bg-white text-left cursor-pointer focus:outline-none transition-colors flex items-center justify-between ${
          isOpen ? 'border-tmc-orange ring-2 ring-tmc-orange/20' : 'border-light-gray hover:border-medium-gray'
        }`}
      >
        <span className={value === 'all' ? 'text-medium-gray' : 'text-dark-gray'}>
          {selectedLabel}
        </span>
        <div className="flex items-center gap-1">
          {value !== 'all' && (
            <button
              type="button"
              onClick={handleClear}
              className="p-0.5 hover:bg-off-white rounded"
              aria-label="Limpar seleção"
            >
              <X size={14} className="text-medium-gray" />
            </button>
          )}
          <ChevronDown
            size={16}
            className={`text-medium-gray transition-transform ${isOpen ? 'rotate-180' : ''}`}
          />
        </div>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-light-gray rounded-lg shadow-lg overflow-hidden">
          {/* Search Input */}
          <div className="p-2 border-b border-light-gray">
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-medium-gray" />
              <input
                ref={inputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={placeholder}
                className="w-full pl-8 pr-3 py-1.5 text-sm border border-light-gray rounded focus:outline-none focus:border-tmc-orange"
              />
            </div>
          </div>

          {/* Options List */}
          <div className="max-h-48 overflow-y-auto">
            {/* "All" Option */}
            <button
              type="button"
              onClick={() => handleSelect('all')}
              className={`w-full px-3 py-2 text-sm text-left hover:bg-off-white transition-colors ${
                value === 'all' ? 'bg-orange-50 text-tmc-orange font-medium' : 'text-dark-gray'
              }`}
            >
              {allLabel}
            </button>

            {/* Filtered Options */}
            {filteredOptions.length === 0 ? (
              <div className="px-3 py-4 text-sm text-medium-gray text-center">
                Nenhum resultado encontrado
              </div>
            ) : (
              filteredOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => handleSelect(option.value)}
                  className={`w-full px-3 py-2 text-sm text-left hover:bg-off-white transition-colors ${
                    value === option.value ? 'bg-orange-50 text-tmc-orange font-medium' : 'text-dark-gray'
                  }`}
                >
                  {option.label}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

SearchableSelect.propTypes = {
  value: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  options: PropTypes.arrayOf(PropTypes.shape({
    value: PropTypes.string.isRequired,
    label: PropTypes.string.isRequired,
  })).isRequired,
  placeholder: PropTypes.string,
  allLabel: PropTypes.string,
  className: PropTypes.string,
};

export default SearchableSelect;
