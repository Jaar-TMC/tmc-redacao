/**
 * CategoryGuidelines - DOs/DON'Ts display panel
 *
 * Shows category-specific editorial guidelines with visual
 * distinction between allowed and prohibited practices.
 */

import PropTypes from 'prop-types';
import { CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import { CATEGORIAS_EDITORIAIS } from '../../constants/editorial';

const CategoryGuidelines = ({
  categoryId,
  compact = false,
  className = ''
}) => {
  const categoria = CATEGORIAS_EDITORIAIS[categoryId];

  if (!categoria) {
    return null;
  }

  const { dos, donts, colorClasses, name, reference } = categoria;

  if (compact) {
    // Compact mode: show in a single row or collapsible
    return (
      <div className={`bg-off-white rounded-lg p-3 ${className}`}>
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle size={14} className="text-amber-500" />
          <span className="text-xs font-medium text-dark-gray">
            Diretrizes: {name}
          </span>
          <span className="text-xs text-medium-gray">
            (Ref: {reference})
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          {dos.slice(0, 3).map((item, i) => (
            <span
              key={`do-${i}`}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-green-50 text-green-700"
            >
              <CheckCircle size={10} />
              {item.length > 30 ? item.substring(0, 30) + '...' : item}
            </span>
          ))}
          {donts.slice(0, 2).map((item, i) => (
            <span
              key={`dont-${i}`}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-red-50 text-red-700"
            >
              <XCircle size={10} />
              {item.length > 25 ? item.substring(0, 25) + '...' : item}
            </span>
          ))}
        </div>
      </div>
    );
  }

  // Full mode: two columns with all guidelines
  return (
    <div className={`border border-light-gray rounded-xl overflow-hidden ${className}`}>
      {/* Header */}
      <div className={`px-4 py-3 ${colorClasses.bg} border-b border-light-gray`}>
        <div className="flex items-center justify-between">
          <h3 className={`font-semibold ${colorClasses.text}`}>
            Diretrizes: {name}
          </h3>
          <span className="text-xs text-medium-gray">
            Referencia: {reference}
          </span>
        </div>
      </div>

      {/* Content */}
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
  );
};

CategoryGuidelines.propTypes = {
  categoryId: PropTypes.string.isRequired,
  compact: PropTypes.bool,
  className: PropTypes.string
};

export default CategoryGuidelines;
