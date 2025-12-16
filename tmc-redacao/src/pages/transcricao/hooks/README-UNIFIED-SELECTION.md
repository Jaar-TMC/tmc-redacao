# Sistema Unificado de Selecao - useUnifiedSelection

## Visao Geral

O hook `useUnifiedSelection` unifica o gerenciamento de selecoes entre as duas visualizacoes da pagina de transcricao:

- **Visualizacao Topicos**: Selecao de cards inteiros (segmentos)
- **Visualizacao Completa**: Selecao de texto livre por arrasto

## Problema Resolvido

**Antes**: Cada visualizacao tinha seu proprio estado de selecao independente. Ao trocar de visualizacao, as selecoes eram perdidas.

**Depois**: Um unico hook gerencia todas as selecoes, preservando-as ao trocar de visualizacao.

## Estrutura de Dados

Cada selecao e armazenada como um objeto com a seguinte estrutura:

```javascript
{
  id: string,              // Identificador unico
  text: string,            // Texto selecionado
  source: 'card' | 'text', // Origem da selecao
  segmentId?: string,      // ID do segmento (se source === 'card')
  startTime?: string       // Timestamp (se source === 'card')
}
```

## API do Hook

### Estado Retornado

```javascript
const {
  // Arrays de selecoes
  selections,           // Array completo de todas as selecoes
  cardSelectionIds,     // Array apenas dos IDs de cards selecionados
  textSelections,       // Array apenas das selecoes de texto

  // Contadores
  selectedCount,        // Total de selecoes
  cardSelectionCount,   // Numero de cards selecionados
  textSelectionCount,   // Numero de selecoes de texto
  totalWords,          // Total de palavras em todas as selecoes

  // Flags
  hasSelection,         // true se houver alguma selecao

  // Funcoes de adicao
  addCardSelection,     // Adiciona/remove selecao de card (toggle)
  addTextSelection,     // Adiciona selecao de texto

  // Funcoes de remocao
  removeSelection,      // Remove por ID
  removeTextSelection,  // Remove selecao de texto especifica
  removeCardSelection,  // Remove selecao de card especifica

  // Funcoes de limpeza
  clearAll,            // Limpa todas as selecoes
  clearCardSelections, // Limpa apenas selecoes de cards
  clearTextSelections, // Limpa apenas selecoes de texto

  // Funcoes de verificacao
  isCardSelected,      // Verifica se um card esta selecionado
  isTextSelected,      // Verifica se um texto esta selecionado
  getSelections,       // Retorna todas as selecoes

  // Funcoes de selecao em massa
  selectAllCards       // Seleciona todos os cards de uma lista
} = useUnifiedSelection();
```

## Uso

### Na TranscricaoPage.jsx

```javascript
import { useUnifiedSelection } from './hooks';

function TranscricaoPage() {
  const selection = useUnifiedSelection();

  // Passar para visualizacao de cards
  <TranscriptionCard
    isSelected={selection.isCardSelected(segment.id)}
    onToggle={() => selection.addCardSelection(segment.id, segment.text, segment.startTime)}
  />

  // Passar para visualizacao completa
  <FullTranscriptionView
    selection={selection}
  />

  // Passar para ConfigPanel
  <ConfigPanel
    selection={{
      selectedCount: selection.selectedCount,
      hasSelection: selection.hasSelection,
      totalWords: selection.totalWords,
      cardCount: selection.cardSelectionCount,
      textCount: selection.textSelectionCount
    }}
  />
}
```

### Na FullTranscriptionView.jsx

```javascript
function FullTranscriptionView({ selection }) {
  // Obter highlights
  const highlights = selection?.textSelections || [];

  // Adicionar selecao
  const handleMouseUp = () => {
    const selectedText = window.getSelection().toString().trim();
    if (selectedText && !selection?.isTextSelected(selectedText)) {
      selection.addTextSelection(selectedText);
    }
  };

  // Remover selecao
  const removeHighlight = (highlightId) => {
    selection.removeSelection(highlightId);
  };

  // Limpar todas
  const clearAll = () => {
    selection.clearTextSelections();
  };
}
```

## Beneficios

1. **Persistencia**: Selecoes sao mantidas ao trocar de visualizacao
2. **Unificacao**: Um unico sistema para ambos os tipos de selecao
3. **Estatisticas**: Contagem de palavras e outras metricas calculadas automaticamente
4. **Flexibilidade**: Suporta mixagem de selecoes de cards e texto
5. **Compatibilidade**: Mantem compatibilidade com ConfigPanel

## Fluxo de Dados

```
TranscricaoPage (useUnifiedSelection)
    |
    ├─> Visualizacao Topicos (TranscriptionCard)
    |   └─> Usa: isCardSelected, addCardSelection
    |
    ├─> Visualizacao Completa (FullTranscriptionView)
    |   └─> Usa: textSelections, addTextSelection, removeSelection
    |
    └─> ConfigPanel
        └─> Recebe: selectedCount, hasSelection, totalWords, cardCount, textCount
```

## Exemplos de Uso

### Selecionar todos os cards

```javascript
const handleSelectAll = () => {
  selection.selectAllCards(transcription);
};
```

### Limpar tudo

```javascript
const handleClearAll = () => {
  selection.clearAll();
};
```

### Verificar se ha selecoes mistas

```javascript
const hasMixedSelection = selection.cardSelectionCount > 0 && selection.textSelectionCount > 0;
```

### Obter texto de todas as selecoes

```javascript
const allText = selection.getSelections().map(s => s.text).join('\n');
```

## Notas de Implementacao

- O hook usa `useState` para armazenar o array de selecoes
- `useMemo` e usado para calcular valores derivados (contadores, estatisticas)
- `useCallback` e usado em todas as funcoes para evitar re-renders desnecessarios
- IDs de cards usam o prefixo `card-` para facil identificacao
- IDs de texto usam timestamp + random para garantir unicidade
