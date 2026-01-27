/**
 * CategorySelector - Card-based category selection UI
 *
 * Displays the 5 TMC editorial categories as selectable cards.
 * Each card shows icon, name, description, and reference style.
 */

import PropTypes from 'prop-types';
import { CATEGORIAS_EDITORIAIS, CATEGORIAS_ARRAY } from '../../constants/editorial';

const CategorySelector = ({
  selectedCategory,
  onCategoryChange,
  className = ''
}) => {
  return (
    <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 ${className}`}>
      {CATEGORIAS_ARRAY.map((categoria) => {
        const Icon = categoria.icon;
        const isSelected = selectedCategory === categoria.id;
        const { colorClasses } = categoria;

        return (
          <button
            key={categoria.id}
            type="button"
            onClick={() => onCategoryChange(categoria.id)}
            className={`
              relative p-4 rounded-xl border-2 text-left transition-all duration-200
              hover:shadow-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-tmc-orange
              ${isSelected
                ? `${colorClasses.bg} ${colorClasses.border} shadow-sm`
                : 'bg-white border-light-gray hover:border-gray-300'
              }
            `}
          >
            {/* Selected indicator */}
            {isSelected && (
              <div className={`absolute top-2 right-2 w-2 h-2 rounded-full ${colorClasses.border.replace('border-', 'bg-')}`} />
            )}

            {/* Icon and Name */}
            <div className="flex items-center gap-3 mb-2">
              <div className={`p-2 rounded-lg ${isSelected ? colorClasses.bg : 'bg-off-white'}`}>
                <Icon
                  size={20}
                  className={isSelected ? colorClasses.icon : 'text-medium-gray'}
                />
              </div>
              <h3 className={`font-semibold ${isSelected ? colorClasses.text : 'text-dark-gray'}`}>
                {categoria.name}
              </h3>
            </div>

            {/* Description */}
            <p className="text-sm text-medium-gray leading-snug">
              {categoria.description}
            </p>

            {/* Opinion badge */}
            {categoria.allowsOpinion && (
              <div className="mt-2">
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-700">
                  Permite Opiniao
                </span>
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
};

CategorySelector.propTypes = {
  selectedCategory: PropTypes.string.isRequired,
  onCategoryChange: PropTypes.func.isRequired,
  className: PropTypes.string
};

export default CategorySelector;
