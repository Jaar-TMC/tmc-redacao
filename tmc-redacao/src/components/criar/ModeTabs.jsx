import PropTypes from 'prop-types';
import { List, FileText } from 'lucide-react';

/**
 * ModeTabs - Tabs para alternar entre modos de visualizacao
 */
const ModeTabs = ({
  activeTab,
  onTabChange,
  tabs = [
    { id: 'topics', label: 'Tópicos', icon: <List size={16} /> },
    { id: 'fulltext', label: 'Texto Completo', icon: <FileText size={16} /> }
  ],
  className = ''
}) => {
  return (
    <div className={`flex gap-2 ${className}`}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`
            flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors
            ${activeTab === tab.id
              ? 'bg-tmc-orange text-white'
              : 'text-medium-gray hover:bg-off-white'
            }
          `}
        >
          {tab.icon}
          {tab.label}
        </button>
      ))}
    </div>
  );
};

ModeTabs.propTypes = {
  activeTab: PropTypes.string.isRequired,
  onTabChange: PropTypes.func.isRequired,
  tabs: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string.isRequired,
    label: PropTypes.string.isRequired,
    icon: PropTypes.node
  })),
  className: PropTypes.string
};

export default ModeTabs;
