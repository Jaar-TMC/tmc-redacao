import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import { ExternalLink, Clock, AlertCircle, Youtube, Play, Pause } from 'lucide-react';
import {
  SourceBadge,
  ContentStats,
  SelectionToggleBar,
  TopicCard
} from '../../../components/criar';

/**
 * TextoBaseTranscricao - Variante da página Texto-Base para Transcrição de Vídeo
 *
 * Experiência completa com:
 * - Player de vídeo embed do YouTube
 * - Timeline com trechos da transcrição
 * - Seleção/edição de trechos
 * - Navegação por timestamp
 */

// Formatar timestamp para exibição
const formatTimestamp = (timestamp) => {
  if (!timestamp) return '00:00';
  if (typeof timestamp === 'string') return timestamp;

  const minutes = Math.floor(timestamp / 60);
  const seconds = Math.floor(timestamp % 60);
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
};

// Converter timestamp string para segundos
const timestampToSeconds = (timestamp) => {
  if (typeof timestamp === 'number') return timestamp;
  if (!timestamp) return 0;

  const parts = timestamp.split(':').map(p => parseInt(p, 10));
  if (parts.length === 2) {
    return parts[0] * 60 + parts[1];
  } else if (parts.length === 3) {
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
  }
  return 0;
};

const TextoBaseTranscricao = ({
  fonte,
  onChangeSource,
  onDataChange
}) => {
  // Extrair dados da fonte
  const video = fonte?.dados?.video || null;
  const transcription = fonte?.dados?.transcription || [];

  const trechos = useMemo(() => {
    // Usar transcription se disponível, senão usar selections
    const segments = transcription.length > 0
      ? transcription
      : (fonte?.dados?.selections || []);

    return segments.map((seg, index) => ({
      id: seg.id || `trecho-${index}`,
      text: seg.text,
      topic: seg.topic || 'Trecho',
      startTime: seg.startTime || seg.timestamp || '00:00',
      endTime: seg.endTime || null,
      source: seg.source || 'cards'
    }));
  }, [transcription, fonte?.dados?.selections]);

  // States
  const [selectedTrechos, setSelectedTrechos] = useState(new Set());
  const [editedTexts, setEditedTexts] = useState({});
  const [currentVideoTime, setCurrentVideoTime] = useState(0);
  const [activeTrecho, setActiveTrecho] = useState(null);

  // Ref para o player
  const playerRef = useRef(null);

  // Inicializar seleção com todos os trechos
  useEffect(() => {
    if (trechos.length > 0 && selectedTrechos.size === 0) {
      setSelectedTrechos(new Set(trechos.map(t => t.id)));
    }
  }, [trechos, selectedTrechos.size]);

  // Estatísticas
  const stats = useMemo(() => {
    let wordCount = 0;

    trechos.forEach(trecho => {
      if (selectedTrechos.has(trecho.id)) {
        const text = editedTexts[trecho.id] || trecho.text;
        wordCount += text.split(/\s+/).filter(Boolean).length;
      }
    });

    return {
      selected: selectedTrechos.size,
      total: trechos.length,
      words: wordCount,
      sources: 1 // Sempre 1 vídeo
    };
  }, [trechos, selectedTrechos, editedTexts]);

  // Handlers
  const handleToggleTrecho = useCallback((trechoId) => {
    setSelectedTrechos(prev => {
      const newSet = new Set(prev);
      if (newSet.has(trechoId)) {
        newSet.delete(trechoId);
      } else {
        newSet.add(trechoId);
      }
      return newSet;
    });
  }, []);

  const handleEditTrecho = useCallback((trechoId, newText) => {
    setEditedTexts(prev => ({
      ...prev,
      [trechoId]: newText
    }));
  }, []);

  const handleSelectAll = useCallback(() => {
    setSelectedTrechos(new Set(trechos.map(t => t.id)));
  }, [trechos]);

  const handleClearSelection = useCallback(() => {
    setSelectedTrechos(new Set());
  }, []);

  // Ir para timestamp no vídeo
  const handleGoToTimestamp = useCallback((timestamp) => {
    const seconds = timestampToSeconds(timestamp);
    setCurrentVideoTime(seconds);

    // Scroll suave para o player se não estiver visível
    if (playerRef.current) {
      playerRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, []);

  // Notificar mudanças
  useEffect(() => {
    if (onDataChange) {
      onDataChange({
        selectedTrechos: Array.from(selectedTrechos),
        editedTexts,
        wordCount: stats.words
      });
    }
  }, [selectedTrechos, editedTexts, stats.words, onDataChange]);

  // Estado vazio - sem trechos
  if (trechos.length === 0) {
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-xl border border-light-gray p-8 text-center">
          <div className="w-16 h-16 bg-off-white rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle size={32} className="text-medium-gray" />
          </div>
          <h3 className="font-semibold text-dark-gray mb-2">
            Nenhum trecho disponível
          </h3>
          <p className="text-sm text-medium-gray mb-4">
            Volte para a tela de Transcrição para transcrever o vídeo novamente.
          </p>
          <button
            onClick={onChangeSource}
            className="px-4 py-2 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors font-medium"
          >
            Voltar para Transcrição
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SourceBadge
        type="transcription"
        title={video?.title || 'Vídeo do YouTube'}
        subtitle={`${trechos.length} trechos`}
        onChangeSource={onChangeSource}
      />

      {/* Layout principal */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Coluna esquerda - Player de vídeo */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl border border-light-gray overflow-hidden sticky top-24">
            {/* Player embed do YouTube */}
            {video && (
              <div ref={playerRef} className="aspect-video bg-black">
                <iframe
                  src={`https://www.youtube.com/embed/${video.videoId}?start=${Math.floor(currentVideoTime)}&enablejsapi=1`}
                  title={video.title}
                  className="w-full h-full"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              </div>
            )}

            {/* Info do vídeo */}
            <div className="p-4">
              <div className="flex items-start gap-2 mb-3">
                <Youtube size={18} className="text-red-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-dark-gray text-sm line-clamp-2">
                    {video?.title || 'Vídeo do YouTube'}
                  </h3>
                  {video?.channel && (
                    <p className="text-xs text-medium-gray mt-1">{video.channel}</p>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between">
                {video?.duration && (
                  <div className="flex items-center gap-1.5 text-xs text-medium-gray">
                    <Clock size={12} />
                    <span>{video.duration}</span>
                  </div>
                )}

                <a
                  href={`https://youtube.com/watch?v=${video?.videoId}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-xs text-tmc-orange hover:underline"
                >
                  <ExternalLink size={12} />
                  Abrir no YouTube
                </a>
              </div>
            </div>

            {/* Dica de uso */}
            <div className="p-4 border-t border-light-gray bg-off-white/50">
              <p className="text-xs text-medium-gray">
                <strong>Dica:</strong> Clique no timestamp de um trecho para pular para aquele momento no vídeo.
              </p>
            </div>
          </div>
        </div>

        {/* Coluna direita - Timeline de trechos */}
        <div className="lg:col-span-3">
          <div className="bg-white rounded-xl border border-light-gray overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-light-gray">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-dark-gray">
                    Timeline da Transcrição
                  </h3>
                  <p className="text-sm text-medium-gray">
                    Selecione os trechos que serão usados na matéria
                  </p>
                </div>
              </div>
            </div>

            {/* Controles de seleção */}
            <div className="p-4 border-b border-light-gray">
              <SelectionToggleBar
                selectedCount={stats.selected}
                totalCount={stats.total}
                onSelectAll={handleSelectAll}
                onClearSelection={handleClearSelection}
              />
            </div>

            {/* Lista de trechos com timeline */}
            <div className="divide-y divide-light-gray max-h-[600px] overflow-y-auto">
              {trechos.map((trecho, index) => (
                <div
                  key={trecho.id}
                  className={`p-4 transition-colors ${
                    activeTrecho === trecho.id ? 'bg-tmc-orange/5' : 'hover:bg-off-white/50'
                  }`}
                  onMouseEnter={() => setActiveTrecho(trecho.id)}
                  onMouseLeave={() => setActiveTrecho(null)}
                >
                  {/* Header do trecho com timestamp */}
                  <div className="flex items-center gap-3 mb-2">
                    {/* Checkbox de seleção */}
                    <button
                      type="button"
                      onClick={() => handleToggleTrecho(trecho.id)}
                      className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                        selectedTrechos.has(trecho.id)
                          ? 'bg-tmc-orange border-tmc-orange text-white'
                          : 'border-light-gray hover:border-tmc-orange'
                      }`}
                    >
                      {selectedTrechos.has(trecho.id) && (
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </button>

                    {/* Timestamp clicável */}
                    <button
                      type="button"
                      onClick={() => handleGoToTimestamp(trecho.startTime)}
                      className="flex items-center gap-1.5 px-2 py-1 bg-dark-gray text-white text-xs font-mono rounded hover:bg-tmc-orange transition-colors"
                    >
                      <Play size={10} fill="currentColor" />
                      {formatTimestamp(trecho.startTime)}
                    </button>

                    {trecho.endTime && (
                      <>
                        <span className="text-medium-gray text-xs">→</span>
                        <span className="text-xs text-medium-gray font-mono">
                          {formatTimestamp(trecho.endTime)}
                        </span>
                      </>
                    )}

                    {/* Tópico/Label */}
                    <span className="px-2 py-0.5 bg-off-white text-medium-gray text-xs rounded-full">
                      {trecho.topic}
                    </span>
                  </div>

                  {/* Texto do trecho */}
                  <div className="ml-8">
                    <p className={`text-sm leading-relaxed ${
                      selectedTrechos.has(trecho.id) ? 'text-dark-gray' : 'text-medium-gray'
                    }`}>
                      {editedTexts[trecho.id] || trecho.text}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {/* Footer com stats */}
            <ContentStats
              selectedCount={stats.selected}
              totalCount={stats.total}
              wordCount={stats.words}
              sourceCount={stats.sources}
              variant="transcription"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

TextoBaseTranscricao.propTypes = {
  fonte: PropTypes.shape({
    tipo: PropTypes.string,
    dados: PropTypes.shape({
      video: PropTypes.shape({
        videoId: PropTypes.string,
        title: PropTypes.string,
        thumbnail: PropTypes.string,
        channel: PropTypes.string,
        duration: PropTypes.string
      }),
      transcription: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.string,
        text: PropTypes.string,
        topic: PropTypes.string,
        startTime: PropTypes.string,
        endTime: PropTypes.string
      })),
      selections: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.string,
        text: PropTypes.string,
        topic: PropTypes.string,
        timestamp: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
        source: PropTypes.string
      }))
    })
  }),
  onChangeSource: PropTypes.func,
  onDataChange: PropTypes.func
};

export default TextoBaseTranscricao;
