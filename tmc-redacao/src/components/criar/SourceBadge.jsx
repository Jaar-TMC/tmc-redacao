import PropTypes from 'prop-types';
import { Video, Flame, Newspaper, Globe, RefreshCw, Youtube } from 'lucide-react';

/**
 * SourceBadge - Badge indicando a fonte selecionada
 *
 * Exibe informacoes sobre a fonte selecionada com opcao de trocar.
 */
const SourceBadge = ({
  type,
  title,
  subtitle,
  onChangeSource
}) => {
  // Mapear tipo para icone e cor
  const sourceConfig = {
    video: {
      icon: <Video size={20} />,
      label: 'Transcrição de Vídeo',
      color: 'text-red-500 bg-red-50'
    },
    transcription: {
      icon: <Youtube size={20} />,
      label: 'Transcrição de Vídeo',
      color: 'text-red-500 bg-red-50'
    },
    tema: {
      icon: <Flame size={20} />,
      label: 'Tema em Alta',
      color: 'text-orange-500 bg-orange-50'
    },
    feed: {
      icon: <Newspaper size={20} />,
      label: 'Matérias do Feed',
      color: 'text-blue-500 bg-blue-50'
    },
    link: {
      icon: <Globe size={20} />,
      label: 'Link da Web',
      color: 'text-green-500 bg-green-50'
    }
  };

  const config = sourceConfig[type] || sourceConfig.link;

  return (
    <div className="bg-white border border-light-gray rounded-xl p-4 mb-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${config.color}`}>
            {config.icon}
          </div>
          <div>
            <p className="text-xs text-medium-gray uppercase tracking-wide font-medium">
              {config.label}
            </p>
            <p className="text-dark-gray font-semibold">
              {title}
              {subtitle && (
                <span className="text-medium-gray font-normal ml-2">
                  ({subtitle})
                </span>
              )}
            </p>
          </div>
        </div>
        {onChangeSource && (
          <button
            onClick={onChangeSource}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-medium-gray hover:text-tmc-orange border border-light-gray rounded-lg hover:border-tmc-orange/50 transition-colors"
          >
            <RefreshCw size={14} />
            Trocar
          </button>
        )}
      </div>
    </div>
  );
};

SourceBadge.propTypes = {
  type: PropTypes.oneOf(['video', 'tema', 'feed', 'link', 'transcription']).isRequired,
  title: PropTypes.string.isRequired,
  subtitle: PropTypes.string,
  onChangeSource: PropTypes.func
};

export default SourceBadge;
