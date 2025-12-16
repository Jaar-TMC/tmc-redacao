# MiniPlayer Component

## Resumo

Componente de mini player de vídeo fixo que aparece automaticamente quando o player principal do YouTube sai da visualização do usuário durante a navegação pela transcrição.

## Arquivos Criados

1. **MiniPlayer.jsx** - Componente principal
2. **MINI_PLAYER_USAGE.md** - Documentação completa de uso
3. **MiniPlayer.example.jsx** - Exemplos de integração
4. **index.js** - Atualizado com export do MiniPlayer

## Características Implementadas

### Funcionalidades Principais
- [x] Aparece/desaparece automaticamente usando IntersectionObserver
- [x] Posição fixed configurável (bottom-right, bottom-left, top-right, top-left)
- [x] Botão para expandir/minimizar (320px → 90vw)
- [x] Botão para fechar o mini player
- [x] Controles básicos: play/pause integrados
- [x] Animação suave ao aparecer/desaparecer (300ms ease-out)
- [x] Z-index 50 (adequado para não conflitar)
- [x] Sincronização de tempo opcional com player principal
- [x] Integração completa com YouTube IFrame API

### Acessibilidade (WCAG 2.1)
- [x] Role semântico: `complementary`
- [x] Aria-labels em todos os botões interativos
- [x] Atalhos de teclado (Espaço, Esc)
- [x] Títulos descritivos com hints de atalhos
- [x] Estados visuais claros (hover, focus)
- [x] Navegação completa por teclado

### Estilização
- [x] Usa tema TMC (bg-dark-green, tmc-orange)
- [x] Classes Tailwind do projeto
- [x] Shadow elevado (shadow-2xl)
- [x] Bordas arredondadas (rounded-xl)
- [x] Transições suaves
- [x] Responsivo (ajusta-se ao viewport)

### Performance
- [x] useCallback para callbacks memorizados
- [x] Lazy loading da YouTube IFrame API
- [x] Cleanup adequado (destroy player ao desmontar)
- [x] Renderização condicional (só renderiza quando visível)
- [x] IntersectionObserver eficiente

## Props API

```typescript
interface MiniPlayerProps {
  // Obrigatórias
  videoId: string;              // ID do vídeo do YouTube
  isMainPlayerVisible: boolean; // Se o player principal está visível

  // Opcionais
  currentTime?: number;         // Tempo atual em segundos (default: 0)
  onTimeUpdate?: (time: number) => void; // Callback de atualização de tempo
  position?: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left'; // Default: 'bottom-right'
}
```

## Integração Rápida (5 minutos)

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

### 4. Adicionar ref ao player principal
```jsx
<div ref={mainPlayerRef} className="aspect-video">
  <iframe src={`https://www.youtube.com/embed/${videoData.videoId}`} ... />
</div>
```

### 5. Renderizar MiniPlayer
```jsx
{currentStep === 3 && videoData && (
  <MiniPlayer
    videoId={videoData.videoId}
    isMainPlayerVisible={isMainPlayerVisible}
  />
)}
```

## Atalhos de Teclado

| Tecla | Ação |
|-------|------|
| Espaço | Play/Pause |
| Esc | Minimizar (se expandido) |
| X | Fechar mini player |

## Comportamento

### Aparecer/Desaparecer
- Aparece quando: `isMainPlayerVisible === false && !isClosed`
- Desaparece quando: `isMainPlayerVisible === true || isClosed`
- Reset do fechamento: Quando player principal volta a ficar visível

### Tamanhos
- **Minimizado**: 320px (w-80)
- **Expandido**: 90vw (max-w-2xl ≈ 768px)
- **Aspect Ratio**: 16:9 (aspect-video)

### Animações
- **Entrada**: translate-y-0 opacity-100 (300ms)
- **Saída**: translate-y-4 opacity-0 (300ms)
- **Easing**: ease-out

### Z-Index Hierarchy
```
MiniPlayer:        z-50
Header (sticky):   z-40
ActionPanel:       z-30
Footer Mobile:     z-30
TrendsSidebar:     z-20
```

## Sincronização Avançada

Para sincronização bidirecional entre players:

```jsx
// Estado compartilhado
const [currentTime, setCurrentTime] = useState(0);

// Callback do mini player
const handleMiniPlayerTimeUpdate = (time) => {
  setCurrentTime(time);
  if (mainYouTubePlayerRef.current && isMainPlayerVisible) {
    mainYouTubePlayerRef.current.seekTo(time, true);
  }
};

// MiniPlayer com sincronização
<MiniPlayer
  videoId={videoData.videoId}
  isMainPlayerVisible={isMainPlayerVisible}
  currentTime={currentTime}
  onTimeUpdate={handleMiniPlayerTimeUpdate}
/>
```

## Responsividade

### Desktop (lg+)
- Posição: bottom-right ou top-right
- Tamanho expandido: max-w-2xl (768px)

### Tablet (md)
- Posição: bottom-right
- Tamanho expandido: 90vw

### Mobile (sm)
- Considerar: top-right para não sobrepor footer fixo
- Tamanho expandido: 90vw
- Hint de atalhos escondido

## Melhorias Futuras

Sugestões para próximas versões:

1. **Controles Avançados**
   - Controle de volume
   - Barra de progresso customizada
   - Velocidade de reprodução

2. **UX Aprimorada**
   - Drag & drop para reposicionar
   - Redimensionamento manual
   - Modo "sempre visível" (pin)

3. **Persistência**
   - Salvar posição no localStorage
   - Lembrar estado expandido/minimizado
   - Salvar preferência de posição

4. **Integrações**
   - Picture-in-Picture nativo
   - Fullscreen API
   - Media Session API (controles do sistema)

5. **Performance**
   - Lazy load de thumbnails
   - Preload de próximos segundos
   - Compressão de vídeo adaptativa

## Testes Sugeridos

### Funcionalidade
- [ ] MiniPlayer aparece quando rolar para baixo
- [ ] MiniPlayer desaparece quando rolar para cima
- [ ] Botão expandir/minimizar funciona
- [ ] Botão fechar funciona e reseta ao voltar
- [ ] Play/pause sincroniza com vídeo

### Acessibilidade
- [ ] Navegação por teclado funciona
- [ ] Screen reader lê corretamente
- [ ] Atalhos funcionam
- [ ] Focus visível em todos os controles

### Responsividade
- [ ] Funciona em mobile (320px+)
- [ ] Funciona em tablet (768px+)
- [ ] Funciona em desktop (1024px+)
- [ ] Não quebra layout em nenhum viewport

### Performance
- [ ] Sem memory leaks
- [ ] Cleanup correto ao desmontar
- [ ] IntersectionObserver não causa lag
- [ ] YouTube API carrega apenas uma vez

## Problemas Conhecidos

Nenhum no momento. Reportar issues em:
`F:\OneDrive - jaarconsult.com.br\JaarConsult - Oficial - TMC\Projeto Ferramenta TMC\.claude\issues\`

## Changelog

### v1.0.0 (2025-12-16)
- Implementação inicial
- Integração com YouTube IFrame API
- Suporte a 4 posições
- Atalhos de teclado
- Animações suaves
- Acessibilidade WCAG 2.1
- Sincronização de tempo opcional
- Documentação completa

## Créditos

Desenvolvido seguindo os padrões da skill **frontend-dev-agent** do projeto TMC Redação.

**Stack**: React 19 + Vite + Tailwind CSS + Lucide Icons + PropTypes

**Padrões**: COMPONENT-PATTERNS.md, STACK-REFERENCE.md
