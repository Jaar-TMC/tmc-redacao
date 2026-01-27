/**
 * CategoryGuidelines - DOs/DON'Ts display panel
 *
 * Shows category-specific editorial guidelines with visual
 * distinction between allowed and prohibited practices.
 * Collapsible by default, expands on user click.
 */

import { useState } from 'react';
import PropTypes from 'prop-types';
import { CheckCircle, XCircle, ChevronDown, ChevronUp, BookOpen } from 'lucide-react';
import { CATEGORIAS_EDITORIAIS } from '../../constants/editorial';

const CategoryGuidelines = ({
  categoryId,
  defaultExpanded = false,
  className = ''
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const categoria = CATEGORIAS_EDITORIAIS[categoryId];

  if (!categoria) {
    return null;
  }

  const { dos, donts, colorClasses, name } = categoria;

  return (
    <div className={`border border-light-gray rounded-xl overflow-hidden ${className}`}>
      {/* Collapsible Header */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className={`w-full px-4 py-3 flex items-center justify-between transition-colors ${
          isExpanded ? colorClasses.bg : 'bg-off-white hover:bg-gray-100'
        }`}
      >
        <div className="flex items-center gap-2">
          <BookOpen size={16} className={isExpanded ? colorClasses.icon : 'text-medium-gray'} />
          <span className={`text-sm font-medium ${isExpanded ? colorClasses.text : 'text-dark-gray'}`}>
            {isExpanded ? `Diretrizes: ${name}` : `Ver diretrizes da categoria ${name}`}
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp size={18} className={colorClasses.icon} />
        ) : (
          <ChevronDown size={18} className="text-medium-gray" />
        )}
      </button>

      {/* Expandable Content */}
      {isExpanded && (
        <div className="border-t border-light-gray">
          <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-light-gray">
            {/* DOs Column */}
            <div className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <div className="p-1 rounded-full bg-green-100">
                  <CheckCircle size={14} className="text-green-600" />
                </div>
                <h4 className="text-sm font-semibold text-green-700">PODE</h4>
              </div>
              <ul className="space-y-2">
                {dos.map((item, index) => (
                  <li
                    key={`do-${index}`}
                    className="flex items-start gap-2 text-sm text-dark-gray"
                  >
                    <CheckCircle size={14} className="text-green-500 mt-0.5 flex-shrink-0" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* DON'Ts Column */}
            <div className="p-4 bg-red-50/30">
              <div className="flex items-center gap-2 mb-3">
                <div className="p-1 rounded-full bg-red-100">
                  <XCircle size={14} className="text-red-600" />
                </div>
                <h4 className="text-sm font-semibold text-red-700">NAO PODE</h4>
              </div>
              <ul className="space-y-2">
                {donts.map((item, index) => (
                  <li
                    key={`dont-${index}`}
                    className="flex items-start gap-2 text-sm text-dark-gray"
                  >
                    <XCircle size={14} className="text-red-500 mt-0.5 flex-shrink-0" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

CategoryGuidelines.propTypes = {
  categoryId: PropTypes.string.isRequired,
  defaultExpanded: PropTypes.bool,
  className: PropTypes.string
};

export default CategoryGuidelines;
