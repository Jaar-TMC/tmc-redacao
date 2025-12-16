import { useState, useCallback } from 'react';
import PropTypes from 'prop-types';
import {
  FileText,
  Clock,
  Hash,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Tv,
  Loader2,
  X
} from 'lucide-react';

/**
 * ConfigPanel - Painel de configuração para geração da matéria
 * @param {Object} props
 * @param {Object} props.config - Configurações atuais
 * @param {Function} props.onChange - Callback ao mudar configuração
 * @param {Object} props.selection - Estado da seleção
 * @param {Object} props.video - Dados do vídeo
 * @param {Function} props.onGenerate - Callback ao gerar matéria
 * @param {boolean} props.isGenerating - Se está gerando
 */
function ConfigPanel({
  config,
  onChange,
  selection,
  video,
  onGenerate,
  isGenerating
}) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleChange = useCallback((key, value) => {
    onChange({ ...config, [key]: value });
  }, [config, onChange]);

  const toneOptions = [
    { value: 'journalistic', label: 'Jornalístico', description: 'Tom neutro e informativo' },
    { value: 'informal', label: 'Informal', description: 'Linguagem mais descontraída' },
    { value: 'technical', label: 'Técnico', description: 'Vocabulário especializado' },
    { value: 'persuasive', label: 'Persuasivo', description: 'Tom de convencimento' }
  ];

  const personaOptions = [
    { value: 'impartial_journalist', label: 'Jornalista Imparcial', description: 'Abordagem neutra e factual' },
    { value: 'specialist', label: 'Especialista', description: 'Autoridade técnica no tema' },
    { value: 'columnist', label: 'Colunista', description: 'Visão pessoal e analítica' },
    { value: 'influencer', label: 'Influencer', description: 'Comunicação próxima e engajadora' }
  ];

  // Estimar palavras baseado na seleção
  const estimatedWords = selection.selectedCount * 150;
  const estimatedMinutes = Math.ceil(estimatedWords / 200);

  return (
    <div className="bg-white rounded-xl border border-light-gray p-6 sticky top-24">
      {/* Resumo da Seleção */}
      <div className="bg-off-white rounded-xl p-4 mb-5">
        <h3 className="text-sm font-semibold text-dark-gray mb-3">
          Resumo da Seleção
        </h3>
        <div className="space-y-2.5 text-sm">
          <div className="flex items-center gap-2.5 text-medium-gray">
            <FileText className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
            <span>
              <strong className="text-dark-gray font-semibold">{selection.selectedCount}</strong> trechos selecionados
            </span>
          </div>
          <div className="flex items-center gap-2.5 text-medium-gray">
            <Clock className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
            <span>
              ~<strong className="text-dark-gray font-semibold">{estimatedMinutes}</strong> min de conteúdo
            </span>
          </div>
          <div className="flex items-center gap-2.5 text-medium-gray">
            <Hash className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
            <span>
              ~<strong className="text-dark-gray font-semibold">{estimatedWords}</strong> palavras estimadas
            </span>
          </div>
        </div>
      </div>

      {/* Tom da Matéria */}
      <div className="mb-5">
        <label className="block text-sm font-semibold text-dark-gray mb-2">
          Tom da Matéria
        </label>
        <p className="text-xs text-medium-gray mb-2">Escolha o estilo de escrita do conteúdo</p>
        <div className="space-y-2">
          {toneOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => handleChange('tone', option.value)}
              className={`w-full p-3 rounded-lg border-2 text-left transition-all ${
                config.tone === option.value
                  ? 'border-tmc-orange bg-tmc-orange/5'
                  : 'border-light-gray hover:border-tmc-orange/50'
              }`}
            >
              <p className="font-medium text-dark-gray">{option.label}</p>
              <p className="text-xs text-medium-gray">{option.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Persona do Redator */}
      <div className="mb-5">
        <label className="block text-sm font-semibold text-dark-gray mb-2">
          Persona do Redator
        </label>
        <p className="text-xs text-medium-gray mb-2">Defina quem será a voz do texto</p>
        <div className="space-y-2">
          {personaOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => handleChange('persona', option.value)}
              className={`w-full p-3 rounded-lg border-2 text-left transition-all ${
                config.persona === option.value
                  ? 'border-tmc-dark-green bg-tmc-dark-green/5'
                  : 'border-light-gray hover:border-tmc-dark-green/50'
              }`}
            >
              <p className="font-medium text-dark-gray">{option.label}</p>
              <p className="text-xs text-medium-gray">{option.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Configurações Avançadas */}
      <div className="mb-5">
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center justify-between w-full py-2 text-sm font-medium text-medium-gray hover:text-dark-gray transition-colors"
          aria-expanded={showAdvanced}
        >
          <span>Configurações Avançadas</span>
          {showAdvanced ? (
            <ChevronUp className="w-4 h-4" aria-hidden="true" />
          ) : (
            <ChevronDown className="w-4 h-4" aria-hidden="true" />
          )}
        </button>

        {showAdvanced && (
          <div className="mt-3 pt-3 border-t border-light-gray space-y-4">
            {/* Criatividade */}
            <div>
              <label className="block text-xs font-semibold text-dark-gray mb-2">
                Criatividade
              </label>
              <div className="flex items-center gap-3">
                <span className="text-xs text-medium-gray">Factual</span>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={config.creativity || 30}
                  onChange={(e) => handleChange('creativity', parseInt(e.target.value))}
                  className="flex-1 h-2 bg-light-gray rounded-lg appearance-none cursor-pointer accent-tmc-orange"
                />
                <span className="text-xs text-medium-gray">Criativo</span>
              </div>
            </div>

            {/* Checkboxes */}
            <label className="flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-all hover:bg-off-white">
              <input
                type="checkbox"
                checked={config.includeQuotes || false}
                onChange={(e) => handleChange('includeQuotes', e.target.checked)}
                className="w-4 h-4 text-tmc-orange rounded focus:ring-tmc-orange focus:ring-2"
              />
              <span className="text-sm text-dark-gray">Incluir citações diretas</span>
            </label>

            <label className="flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-all hover:bg-off-white">
              <input
                type="checkbox"
                checked={config.citeSource || true}
                onChange={(e) => handleChange('citeSource', e.target.checked)}
                className="w-4 h-4 text-tmc-orange rounded focus:ring-tmc-orange focus:ring-2"
              />
              <span className="text-sm text-dark-gray">Citar fonte (vídeo)</span>
            </label>

            <label className="flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-all hover:bg-off-white">
              <input
                type="checkbox"
                checked={config.addIntroConclusion || false}
                onChange={(e) => handleChange('addIntroConclusion', e.target.checked)}
                className="w-4 h-4 text-tmc-orange rounded focus:ring-tmc-orange focus:ring-2"
              />
              <span className="text-sm text-dark-gray">Adicionar intro/conclusão</span>
            </label>

            {/* Keywords SEO */}
            <div>
              <label className="block text-xs font-semibold text-dark-gray mb-2">
                Keywords SEO
              </label>
              <div className="flex flex-wrap gap-2 mb-2">
                {(config.keywords || []).map((keyword, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center gap-1 px-2.5 py-1 bg-tmc-orange/10 text-tmc-orange text-xs rounded-full font-medium"
                  >
                    {keyword}
                    <button
                      type="button"
                      onClick={() => {
                        const newKeywords = config.keywords.filter((_, i) => i !== index);
                        handleChange('keywords', newKeywords);
                      }}
                      className="hover:bg-tmc-orange/20 rounded-full p-0.5 transition-colors"
                      aria-label={`Remover keyword ${keyword}`}
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
              <input
                type="text"
                placeholder="Digite e pressione Enter"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && e.target.value.trim()) {
                    e.preventDefault();
                    const newKeywords = [...(config.keywords || []), e.target.value.trim()];
                    handleChange('keywords', newKeywords);
                    e.target.value = '';
                  }
                }}
                className="w-full px-3 py-2.5 border border-light-gray rounded-lg text-sm focus:ring-2 focus:ring-tmc-orange focus:border-tmc-orange transition-all"
              />
            </div>
          </div>
        )}
      </div>

      {/* Fonte do Vídeo */}
      {video && (
        <div className="bg-off-white rounded-xl p-4 mb-5">
          <h3 className="text-sm font-semibold text-dark-gray mb-3">
            Fonte do Vídeo
          </h3>
          <p className="text-sm text-dark-gray font-medium line-clamp-2 mb-3">
            {video.title}
          </p>
          <div className="flex items-center gap-2 text-xs text-medium-gray mb-3">
            <Tv className="w-3.5 h-3.5 flex-shrink-0" aria-hidden="true" />
            <span>{video.channel}</span>
          </div>
          <a
            href={video.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-tmc-orange hover:underline font-medium transition-colors"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
            Abrir no YouTube
          </a>
        </div>
      )}

      {/* Botão Gerar */}
      <button
        type="button"
        onClick={onGenerate}
        disabled={!selection.hasSelection || isGenerating}
        className={`
          w-full py-3 px-4 rounded-lg font-semibold text-white
          flex items-center justify-center gap-2
          transition-colors
          ${selection.hasSelection && !isGenerating
            ? 'bg-tmc-orange hover:bg-tmc-orange/90'
            : 'bg-light-gray text-medium-gray cursor-not-allowed'
          }
        `}
      >
        {isGenerating ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" aria-hidden="true" />
            <span>Gerando...</span>
          </>
        ) : (
          <span>Gerar Matéria</span>
        )}
      </button>

      {!selection.hasSelection && (
        <p className="text-xs text-medium-gray text-center mt-3">
          Selecione pelo menos um trecho para gerar
        </p>
      )}
    </div>
  );
}

ConfigPanel.propTypes = {
  config: PropTypes.shape({
    tone: PropTypes.string,
    persona: PropTypes.string,
    creativity: PropTypes.number,
    includeQuotes: PropTypes.bool,
    citeSource: PropTypes.bool,
    addIntroConclusion: PropTypes.bool,
    keywords: PropTypes.arrayOf(PropTypes.string)
  }).isRequired,
  onChange: PropTypes.func.isRequired,
  selection: PropTypes.shape({
    selectedCount: PropTypes.number.isRequired,
    hasSelection: PropTypes.bool.isRequired
  }).isRequired,
  video: PropTypes.shape({
    title: PropTypes.string,
    channel: PropTypes.string,
    url: PropTypes.string
  }),
  onGenerate: PropTypes.func.isRequired,
  isGenerating: PropTypes.bool
};

export default ConfigPanel;
