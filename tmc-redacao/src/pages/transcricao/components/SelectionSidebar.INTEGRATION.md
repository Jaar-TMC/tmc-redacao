# Guia de Integração: SelectionSidebar

Este guia mostra como integrar o componente `SelectionSidebar` na página `TranscricaoPage.jsx`.

## Passo 1: Importar o Componente

No arquivo `TranscricaoPage.jsx`, adicione a importação:

```jsx
import {
  YouTubeInput,
  VideoPreview,
  TranscriptionCard,
  FullTranscriptionView,
  ConfigPanel,
  ProgressOverlay,
  StepIndicator,
  SelectionSidebar  // ← Adicionar esta linha
} from './components';
```

## Passo 2: Criar Estado para Seleções com Dados Completos

O `SelectionSidebar` precisa receber objetos `{ id, text, source }`, não apenas IDs.

Adicione após os estados existentes (linha ~90):

```jsx
// Estado de ordenação customizada (opcional)
const [selectionOrder, setSelectionOrder] = useState([]);
```

## Passo 3: Criar Helpers para Conversão de Dados

Adicione estes `useMemo` após as variáveis de estado:

```jsx
// Converter seleções do modo cards para formato do SelectionSidebar
const cardSelections = useMemo(() => {
  return selection.selectedIds.map(id => {
    const segment = transcription.find(s => s.id === id);
    if (!segment) return null;
    return {
      id: segment.id,
      text: segment.text,
      source: 'cards'
    };
  }).filter(Boolean);
}, [selection.selectedIds, transcription]);

// Seleções unificadas baseadas no viewMode
const unifiedSelections = useMemo(() => {
  return viewMode === 'cards' ? cardSelections : textHighlights;
}, [viewMode, cardSelections, textHighlights]);
```

## Passo 4: Criar Handlers

Adicione estes handlers após os handlers existentes:

```jsx
// Handler para remover seleção individual
const handleRemoveSelection = useCallback((id) => {
  if (viewMode === 'cards') {
    selection.deselect(id);
  } else {
    setTextHighlights(prev => prev.filter(h => h.id !== id));
  }
}, [viewMode, selection]);

// Handler para reordenar seleções
const handleReorderSelection = useCallback((fromIndex, toIndex) => {
  if (viewMode === 'cards') {
    // Para modo cards, reordenar os IDs selecionados
    const newSelectedIds = [...selection.selectedIds];
    const [removed] = newSelectedIds.splice(fromIndex, 1);
    newSelectedIds.splice(toIndex, 0, removed);

    // Atualizar seleção (desselecionar tudo e reselecionar na nova ordem)
    selection.deselectAll();
    setTimeout(() => {
      selection.selectAll(newSelectedIds);
    }, 0);
  } else {
    // Para modo full, reordenar textHighlights
    setTextHighlights(prev => {
      const newHighlights = [...prev];
      const [removed] = newHighlights.splice(fromIndex, 1);
      newHighlights.splice(toIndex, 0, removed);
      return newHighlights;
    });
  }
}, [viewMode, selection]);

// Handler para limpar todas as seleções
const handleClearAllSelections = useCallback(() => {
  if (viewMode === 'cards') {
    selection.deselectAll();
  } else {
    setTextHighlights([]);
  }
}, [viewMode, selection]);
```

## Passo 5: Atualizar Layout da Coluna Direita

Localize a seção "Coluna direita: Configurações" (linha ~495) e substitua por:

```jsx
{/* Coluna direita: Seleções + Configurações */}
<div className="w-full lg:w-2/5 space-y-4">
  {/* Painel de Seleções */}
  <SelectionSidebar
    selections={unifiedSelections}
    onRemove={handleRemoveSelection}
    onReorder={handleReorderSelection}
    onClear={handleClearAllSelections}
  />

  {/* Painel de Configuração */}
  <ConfigPanel
    config={config}
    onChange={setConfig}
    selection={viewMode === 'cards'
      ? {
          selectedCount: selection.selectedCount,
          hasSelection: selection.hasSelection
        }
      : {
          selectedCount: textHighlights.length,
          hasSelection: textHighlights.length > 0,
          totalWords: textHighlights.reduce((acc, h) => acc + h.text.split(/\s+/).length, 0)
        }
    }
    video={videoData}
    onGenerate={handleGenerate}
    isGenerating={isGenerating}
    viewMode={viewMode}
  />
</div>
```

## Passo 6: (Opcional) Ajustar ConfigPanel

Se quiser que o ConfigPanel seja mais compacto (já que agora tem o SelectionSidebar acima), você pode:

1. Remover a seção "Resumo da Seleção" do ConfigPanel (linhas 60-85)
2. Deixar essa informação apenas no SelectionSidebar
3. Ou manter ambos para redundância útil ao usuário

## Resultado Esperado

Após a integração, o usuário verá:

1. **Coluna Esquerda** (60%):
   - Player do YouTube
   - Toolbar (toggle cards/full, select all, busca)
   - Transcrição (cards ou texto completo)

2. **Coluna Direita** (40%):
   - **SelectionSidebar** (novo!):
     - Lista de trechos selecionados
     - Preview com expand/collapse
     - Botões para reordenar (↑/↓)
     - Botão para remover individual (×)
     - Estatísticas (itens, palavras, tempo)
     - Botão "Limpar Tudo"

   - **ConfigPanel** (existente):
     - Tom da matéria
     - Persona do redator
     - Configurações avançadas
     - Fonte do vídeo
     - Botão "Gerar Matéria"

## Comportamento por ViewMode

### Modo Cards (`viewMode === 'cards'`)

- `SelectionSidebar` mostra trechos dos cards selecionados
- Source tag: "Tópico"
- Sincronizado com `useMultiSelect`

### Modo Full (`viewMode === 'full'`)

- `SelectionSidebar` mostra textos highlightados
- Source tag: "Texto"
- Sincronizado com `textHighlights`

## Estados de UI

### Vazio (0 seleções)

```
┌─────────────────────────┐
│      Seleções           │
├─────────────────────────┤
│                         │
│     [ícone documento]   │
│                         │
│  Nenhum trecho          │
│  selecionado            │
│                         │
│  Selecione trechos da   │
│  transcrição...         │
│                         │
└─────────────────────────┘
```

### Com Seleções (3 itens)

```
┌─────────────────────────────────┐
│ Seleções        [Limpar Tudo]   │
├─────────────────────────────────┤
│ 📄 3 itens  #️⃣ 450 palavras      │
│ ⏱️ Tempo: 3 minutos              │
├─────────────────────────────────┤
│ ⠿ "Olá, sejam bem-vind..."      │
│   # 25 palavras  [Tópico]       │
│   [↑] [↓] [×]                   │
├─────────────────────────────────┤
│ ⠿ "Nos últimos meses..."        │
│   # 15 palavras  [Tópico]       │
│   [↑] [↓] [×]                   │
├─────────────────────────────────┤
│ ⠿ "Especialistas apontam..."    │
│   # 12 palavras  [Texto]        │
│   [↑] [↓] [×]                   │
└─────────────────────────────────┘
```

## Fluxo de Interação

1. **Usuário seleciona card/texto**
   → Aparece no SelectionSidebar

2. **Usuário clica em "×" no SelectionSidebar**
   → Item removido
   → Card/highlight também desmarca

3. **Usuário clica em ↑/↓**
   → Item move na lista
   → Ordem mantida para geração

4. **Usuário clica em "Limpar Tudo"**
   → Confirmação
   → Todas seleções removidas
   → SelectionSidebar volta ao estado vazio

5. **Usuário clica no preview**
   → Texto expande/recolhe

## Testes Recomendados

- [ ] Selecionar cards → ver aparecer no sidebar
- [ ] Remover do sidebar → card desmarca
- [ ] Reordenar → ordem muda
- [ ] Limpar tudo → confirmação e limpeza
- [ ] Alternar viewMode → sidebar atualiza
- [ ] Expandir/recolher preview
- [ ] Testar com 0, 1, 5, 10+ seleções
- [ ] Testar scroll com muitas seleções
- [ ] Keyboard navigation
- [ ] Screen reader

## Troubleshooting

### SelectionSidebar não atualiza

- Verifique se `unifiedSelections` está sendo recalculado
- Check console para warnings do React
- Confirme que `selection.selectedIds` ou `textHighlights` está mudando

### Ordem não é mantida

- Implemente estado `selectionOrder` customizado
- Ou aceite que ordem segue a ordem de clique

### Performance com muitas seleções

- `useMemo` já otimiza cálculos
- Se necessário, adicione React.memo no SelectionItem
- Virtualização (react-window) para 100+ itens

## Próximos Passos

Após integração básica funcionar:

1. [ ] Adicionar drag & drop visual
2. [ ] Sincronizar highlight ao passar mouse
3. [ ] Salvar ordem no localStorage
4. [ ] Exportar seleções
5. [ ] Atalhos de teclado

---

**Dúvidas?** Consulte:
- `SelectionSidebar.README.md` - Documentação completa
- `SelectionSidebar.example.jsx` - Exemplo standalone
