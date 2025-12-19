import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import { CheckSquare, Square, Search, AlertCircle } from 'lucide-react';
import { SourceBadge, ContentStats } from '../../../components/criar';
import {
  TranscriptionCard,
  SelectionSidebar,
  MiniPlayer
} from '../../transcricao/components';

/**
 * TextoBaseTranscricao - Variante da página Texto-Base para Transcrição de Vídeo
 *
 * Experiência COMPLETA com:
 * - Player de vídeo embed do YouTube
 * - TranscriptionCards expandíveis com seleção de texto
 * - SelectionSidebar para gerenciar seleções
 * - MiniPlayer quando player principal sai de vista
 * - Busca na transcrição
 */

const TextoBaseTranscricao = ({
  fonte,
  onChangeSource,
  onDataChange
}) => {
  // Extrair dados da fonte
  const video = fonte?.dados?.video || null;
  const transcription = fonte?.dados?.transcription || [];

  // States
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [cardHighlights, setCardHighlights] = useState({});
  const [unifiedSelections, setUnifiedSelections] = useState([]);

  // Refs e estados para MiniPlayer
  const mainPlayerRef = useRef(null);
  const [isMainPlayerVisible, setIsMainPlayerVisible] = useState(true);
  const [currentVideoTime, setCurrentVideoTime] = useState(0);

  // Inicializar seleção com todos os trechos
  useEffect(() => {
    if (transcription.length > 0 && selectedIds.size === 0) {
      setSelectedIds(new Set(transcription.map(t => t.id)));
    }
  }, [transcription, selectedIds.size]);

  // Filtrar transcrição por busca
  const filteredTranscription = useMemo(() => {
    return transcription.filter(segment =>
      segment.text.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [transcription, searchQuery]);

  // Sincronizar seleções unificadas
  useEffect(() => {
    const selections = [];

    // Cards inteiros selecionados
    selectedIds.forEach(id => {
      const segment = transcription.find(s => s.id === id);
      if (segment) {
        selections.push({
          id: `card-${id}`,
          text: segment.text,
          source: 'cards',
          topic: segment.topic,
          timestamp: segment.startTime
        });
      }
    });

    // Highlights de texto dentro dos cards
    Object.entries(cardHighlights).forEach(([segmentId, highlights]) => {
      const segment = transcription.find(s => s.id === segmentId);
      if (segment && highlights.length > 0) {
        highlights.forEach((text, index) => {
          selections.push({
            id: `text-${segmentId}-${index}`,
            text: text,
            source: 'full',
            topic: segment.topic,
            timestamp: segment.startTime
          });
        });
      }
    });

    setUnifiedSelections(selections);
  }, [selectedIds, cardHighlights, transcription]);

  // Observer para detectar visibilidade do player principal
  useEffect(() => {
    if (!mainPlayerRef.current) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsMainPlayerVisible(entry.isIntersecting);
      },
      { threshold: 0.3 }
    );

    observer.observe(mainPlayerRef.current);

    return () => observer.disconnect();
  }, []);

  // Notificar mudanças
  useEffect(() => {
    if (onDataChange) {
      const wordCount = unifiedSelections.reduce((acc, sel) => {
        return acc + sel.text.split(/\s+/).filter(Boolean).length;
      }, 0);

      onDataChange({
        selectedTrechos: Array.from(selectedIds),
        textHighlights: cardHighlights,
        unifiedSelections,
        wordCount
      });
    }
  }, [selectedIds, cardHighlights, unifiedSelections, onDataChange]);

  // Handlers de seleção
  const handleToggle = useCallback((id) => {
    setSelectedIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    setSelectedIds(new Set(transcription.map(s => s.id)));
  }, [transcription]);

  const handleDeselectAll = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const isSelected = useCallback((id) => {
    return selectedIds.has(id);
  }, [selectedIds]);

  // Handler para seleção de texto dentro dos cards
  const handleTextSelect = useCallback((segmentId, selectedText, isRemove = false) => {
    setCardHighlights(prev => {
      const current = prev[segmentId] || [];

      if (isRemove) {
        const filtered = current.filter(h => h !== selectedText);
        if (filtered.length === 0) {
          const { [segmentId]: _, ...rest } = prev;
          return rest;
        }
        return { ...prev, [segmentId]: filtered };
      } else {
        if (current.includes(selectedText)) return prev;
        return { ...prev, [segmentId]: [...current, selectedText] };
      }
    });
  }, []);

  // Play segment (mock)
  const handlePlaySegment = useCallback((segmentId, isPlaying) => {
    console.log('Play segment:', segmentId, isPlaying);
  }, []);

  // Go to moment - pula para timestamp no vídeo
  const handleGoToMoment = useCallback((seconds) => {
    let timeInSeconds = seconds;
    if (typeof seconds === 'string') {
      const parts = seconds.split(':').map(p => parseInt(p, 10));
      if (parts.length === 2) {
        timeInSeconds = parts[0] * 60 + parts[1];
      } else if (parts.length === 3) {
        timeInSeconds = parts[0] * 3600 + parts[1] * 60 + parts[2];
      }
    }

    setCurrentVideoTime(timeInSeconds);

    if (mainPlayerRef.current && !isMainPlayerVisible) {
      mainPlayerRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [isMainPlayerVisible]);

  // Handlers para SelectionSidebar
  const handleRemoveSelection = useCallback((selectionId) => {
    if (selectionId.startsWith('card-')) {
      const cardId = selectionId.replace('card-', '');
      handleToggle(cardId);
    } else if (selectionId.startsWith('text-')) {
      const parts = selectionId.split('-');
      const segmentId = parts[1];
      const selection = unifiedSelections.find(s => s.id === selectionId);
      if (selection) {
        handleTextSelect(segmentId, selection.text, true);
      }
    }
  }, [unifiedSelections, handleTextSelect, handleToggle]);

  const handleReorderSelections = useCallback((fromIndex, toIndex) => {
    setUnifiedSelections(prev => {
      const newSelections = [...prev];
      const [moved] = newSelections.splice(fromIndex, 1);
      newSelections.splice(toIndex, 0, moved);
      return newSelections;
    });
  }, []);

  const handleClearAllSelections = useCallback(() => {
    setSelectedIds(new Set());
    setCardHighlights({});
  }, []);

  // Estatísticas
  const stats = useMemo(() => {
    const wordCount = unifiedSelections.reduce((acc, sel) => {
      return acc + sel.text.split(/\s+/).filter(Boolean).length;
    }, 0);

    return {
      selected: unifiedSelections.length,
      total: transcription.length,
      words: wordCount
    };
  }, [unifiedSelections, transcription]);

  // Estado vazio - sem transcrição
  if (transcription.length === 0) {
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-xl border border-light-gray p-8 text-center">
          <div className="w-16 h-16 bg-off-white rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle size={32} className="text-medium-gray" />
          </div>
          <h3 className="font-semibold text-dark-gray mb-2">
            Nenhuma transcrição disponível
          </h3>
          <p className="text-sm text-medium-gray mb-4">
            Volte para a tela de Transcrição para transcrever o vídeo.
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
        subtitle={video?.channel}
        onChangeSource={onChangeSource}
      />

      {/* Layout principal */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Coluna esquerda: Vídeo + Transcrição */}
        <div className="w-full lg:w-3/5">
          {/* Player embed */}
          {video && (
            <div
              ref={mainPlayerRef}
              className="bg-black rounded-xl overflow-hidden mb-4 aspect-video"
            >
              <iframe
                src={`https://www.youtube.com/embed/${video.videoId}${currentVideoTime > 0 ? `?start=${Math.floor(currentVideoTime)}` : ''}`}
                title={video.title}
                className="w-full h-full"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </div>
          )}

          {/* Toolbar de seleção */}
          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleSelectAll}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-medium-gray hover:text-dark-gray hover:bg-off-white rounded-lg transition-colors"
              >
                <CheckSquare className="w-4 h-4" />
                <span className="hidden sm:inline">Selecionar Tudo</span>
              </button>
              <button
                type="button"
                onClick={handleDeselectAll}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-medium-gray hover:text-dark-gray hover:bg-off-white rounded-lg transition-colors"
              >
                <Square className="w-4 h-4" />
                <span className="hidden sm:inline">Limpar</span>
              </button>
            </div>

            {/* Busca na transcrição */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-medium-gray" />
              <input
                type="text"
                placeholder="Buscar na transcrição..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-4 py-1.5 text-sm border border-light-gray rounded-lg focus:ring-2 focus:ring-tmc-orange focus:border-tmc-orange"
              />
            </div>
          </div>

          {/* Cards de transcrição */}
          <div className="space-y-3">
            {filteredTranscription.map(segment => (
              <TranscriptionCard
                key={segment.id}
                segment={segment}
                isSelected={isSelected(segment.id)}
                onToggle={handleToggle}
                onPlaySegment={handlePlaySegment}
                onGoToMoment={handleGoToMoment}
                onTextSelect={handleTextSelect}
                textHighlights={cardHighlights[segment.id] || []}
              />
            ))}

            {filteredTranscription.length === 0 && searchQuery && (
              <div className="text-center py-8 text-medium-gray">
                <p>Nenhum trecho encontrado para &ldquo;{searchQuery}&rdquo;</p>
              </div>
            )}
          </div>

          {/* Stats */}
          <div className="mt-4">
            <ContentStats
              selectedCount={stats.selected}
              totalCount={stats.total}
              wordCount={stats.words}
              sourceCount={1}
              variant="transcription"
            />
          </div>
        </div>

        {/* Coluna direita: Seleções */}
        <div className="w-full lg:w-2/5">
          <div className="sticky top-24">
            <SelectionSidebar
              selections={unifiedSelections}
              onRemove={handleRemoveSelection}
              onReorder={handleReorderSelections}
              onClear={handleClearAllSelections}
            />
          </div>
        </div>
      </div>

      {/* MiniPlayer - aparece quando o player principal sai de vista */}
      {video && (
        <MiniPlayer
          videoId={video.videoId}
          isMainPlayerVisible={isMainPlayerVisible}
          currentTime={currentVideoTime}
          onTimeUpdate={setCurrentVideoTime}
          position="bottom-right"
        />
      )}
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
        text: PropTypes.string
      }))
    })
  }),
  onChangeSource: PropTypes.func,
  onDataChange: PropTypes.func
};

export default TextoBaseTranscricao;
