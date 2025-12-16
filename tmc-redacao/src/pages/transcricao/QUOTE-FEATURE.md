# Funcionalidade de Marcação de Citações Diretas

## Visão Geral

A funcionalidade de marcação de citações permite que jornalistas distingam entre **falas diretas** (citações entre aspas) e **resumos parafraseados** ao trabalhar com transcrições de vídeos do YouTube.

## Componentes Criados

### 1. QuoteMarker.jsx
**Localização:** `src/pages/transcricao/components/QuoteMarker.jsx`

Botão/toggle para marcar uma seleção como citação direta.

**Props:**
- `isQuote: boolean` - Se está marcado como citação
- `onToggle: Function` - Callback ao alternar estado
- `size: 'sm' | 'md'` - Tamanho do botão (default: 'md')
- `disabled: boolean` - Se está desabilitado

**Uso:**
```jsx
<QuoteMarker
  isQuote={isQuote}
  onToggle={() => toggleQuote(id)}
  size="sm"
/>
```

### 2. SelectionTooltip.jsx
**Localização:** `src/pages/transcricao/components/SelectionTooltip.jsx`

Tooltip que aparece ao selecionar texto na transcrição completa, oferecendo opções para adicionar como resumo ou citação.

**Props:**
- `isVisible: boolean` - Se o tooltip está visível
- `position: {x: number, y: number}` - Posição do tooltip
- `onAddAsText: Function` - Callback ao adicionar como resumo
- `onAddAsQuote: Function` - Callback ao adicionar como citação
- `onClose: Function` - Callback ao fechar

**Uso:**
```jsx
<SelectionTooltip
  isVisible={tooltipVisible}
  position={tooltipPosition}
  onAddAsText={handleAddAsText}
  onAddAsQuote={handleAddAsQuote}
  onClose={handleClose}
/>
```

## Componentes Atualizados

### TranscriptionCard.jsx

**Novas Props:**
- `isQuote: boolean` - Se o card está marcado como citação
- `onToggleQuote: Function` - Callback ao marcar/desmarcar citação

**Visual Diferenciado:**
- **Citações:** Borda azul, fundo azul claro, barra lateral azul, badge "Citação", texto em itálico
- **Resumos:** Borda padrão, fundo padrão, sem barra lateral

**Uso:**
```jsx
<TranscriptionCard
  segment={segment}
  isSelected={isSelected}
  isQuote={isQuote}
  onToggle={handleToggle}
  onToggleQuote={handleToggleQuote}
  onPlaySegment={handlePlay}
  onGoToMoment={handleGoTo}
/>
```

### FullTranscriptionView.jsx

**Funcionalidades Adicionadas:**
- Tooltip ao selecionar texto com opções de adicionar como resumo ou citação
- Highlights visuais diferentes:
  - **Citações:** Fundo azul claro com ícone de aspas
  - **Resumos:** Fundo amarelo claro
- Contador separado de citações e resumos no footer
- Tooltip ao passar o mouse sobre highlights mostrando tipo

### useUnifiedSelection.js

**Novas Funções:**
- `toggleQuote(id)` - Alterna status de citação de uma seleção
- `isQuote(id)` - Verifica se uma seleção é citação

**Novos Campos:**
- `isQuote: boolean` - Adicionado em todas as seleções (cards e texto)
- `quoteCount: number` - Contador de citações

**Estrutura de Seleção Atualizada:**
```javascript
{
  id: string,
  text: string,
  source: 'card' | 'text',
  isQuote: boolean,  // NOVO
  segmentId?: string,
  startTime?: string
}
```

## Fluxo de Uso

### Modo Cards (Visualização por Tópicos)

1. Usuário seleciona um card clicando no checkbox
2. Card selecionado mostra botão "Marcar citação" no canto inferior direito
3. Ao clicar em "Marcar citação":
   - Visual do card muda para azul
   - Aparece badge "Citação" com ícone de aspas
   - Texto fica em itálico
   - Barra lateral azul no lado esquerdo
4. Pode clicar novamente para desmarcar como citação

### Modo Completo (Transcrição Completa)

1. Usuário seleciona texto arrastando o mouse
2. Tooltip aparece com duas opções:
   - **"Adicionar como resumo"** - Texto será parafraseado
   - **"Adicionar como citação"** - Fala direta entre aspas
3. Ao escolher:
   - Texto é destacado com cor correspondente (amarelo ou azul)
   - Ícone de aspas aparece se for citação
   - Hover mostra tooltip indicando o tipo
4. Clicar no highlight para remover

## Acessibilidade

- `aria-pressed` no botão QuoteMarker indica estado de toggle
- `aria-label` descritivo em todos os botões
- Cores com contraste adequado (WCAG 2.1)
- Navegação por teclado suportada
- Labels descritivos para leitores de tela

## Cores e Estilos

### Citações
- Borda: `border-blue-400`
- Fundo card: `bg-blue-50/50`
- Highlight: `bg-blue-200 hover:bg-blue-300`
- Badge: `bg-blue-500 text-white`
- Barra lateral: `bg-blue-500`

### Resumos
- Borda: `border-gray-200`
- Fundo card: `bg-white`
- Highlight: `bg-yellow-200 hover:bg-yellow-300`
- Sem badge ou barra lateral

## Integração com TranscricaoPage

```jsx
import { useUnifiedSelection } from './hooks';

function TranscricaoPage() {
  const selection = useUnifiedSelection();

  // Modo cards
  <TranscriptionCard
    segment={segment}
    isSelected={selection.isCardSelected(segment.id)}
    isQuote={selection.isQuote(segment.id)}
    onToggle={() => selection.addCardSelection(segment.id, segment.text, segment.startTime)}
    onToggleQuote={() => selection.toggleQuote(segment.id)}
    onPlaySegment={handlePlaySegment}
    onGoToMoment={handleGoToMoment}
  />

  // Modo completo
  <FullTranscriptionView
    segments={transcription}
    selection={selection}
    onGoToMoment={handleGoToMoment}
  />
}
```

## Métricas

O hook `useUnifiedSelection` fornece:
- `quoteCount` - Total de citações marcadas
- `selectedCount` - Total de seleções (citações + resumos)
- `cardSelectionCount` - Seleções de cards
- `textSelectionCount` - Seleções de texto livre

## Testes Sugeridos

1. **Marcar card como citação**
   - Selecionar card
   - Clicar em "Marcar citação"
   - Verificar mudança visual
   - Desmarcar e verificar volta ao estado normal

2. **Selecionar texto como citação**
   - Arrastar texto
   - Escolher "Adicionar como citação" no tooltip
   - Verificar highlight azul com ícone de aspas
   - Clicar para remover

3. **Alternar entre modos**
   - Marcar seleções no modo cards
   - Alternar para modo completo
   - Verificar que seleções são mantidas
   - Voltar ao modo cards

4. **Acessibilidade**
   - Navegar com Tab
   - Ativar com Enter/Space
   - Verificar leitores de tela

## Próximas Melhorias

- [ ] Atalho de teclado para marcar citação (ex: Ctrl+Q)
- [ ] Filtro para mostrar apenas citações
- [ ] Exportar citações separadamente
- [ ] Estatísticas de proporção citação/resumo
- [ ] Sugestão automática de citações (detectar aspas no texto)
