import { useState } from 'react';
import SelectionSidebar from './SelectionSidebar';

/**
 * Exemplo de uso do SelectionSidebar
 *
 * Este arquivo demonstra como integrar o SelectionSidebar
 * na página de transcrição
 */

function SelectionSidebarExample() {
  // Estado das seleções
  const [selections, setSelections] = useState([
    {
      id: '1',
      text: 'Olá, sejam bem-vindos ao nosso canal. Hoje vamos falar sobre um tema muito importante que tem chamado a atenção de todos.',
      source: 'cards'
    },
    {
      id: '2',
      text: 'Nos últimos meses, observamos uma mudança significativa no comportamento do mercado.',
      source: 'cards'
    },
    {
      id: '3',
      text: 'Especialistas apontam que essa tendência deve continuar pelos próximos anos.',
      source: 'full'
    }
  ]);

  // Handler para remover item
  const handleRemove = (id) => {
    setSelections(prev => prev.filter(sel => sel.id !== id));
  };

  // Handler para reordenar itens
  const handleReorder = (fromIndex, toIndex) => {
    setSelections(prev => {
      const newSelections = [...prev];
      const [removed] = newSelections.splice(fromIndex, 1);
      newSelections.splice(toIndex, 0, removed);
      return newSelections;
    });
  };

  // Handler para limpar todas seleções
  const handleClear = () => {
    setSelections([]);
  };

  return (
    <div className="p-8 bg-off-white min-h-screen">
      <div className="max-w-md mx-auto">
        <h1 className="text-2xl font-bold text-dark-gray mb-6">
          SelectionSidebar - Exemplo
        </h1>

        <SelectionSidebar
          selections={selections}
          onRemove={handleRemove}
          onReorder={handleReorder}
          onClear={handleClear}
        />

        {/* Botões de teste */}
        <div className="mt-6 space-y-3">
          <button
            type="button"
            onClick={() => setSelections(prev => [...prev, {
              id: String(Date.now()),
              text: 'Nova seleção de exemplo adicionada ao final da lista.',
              source: 'cards'
            }])}
            className="w-full py-2 px-4 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors"
          >
            Adicionar Seleção
          </button>

          <button
            type="button"
            onClick={handleClear}
            className="w-full py-2 px-4 border border-light-gray text-dark-gray rounded-lg hover:bg-off-white transition-colors"
          >
            Limpar Tudo
          </button>
        </div>
      </div>
    </div>
  );
}

export default SelectionSidebarExample;

/**
 * INTEGRAÇÃO NA TRANSCRIÇÃO PAGE
 *
 * Para integrar o SelectionSidebar na TranscricaoPage:
 *
 * 1. Importar o componente:
 *
 * import { SelectionSidebar } from './components';
 *
 *
 * 2. Criar estado para as seleções com dados completos:
 *
 * const [textSelections, setTextSelections] = useState([]);
 *
 *
 * 3. Sincronizar com useMultiSelect (modo cards):
 *
 * const selection = useMultiSelect();
 *
 * // Converter IDs selecionados em objetos completos
 * const cardSelections = useMemo(() => {
 *   return selection.selectedIds.map(id => {
 *     const segment = transcription.find(s => s.id === id);
 *     return {
 *       id: segment.id,
 *       text: segment.text,
 *       source: 'cards'
 *     };
 *   }).filter(Boolean);
 * }, [selection.selectedIds, transcription]);
 *
 *
 * 4. Handlers:
 *
 * const handleRemoveSelection = useCallback((id) => {
 *   if (viewMode === 'cards') {
 *     selection.deselect(id);
 *   } else {
 *     setTextHighlights(prev => prev.filter(h => h.id !== id));
 *   }
 * }, [viewMode, selection]);
 *
 * const handleReorderSelection = useCallback((fromIndex, toIndex) => {
 *   // Se quiser manter ordem das seleções,
 *   // pode criar um estado separado para isso
 *   // Por enquanto, a ordem segue a ordem de seleção
 * }, []);
 *
 * const handleClearSelections = useCallback(() => {
 *   if (viewMode === 'cards') {
 *     selection.deselectAll();
 *   } else {
 *     setTextHighlights([]);
 *   }
 * }, [viewMode, selection]);
 *
 *
 * 5. Renderizar na sidebar direita (substituindo ou ao lado do ConfigPanel):
 *
 * <div className="w-full lg:w-2/5 space-y-4">
 *   <SelectionSidebar
 *     selections={viewMode === 'cards' ? cardSelections : textHighlights}
 *     onRemove={handleRemoveSelection}
 *     onReorder={handleReorderSelection}
 *     onClear={handleClearSelections}
 *   />
 *
 *   <ConfigPanel
 *     config={config}
 *     onChange={setConfig}
 *     selection={{
 *       selectedCount: viewMode === 'cards'
 *         ? selection.selectedCount
 *         : textHighlights.length,
 *       hasSelection: viewMode === 'cards'
 *         ? selection.hasSelection
 *         : textHighlights.length > 0
 *     }}
 *     video={videoData}
 *     onGenerate={handleGenerate}
 *     isGenerating={isGenerating}
 *     viewMode={viewMode}
 *   />
 * </div>
 */
