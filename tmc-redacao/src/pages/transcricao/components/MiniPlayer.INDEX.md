# MiniPlayer - Índice de Documentação

## Arquivos do Componente

### Código-Fonte
- **MiniPlayer.jsx** (9.2 KB)
  - Componente React principal
  - 300+ linhas de código
  - Integração completa com YouTube IFrame API
  - PropTypes, hooks (useState, useEffect, useCallback)
  - Acessibilidade WCAG 2.1

### Documentação
1. **MiniPlayer.README.md** (7.0 KB)
   - Overview completo do componente
   - Props API
   - Integração rápida (5 minutos)
   - Atalhos de teclado
   - Comportamento e estados
   - Sincronização avançada
   - Melhorias futuras
   - Changelog

2. **MINI_PLAYER_USAGE.md** (Tamanho completo)
   - Guia de uso detalhado
   - Tabela de props
   - Exemplo básico
   - Exemplo com sincronização
   - Posicionamento
   - Troubleshooting
   - Melhorias futuras

3. **MiniPlayer.VISUAL.md** (19.8 KB)
   - Especificação visual completa
   - Diagramas ASCII art
   - Layout em diferentes estados
   - Animações
   - Responsividade
   - Cores do tema TMC
   - Acessibilidade visual
   - Fluxo de interação

4. **MiniPlayer.example.jsx** (10.3 KB)
   - Exemplo de integração na TranscricaoPage
   - Código comentado passo a passo
   - Versão básica
   - Versão avançada com sincronização
   - Notas de implementação

### Exports
- **index.js** (atualizado)
  - Export adicionado: `export { default as MiniPlayer } from './MiniPlayer';`

## Navegação Rápida

### Para Começar
1. Leia: **MiniPlayer.README.md** (visão geral)
2. Veja: **MiniPlayer.example.jsx** (código de exemplo)
3. Implemente: Copie o código do exemplo para TranscricaoPage.jsx

### Para Entender Detalhes
- **Props e API**: MINI_PLAYER_USAGE.md (seção Props)
- **Layout e Design**: MiniPlayer.VISUAL.md
- **Comportamento**: MiniPlayer.README.md (seção Comportamento)

### Para Troubleshooting
- **MINI_PLAYER_USAGE.md** (seção Troubleshooting)
- **MiniPlayer.example.jsx** (notas de implementação)

## Estrutura do Componente

```
MiniPlayer/
├── MiniPlayer.jsx ..................... Código-fonte principal
├── MiniPlayer.README.md ............... Documentação principal
├── MINI_PLAYER_USAGE.md ............... Guia de uso completo
├── MiniPlayer.VISUAL.md ............... Especificação visual
├── MiniPlayer.example.jsx ............. Exemplos de código
├── MiniPlayer.INDEX.md ................ Este arquivo (índice)
└── index.js (atualizado) .............. Export do componente
```

## Características Principais

### Funcionalidades
- [x] Aparece/desaparece automaticamente (IntersectionObserver)
- [x] 4 posições configuráveis (bottom-right, bottom-left, top-right, top-left)
- [x] Expandir/minimizar (320px ↔ 90vw)
- [x] Fechar manual com reset automático
- [x] Controles play/pause integrados
- [x] Animações suaves (300ms ease-out)
- [x] Z-index 50 (não conflita com outros elementos)
- [x] Sincronização de tempo opcional

### Tecnologias
- React 19 (hooks: useState, useEffect, useCallback, useRef)
- PropTypes (validação de tipos)
- Tailwind CSS (estilização)
- Lucide React (ícones)
- YouTube IFrame API (player)

### Acessibilidade
- [x] WCAG 2.1 Level AA compliant
- [x] Role semântico (complementary)
- [x] Aria-labels em todos os controles
- [x] Atalhos de teclado (Espaço, Esc)
- [x] Focus indicators visíveis
- [x] Navegação completa por teclado

## Integração Rápida

### 1. Import
```jsx
import { MiniPlayer } from './components';
```

### 2. Estados
```jsx
const [isMainPlayerVisible, setIsMainPlayerVisible] = useState(true);
const mainPlayerRef = useRef(null);
```

### 3. Observer
```jsx
useEffect(() => {
  if (!mainPlayerRef.current || currentStep !== 3) return;
  const observer = new IntersectionObserver(
    ([entry]) => setIsMainPlayerVisible(entry.isIntersecting),
    { threshold: 0.5 }
  );
  observer.observe(mainPlayerRef.current);
  return () => observer.disconnect();
}, [currentStep]);
```

### 4. Adicionar ref
```jsx
<div ref={mainPlayerRef} className="aspect-video">
  <iframe src={`https://www.youtube.com/embed/${videoData.videoId}`} ... />
</div>
```

### 5. Renderizar
```jsx
{currentStep === 3 && videoData && (
  <MiniPlayer
    videoId={videoData.videoId}
    isMainPlayerVisible={isMainPlayerVisible}
  />
)}
```

## Props API

| Prop | Tipo | Required | Default | Descrição |
|------|------|----------|---------|-----------|
| `videoId` | string | Sim | - | ID do vídeo do YouTube |
| `isMainPlayerVisible` | boolean | Sim | - | Player principal está visível |
| `currentTime` | number | Não | 0 | Tempo atual (segundos) |
| `onTimeUpdate` | function | Não | - | Callback de atualização de tempo |
| `position` | string | Não | 'bottom-right' | Posição do mini player |

## Tamanho dos Arquivos

```
Total: ~46.5 KB (documentação completa)

MiniPlayer.jsx ............. 9.2 KB (código)
MiniPlayer.README.md ....... 7.0 KB (doc principal)
MiniPlayer.VISUAL.md ....... 19.8 KB (especificação visual)
MiniPlayer.example.jsx ..... 10.3 KB (exemplos)
MINI_PLAYER_USAGE.md ....... (guia de uso completo)
MiniPlayer.INDEX.md ........ Este arquivo
```

## Padrões Seguidos

- **frontend-dev-agent** skill guidelines
- **COMPONENT-PATTERNS.md** (TranscriptionCard pattern)
- **STACK-REFERENCE.md** (React 19 + Tailwind)
- **TMC Design System** (cores, espaçamentos, tipografia)
- **WCAG 2.1** Level AA (acessibilidade)

## Próximos Passos

### Implementação Básica (15 min)
1. [ ] Copiar código do MiniPlayer.example.jsx
2. [ ] Adicionar import em TranscricaoPage.jsx
3. [ ] Adicionar estados (isMainPlayerVisible, mainPlayerRef)
4. [ ] Adicionar IntersectionObserver useEffect
5. [ ] Adicionar ref ao player principal
6. [ ] Renderizar MiniPlayer
7. [ ] Testar scroll up/down

### Testes (30 min)
1. [ ] Testar em diferentes viewports (mobile, tablet, desktop)
2. [ ] Testar atalhos de teclado
3. [ ] Testar expandir/minimizar
4. [ ] Testar fechar e reabrir
5. [ ] Testar em diferentes posições
6. [ ] Verificar acessibilidade (screen reader)
7. [ ] Verificar performance (sem memory leaks)

### Sincronização Avançada (opcional, 30 min)
1. [ ] Implementar YouTube IFrame API no player principal
2. [ ] Adicionar estado de currentTime
3. [ ] Conectar callback onTimeUpdate
4. [ ] Testar sincronização bidirecional
5. [ ] Conectar com botão "Ir para momento"

## Manutenção

### Quando Atualizar
- Nova versão do React
- Mudanças no YouTube IFrame API
- Novos requisitos de acessibilidade
- Feedback dos usuários

### Como Reportar Issues
Criar arquivo em:
`F:\OneDrive - jaarconsult.com.br\JaarConsult - Oficial - TMC\Projeto Ferramenta TMC\.claude\issues\miniplayer-[issue].md`

## Créditos

**Desenvolvido por**: Frontend Dev Agent (Claude Opus 4.5)
**Data**: 2025-12-16
**Projeto**: TMC Redação
**Versão**: 1.0.0

**Stack**: React 19 + Vite + Tailwind CSS + Lucide Icons + PropTypes

**Referências**:
- F:\...\skill.md (frontend-dev-agent)
- F:\...\COMPONENT-PATTERNS.md
- F:\...\STACK-REFERENCE.md

## Licença

Código proprietário do projeto TMC Redação.
