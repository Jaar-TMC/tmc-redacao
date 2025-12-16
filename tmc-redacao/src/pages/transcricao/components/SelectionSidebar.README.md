# SelectionSidebar

Componente de sidebar que exibe preview dos trechos de texto selecionados pelo usuário na página de transcrição.

## Funcionalidades

- Exibe lista de trechos/textos selecionados
- Preview compacto com opção de expandir
- Contagem total de palavras e tempo estimado de leitura
- Remover itens individuais
- Reordenar itens (botões up/down)
- Limpar todas as seleções
- Estado vazio com mensagem informativa
- Acessibilidade completa (ARIA labels, keyboard navigation)

## Props

| Prop | Tipo | Obrigatório | Descrição |
|------|------|-------------|-----------|
| `selections` | `Array<Selection>` | Não | Array de seleções (padrão: `[]`) |
| `onRemove` | `Function` | Sim | Callback ao remover item: `(id: string) => void` |
| `onReorder` | `Function` | Sim | Callback ao reordenar: `(fromIndex: number, toIndex: number) => void` |
| `onClear` | `Function` | Sim | Callback ao limpar todas seleções: `() => void` |

### Tipo `Selection`

```typescript
{
  id: string;           // ID único da seleção
  text: string;         // Texto selecionado
  source: 'cards' | 'full'; // Origem: seleção por cards ou texto completo
}
```

## Uso Básico

```jsx
import { SelectionSidebar } from './components';

function TranscricaoPage() {
  const [selections, setSelections] = useState([]);

  const handleRemove = (id) => {
    setSelections(prev => prev.filter(sel => sel.id !== id));
  };

  const handleReorder = (fromIndex, toIndex) => {
    setSelections(prev => {
      const newSelections = [...prev];
      const [removed] = newSelections.splice(fromIndex, 1);
      newSelections.splice(toIndex, 0, removed);
      return newSelections;
    });
  };

  const handleClear = () => {
    setSelections([]);
  };

  return (
    <SelectionSidebar
      selections={selections}
      onRemove={handleRemove}
      onReorder={handleReorder}
      onClear={handleClear}
    />
  );
}
```

## Integração com TranscricaoPage

### Modo Cards

No modo de visualização por cards, sincronize com o hook `useMultiSelect`:

```jsx
import { useMemo } from 'react';
import { useMultiSelect } from './hooks';

const selection = useMultiSelect();

// Converter IDs selecionados em objetos Selection
const cardSelections = useMemo(() => {
  return selection.selectedIds.map(id => {
    const segment = transcription.find(s => s.id === id);
    return {
      id: segment.id,
      text: segment.text,
      source: 'cards'
    };
  }).filter(Boolean);
}, [selection.selectedIds, transcription]);

// Handler para remover
const handleRemoveSelection = (id) => {
  selection.deselect(id);
};

// Renderizar
<SelectionSidebar
  selections={cardSelections}
  onRemove={handleRemoveSelection}
  onReorder={handleReorderSelection}
  onClear={selection.deselectAll}
/>
```

### Modo Full (Texto Completo)

No modo de texto completo, use o estado `textHighlights`:

```jsx
const [textHighlights, setTextHighlights] = useState([]);

// textHighlights já vem no formato correto:
// [{ id, text, source: 'full' }]

<SelectionSidebar
  selections={textHighlights}
  onRemove={(id) => setTextHighlights(prev => prev.filter(h => h.id !== id))}
  onReorder={handleReorderHighlights}
  onClear={() => setTextHighlights([])}
/>
```

## Recursos de UI/UX

### Preview de Texto

- Texto truncado em 120 caracteres por padrão
- Clique para expandir/recolher preview completo
- Preserva aspas no texto

### Estatísticas

- Contador de itens selecionados
- Total de palavras somando todas as seleções
- Tempo estimado de leitura (200 palavras/minuto)

### Reordenação

- Botões ⬆️ (ChevronUp) e ⬇️ (ChevronDown)
- Primeiro item: botão ⬆️ desabilitado
- Último item: botão ⬇️ desabilitado
- Ícone de grip (GripVertical) como indicador visual

### Estado Vazio

Quando `selections.length === 0`:

- Ícone de documento
- Mensagem "Nenhum trecho selecionado"
- Instrução para o usuário

### Confirmação de Limpeza

Ao clicar em "Limpar Tudo", exibe confirmação via `window.confirm`:

```
Deseja realmente limpar todas as seleções?
```

## Acessibilidade

### ARIA Attributes

- `role="complementary"` no container principal
- `aria-label="Painel de seleções"` para contexto
- `aria-expanded` nos botões de expandir
- `aria-label` descritivos em todos os botões

### Keyboard Navigation

- Tab/Shift+Tab para navegar entre botões
- Enter/Space para ativar botões
- Todas as ações acessíveis via teclado

### Semântica

- Uso de botões (`<button>`) para ações interativas
- Hierarquia de headings (`<h2>` para título)
- Ícones com `aria-hidden="true"`

## Cores do Tema

Seguindo o design system TMC:

- **tmc-orange**: Badges de fonte, hover states
- **tmc-dark-green**: (reservado para futuras features)
- **off-white**: Background dos itens
- **light-gray**: Borders
- **medium-gray**: Textos secundários
- **dark-gray**: Textos principais
- **error**: Botão de remover (hover)

## Scrolling

- Lista com scroll vertical automático
- `max-h-[calc(100vh-20rem)]` para não ultrapassar viewport
- Scrollbar customizado via CSS global

## Performance

- `useMemo` para calcular totalWords e estimatedMinutes
- `useCallback` para handlers evitando re-renders
- Estado local `expandedId` para controle de expansão

## Testes Sugeridos

1. **Funcionalidade**
   - Remover item individual
   - Reordenar itens (up/down)
   - Limpar todas seleções
   - Expandir/recolher preview

2. **Estados**
   - Lista vazia (empty state)
   - 1 item (botão down desabilitado)
   - Múltiplos itens
   - Muitos itens (scroll)

3. **Acessibilidade**
   - Navegação por teclado
   - Screen reader (NVDA/JAWS)
   - Contraste de cores (WCAG 2.1 AA)

4. **Responsividade**
   - Desktop
   - Tablet
   - Mobile (integração com layout responsivo da página)

## Próximas Melhorias

- [ ] Drag & drop nativo (HTML5 Drag API)
- [ ] Animações de reordenação (Framer Motion)
- [ ] Busca/filtro dentro das seleções
- [ ] Exportar seleções (JSON/texto)
- [ ] Highlight do item ao passar mouse no card correspondente
- [ ] Atalhos de teclado (Del para remover, Ctrl+A para selecionar tudo)

## Arquivos Relacionados

- `SelectionSidebar.jsx` - Componente principal
- `SelectionSidebar.example.jsx` - Exemplo de uso e integração
- `index.js` - Export do componente
- `TranscricaoPage.jsx` - Página que usa o componente
- `useMultiSelect.js` - Hook de seleção múltipla (modo cards)

## Dependências

- React 19+
- PropTypes
- Lucide React (ícones)
- Tailwind CSS

## Licença

TMC Redação - Uso interno
