import PropTypes from 'prop-types';
import { FileText, CheckSquare, Newspaper } from 'lucide-react';

/**
 * ContentStats - Barra de estatisticas do conteudo selecionado
 *
 * Mostra contagem de itens selecionados e palavras estimadas.
 */
const ContentStats = ({
  selectedCount,
  totalCount,
  wordCount,
  sourceCount,
  variant = 'default' // 'default' | 'video' | 'tema' | 'feed' | 'link'
}) => {
  // Gerar texto de acordo com a variante
  const getStatsText = () => {
    switch (variant) {
      case 'video':
        return (
          <>
            <strong className="text-dark-gray">{selectedCount}</strong> de{' '}
            <strong className="text-dark-gray">{totalCount}</strong> trechos selecionados
          </>
        );
      case 'tema':
        return (
          <>
            <strong className="text-dark-gray">{selectedCount}</strong>{' '}
            {selectedCount === 1 ? 'matéria selecionada' : 'matérias selecionadas'}
          </>
        );
      case 'feed':
        return (
          <>
            <strong className="text-dark-gray">{sourceCount}</strong>{' '}
            {sourceCount === 1 ? 'matéria' : 'matérias'}
            <span className="mx-1">•</span>
            <strong className="text-dark-gray">{selectedCount}</strong> de{' '}
            <strong className="text-dark-gray">{totalCount}</strong> tópicos selecionados
          </>
        );
      case 'link':
        return (
          <>
            <strong className="text-dark-gray">{selectedCount}</strong> de{' '}
            <strong className="text-dark-gray">{totalCount}</strong> tópicos selecionados
          </>
        );
      default:
        return (
          <>
            <strong className="text-dark-gray">{selectedCount}</strong> de{' '}
            <strong className="text-dark-gray">{totalCount}</strong> itens selecionados
          </>
        );
    }
  };

  // Icone de acordo com a variante
  const getIcon = () => {
    switch (variant) {
      case 'video':
        return <CheckSquare size={16} className="text-tmc-orange" />;
      case 'tema':
      case 'feed':
        return <Newspaper size={16} className="text-tmc-orange" />;
      default:
        return <FileText size={16} className="text-tmc-orange" />;
    }
  };

  return (
    <div className="border-t border-light-gray px-4 py-3 bg-off-white/50 rounded-b-xl">
      <div className="flex items-center gap-2 text-sm text-medium-gray">
        {getIcon()}
        <span>
          {getStatsText()}
          <span className="mx-2">•</span>
          ~<strong className="text-dark-gray">{wordCount.toLocaleString()}</strong> palavras
        </span>
      </div>
    </div>
  );
};

ContentStats.propTypes = {
  selectedCount: PropTypes.number.isRequired,
  totalCount: PropTypes.number.isRequired,
  wordCount: PropTypes.number.isRequired,
  sourceCount: PropTypes.number,
  variant: PropTypes.oneOf(['default', 'video', 'tema', 'feed', 'link'])
};

export default ContentStats;
