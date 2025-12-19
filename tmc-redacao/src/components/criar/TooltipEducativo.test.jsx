import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import TooltipEducativo from './TooltipEducativo';

describe('TooltipEducativo', () => {
  it('deve renderizar o botão de ajuda', () => {
    render(
      <TooltipEducativo title="Título de Teste" icon="📝">
        <p>Conteúdo de teste</p>
      </TooltipEducativo>
    );

    const button = screen.getByLabelText('Ajuda: Título de Teste');
    expect(button).toBeInTheDocument();
  });

  it('deve abrir o tooltip ao clicar no botão', async () => {
    render(
      <TooltipEducativo title="Título de Teste" icon="📝">
        <p>Conteúdo de teste</p>
      </TooltipEducativo>
    );

    const button = screen.getByLabelText('Ajuda: Título de Teste');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('TÍTULO DE TESTE')).toBeInTheDocument();
      expect(screen.getByText('Conteúdo de teste')).toBeInTheDocument();
    });
  });

  it('deve fechar o tooltip ao clicar no X', async () => {
    render(
      <TooltipEducativo title="Título de Teste" icon="📝">
        <p>Conteúdo de teste</p>
      </TooltipEducativo>
    );

    // Abrir
    const button = screen.getByLabelText('Ajuda: Título de Teste');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    // Fechar
    const closeButton = screen.getByLabelText('Fechar tooltip');
    fireEvent.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('deve fechar o tooltip ao pressionar Escape', async () => {
    render(
      <TooltipEducativo title="Título de Teste" icon="📝">
        <p>Conteúdo de teste</p>
      </TooltipEducativo>
    );

    // Abrir
    const button = screen.getByLabelText('Ajuda: Título de Teste');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    // Fechar com Escape
    fireEvent.keyDown(document, { key: 'Escape' });

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('deve exibir o ícone quando fornecido', async () => {
    render(
      <TooltipEducativo title="Título de Teste" icon="📝">
        <p>Conteúdo de teste</p>
      </TooltipEducativo>
    );

    const button = screen.getByLabelText('Ajuda: Título de Teste');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText('📝')).toBeInTheDocument();
    });
  });

  it('deve aceitar conteúdo JSX complexo', async () => {
    render(
      <TooltipEducativo title="Título de Teste" icon="📝">
        <p>Parágrafo 1</p>
        <ul>
          <li>Item 1</li>
          <li>Item 2</li>
        </ul>
        <p>Parágrafo 2</p>
      </TooltipEducativo>
    );

    const button = screen.getByLabelText('Ajuda: Título de Teste');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText('Parágrafo 1')).toBeInTheDocument();
      expect(screen.getByText('Item 1')).toBeInTheDocument();
      expect(screen.getByText('Item 2')).toBeInTheDocument();
      expect(screen.getByText('Parágrafo 2')).toBeInTheDocument();
    });
  });

  it('deve ter aria-expanded correto', async () => {
    render(
      <TooltipEducativo title="Título de Teste" icon="📝">
        <p>Conteúdo de teste</p>
      </TooltipEducativo>
    );

    const button = screen.getByLabelText('Ajuda: Título de Teste');

    // Inicialmente fechado
    expect(button).toHaveAttribute('aria-expanded', 'false');

    // Abrir
    fireEvent.click(button);

    await waitFor(() => {
      expect(button).toHaveAttribute('aria-expanded', 'true');
    });
  });

  it('deve fechar ao clicar fora do tooltip', async () => {
    render(
      <div>
        <TooltipEducativo title="Título de Teste" icon="📝">
          <p>Conteúdo de teste</p>
        </TooltipEducativo>
        <div data-testid="outside">Elemento externo</div>
      </div>
    );

    // Abrir
    const button = screen.getByLabelText('Ajuda: Título de Teste');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    // Clicar fora
    const outside = screen.getByTestId('outside');
    fireEvent.mouseDown(outside);

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('deve aplicar className customizado', () => {
    render(
      <TooltipEducativo
        title="Título de Teste"
        icon="📝"
        className="custom-class"
      >
        <p>Conteúdo de teste</p>
      </TooltipEducativo>
    );

    const container = screen.getByLabelText('Ajuda: Título de Teste').parentElement;
    expect(container).toHaveClass('custom-class');
  });

  it('deve retornar foco ao botão ao fechar', async () => {
    render(
      <TooltipEducativo title="Título de Teste" icon="📝">
        <p>Conteúdo de teste</p>
      </TooltipEducativo>
    );

    const button = screen.getByLabelText('Ajuda: Título de Teste');

    // Abrir
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    // Fechar
    const closeButton = screen.getByLabelText('Fechar tooltip');
    fireEvent.click(closeButton);

    await waitFor(() => {
      expect(document.activeElement).toBe(button);
    });
  });
});
