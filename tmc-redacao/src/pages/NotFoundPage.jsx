export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <h1 className="text-4xl font-bold text-gray-800 mb-4">404</h1>
      <p className="text-lg text-gray-600 mb-6">Página não encontrada</p>
      <a href="/" className="text-blue-600 hover:text-blue-800 underline">
        Voltar para a página inicial
      </a>
    </div>
  );
}
