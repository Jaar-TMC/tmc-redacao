import TooltipEducativo from './TooltipEducativo';

/**
 * Exemplos de uso do TooltipEducativo
 *
 * Este arquivo demonstra diferentes casos de uso do componente TooltipEducativo
 * conforme especificado no documento de planejamento UI/UX.
 */

export default function TooltipEducativoExamples() {
  return (
    <div className="p-8 space-y-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-dark-gray mb-8">
        Exemplos de TooltipEducativo
      </h1>

      {/* Exemplo 1: Orientação sobre o Lide */}
      <div className="p-6 bg-off-white rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          <label className="text-sm font-semibold text-dark-gray">
            Orientação do Lide
          </label>
          <TooltipEducativo
            title="Orientação sobre o Lide"
            icon="📝"
            position="right"
          >
            <p>
              O lide é o primeiro parágrafo da matéria - deve responder às
              perguntas: <strong>O quê? Quem? Quando? Onde? Por quê? Como?</strong>
            </p>
            <p>Indique qual ângulo você quer destacar:</p>
            <ul>
              <li>"Focar no impacto econômico para o cidadão"</li>
              <li>"Destacar a reação do mercado financeiro"</li>
              <li>"Priorizar as declarações do ministro"</li>
            </ul>
          </TooltipEducativo>
        </div>
        <textarea
          className="w-full p-3 border border-light-gray rounded-lg"
          placeholder="Ex: Focar no impacto econômico..."
          rows={3}
        />
      </div>

      {/* Exemplo 2: Data de Publicação */}
      <div className="p-6 bg-off-white rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          <label className="text-sm font-semibold text-dark-gray">
            Data de Publicação
          </label>
          <TooltipEducativo
            title="Data de Publicação"
            icon="📅"
            position="right"
          >
            <p>
              Quando o conteúdo original foi publicado ou quando o evento
              aconteceu. Isso ajuda a IA a contextualizar temporalmente e usar
              verbos no tempo correto.
            </p>
            <p>
              <strong>Exemplo:</strong> Se o texto-base é de ontem, a IA saberá
              que deve usar "anunciou ontem" em vez de "anuncia hoje".
            </p>
          </TooltipEducativo>
        </div>
        <input
          type="date"
          className="w-full p-3 border border-light-gray rounded-lg"
        />
      </div>

      {/* Exemplo 3: Declarações de Fontes */}
      <div className="p-6 bg-off-white rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          <label className="text-sm font-semibold text-dark-gray">
            Declarações de Fontes
          </label>
          <TooltipEducativo
            title="Declarações de Fontes"
            icon="💬"
            position="auto"
          >
            <p>
              Citações diretas de especialistas, autoridades ou envolvidos dão
              credibilidade e humanizam a matéria.
            </p>
            <p>
              <strong>Formato sugerido:</strong>
            </p>
            <code>Nome, cargo/função: 'Declaração entre aspas simples'</code>
            <p>
              <strong>Exemplo:</strong>
            </p>
            <p>
              "João Silva, economista da FGV: 'As medidas terão efeito positivo
              em até 6 meses'"
            </p>
          </TooltipEducativo>
        </div>
        <textarea
          className="w-full p-3 border border-light-gray rounded-lg"
          placeholder="Adicione citações diretas..."
          rows={4}
        />
      </div>

      {/* Exemplo 4: Contexto Adicional */}
      <div className="p-6 bg-off-white rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          <label className="text-sm font-semibold text-dark-gray">
            Contexto Adicional
          </label>
          <TooltipEducativo
            title="Contexto Adicional"
            icon="ℹ️"
            position="bottom"
          >
            <p>
              Informações de background que a IA deve considerar mas que não
              estão no texto-base:
            </p>
            <ul>
              <li>
                <strong>Histórico do tema:</strong> "Essa é a terceira tentativa..."
              </li>
              <li>
                <strong>Nuances políticas:</strong> "O partido X é contra..."
              </li>
              <li>
                <strong>Dados complementares:</strong> "Segundo o IBGE..."
              </li>
              <li>
                <strong>Conexões com outros fatos:</strong> "Isso se relaciona com..."
              </li>
            </ul>
          </TooltipEducativo>
        </div>
        <textarea
          className="w-full p-3 border border-light-gray rounded-lg"
          placeholder="Adicione contexto que não está no texto-base..."
          rows={4}
        />
      </div>

      {/* Exemplo 5: Persona da Matéria */}
      <div className="p-6 bg-off-white rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          <label className="text-sm font-semibold text-dark-gray">
            Persona da Matéria
          </label>
          <TooltipEducativo
            title="Persona da Matéria"
            icon="👤"
            position="left"
          >
            <p>Define a "voz" e abordagem do texto:</p>
            <ul>
              <li>
                <strong>Jornalista Imparcial:</strong> Objetivo, factual, sem opinião
              </li>
              <li>
                <strong>Especialista:</strong> Análise técnica aprofundada
              </li>
              <li>
                <strong>Colunista:</strong> Pode incluir opinião fundamentada
              </li>
              <li>
                <strong>Influencer:</strong> Linguagem próxima e engajadora
              </li>
            </ul>
            <p>
              Para hard news, prefira "Jornalista Imparcial". Para análises,
              "Especialista" ou "Colunista".
            </p>
          </TooltipEducativo>
        </div>
        <div className="space-y-2">
          <label className="flex items-center gap-2">
            <input type="radio" name="persona" value="jornalista" defaultChecked />
            <span className="text-sm text-medium-gray">Jornalista Imparcial</span>
          </label>
          <label className="flex items-center gap-2">
            <input type="radio" name="persona" value="especialista" />
            <span className="text-sm text-medium-gray">Especialista</span>
          </label>
          <label className="flex items-center gap-2">
            <input type="radio" name="persona" value="colunista" />
            <span className="text-sm text-medium-gray">Colunista</span>
          </label>
          <label className="flex items-center gap-2">
            <input type="radio" name="persona" value="influencer" />
            <span className="text-sm text-medium-gray">Influencer</span>
          </label>
        </div>
      </div>

      {/* Exemplo 6: Tom da Escrita */}
      <div className="p-6 bg-off-white rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          <label className="text-sm font-semibold text-dark-gray">
            Tom da Escrita
          </label>
          <TooltipEducativo
            title="Tom da Escrita"
            icon="🎭"
            position="top"
          >
            <p>O tom afeta a escolha de palavras e construção das frases:</p>
            <ul>
              <li>
                <strong>Formal:</strong> Linguagem séria, vocabulário culto
              </li>
              <li>
                <strong>Informal:</strong> Mais leve, próximo do leitor
              </li>
              <li>
                <strong>Técnico:</strong> Termos especializados, para público expert
              </li>
              <li>
                <strong>Persuasivo:</strong> Argumentativo, para editoriais
              </li>
              <li>
                <strong>Neutro:</strong> Equilibrado, sem emoção
              </li>
            </ul>
            <p>
              Para notícias do dia, <strong>"Formal"</strong> ou{' '}
              <strong>"Neutro"</strong> funcionam melhor.
            </p>
          </TooltipEducativo>
        </div>
        <select className="w-full p-3 border border-light-gray rounded-lg">
          <option>Formal</option>
          <option>Informal</option>
          <option>Técnico</option>
          <option>Persuasivo</option>
          <option>Neutro</option>
        </select>
      </div>

      {/* Exemplo 7: Instruções Adicionais */}
      <div className="p-6 bg-off-white rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          <label className="text-sm font-semibold text-dark-gray">
            Instruções Adicionais para IA
          </label>
          <TooltipEducativo
            title="Instruções Adicionais"
            icon="✍️"
            position="auto"
          >
            <p>Comandos específicos para a IA seguir:</p>
            <p>
              <strong>Exemplos úteis:</strong>
            </p>
            <ul>
              <li>"Evitar termos muito técnicos"</li>
              <li>"Explicar siglas na primeira menção"</li>
              <li>"Manter parágrafos curtos (3-4 linhas)"</li>
              <li>"Incluir dados numéricos quando disponíveis"</li>
              <li>"Não usar adjetivos valorativos"</li>
            </ul>
          </TooltipEducativo>
        </div>
        <textarea
          className="w-full p-3 border border-light-gray rounded-lg"
          placeholder="Ex: Evitar termos muito técnicos..."
          rows={3}
        />
      </div>

      {/* Exemplo 8: Link Complementar */}
      <div className="p-6 bg-off-white rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          <label className="text-sm font-semibold text-dark-gray">
            Link Complementar
          </label>
          <TooltipEducativo
            title="Link Complementar (WEB)"
            icon="🔗"
            position="auto"
          >
            <p>
              Adicione links de páginas que complementam a matéria. O conteúdo
              será extraído automaticamente.
            </p>
            <p>
              <strong>Útil para:</strong>
            </p>
            <ul>
              <li>Matérias relacionadas de outros veículos</li>
              <li>Páginas oficiais com dados adicionais</li>
              <li>Comunicados de imprensa</li>
            </ul>
            <p>Você poderá revisar e selecionar o que usar.</p>
          </TooltipEducativo>
        </div>
        <input
          type="url"
          className="w-full p-3 border border-light-gray rounded-lg"
          placeholder="https://exemplo.com/noticia..."
        />
      </div>
    </div>
  );
}
