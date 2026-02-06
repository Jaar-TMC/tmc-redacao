#!/usr/bin/env python3
"""
Script de Re-clustering para Artigos Existentes

Este script realiza o reset completo do sistema de temas semanticos e
reprocessa todos os artigos que possuem embeddings.

Fases:
1. LIMPEZA - Remove relacoes artigo-tema, desativa temas, reseta flags
2. REPROCESSAMENTO - Reclusteriza artigos com embeddings
3. RELATORIO - Gera estatisticas dos novos temas

Uso:
    python recluster_articles.py [--dry-run] [--verbose] [--batch-size N]

Variaveis de ambiente necessarias:
    SQL_SERVER, SQL_DATABASE, SQL_USERNAME, SQL_PASSWORD
"""

import os
import sys
import json
import argparse
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

# Adicionar o diretorio pai ao path para imports
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

import pymssql

# Configuracao de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class ReclusteringScript:
    """
    Script de re-clustering para artigos existentes.

    Executa em 3 fases:
    1. Limpeza de dados existentes
    2. Reprocessamento de artigos com embeddings
    3. Geracao de relatorio
    """

    def __init__(
        self,
        dry_run: bool = False,
        verbose: bool = False,
        batch_size: int = 100
    ):
        """
        Inicializa o script.

        Args:
            dry_run: Se True, simula operacoes sem alterar dados
            verbose: Se True, exibe logs detalhados
            batch_size: Tamanho do lote para processamento
        """
        self.dry_run = dry_run
        self.verbose = verbose
        self.batch_size = batch_size

        # Configuracoes de conexao
        self.server = os.environ.get('SQL_SERVER', 'bi4ia-tmc.database.windows.net')
        self.database = os.environ.get('SQL_DATABASE', 'tmc')
        self.username = os.environ.get('SQL_USERNAME', 'tmc_collector')
        self.password = os.environ.get('SQL_PASSWORD', '')

        # Estatisticas
        self.stats = {
            'article_themes_deleted': 0,
            'themes_deactivated': 0,
            'articles_reset': 0,
            'articles_with_embedding': 0,
            'articles_processed': 0,
            'themes_created': 0,
            'errors': []
        }

        if verbose:
            logger.setLevel(logging.DEBUG)

    def get_connection(self) -> pymssql.Connection:
        """Obtem conexao com o banco de dados."""
        return pymssql.connect(
            server=self.server,
            user=self.username,
            password=self.password,
            database=self.database,
            login_timeout=30,
            as_dict=False,
            charset='UTF-8'
        )

    def test_connection(self) -> bool:
        """Testa conexao com o banco."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                logger.info("Conexao com banco de dados OK")
                return True
        except Exception as e:
            logger.error(f"Falha na conexao: {e}")
            return False

    # ========================================
    # FASE 1: LIMPEZA
    # ========================================

    def phase1_cleanup(self) -> bool:
        """
        Fase 1: Limpeza dos dados existentes.

        - Deleta todas as entradas de article_themes
        - Marca todos os temas como inactive
        - Reseta has_theme/primary_theme_id nos artigos

        Returns:
            True se executou com sucesso
        """
        logger.info("=" * 60)
        logger.info("FASE 1: LIMPEZA")
        logger.info("=" * 60)

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 1.1 - Contar registros antes
                cursor.execute("SELECT COUNT(*) FROM article_themes")
                article_themes_count = cursor.fetchone()[0]
                logger.info(f"Relacoes artigo-tema existentes: {article_themes_count}")

                cursor.execute("SELECT COUNT(*) FROM themes WHERE status = 'active'")
                active_themes_count = cursor.fetchone()[0]
                logger.info(f"Temas ativos existentes: {active_themes_count}")

                if self.dry_run:
                    logger.info("[DRY-RUN] Simulando limpeza...")
                    self.stats['article_themes_deleted'] = article_themes_count
                    self.stats['themes_deactivated'] = active_themes_count
                    return True

                # 1.2 - Deletar relacoes artigo-tema
                logger.info("Deletando relacoes artigo-tema...")
                cursor.execute("DELETE FROM article_themes")
                self.stats['article_themes_deleted'] = cursor.rowcount
                logger.info(f"  Deletadas: {self.stats['article_themes_deleted']} relacoes")

                # 1.3 - Marcar temas como inactive
                logger.info("Desativando temas existentes...")
                cursor.execute("""
                    UPDATE themes
                    SET status = 'inactive',
                        last_updated_at = GETUTCDATE()
                    WHERE status = 'active'
                """)
                self.stats['themes_deactivated'] = cursor.rowcount
                logger.info(f"  Desativados: {self.stats['themes_deactivated']} temas")

                # 1.4 - Resetar flags nos artigos (se existirem as colunas)
                logger.info("Resetando flags de tema nos artigos...")
                try:
                    cursor.execute("""
                        UPDATE collected_articles
                        SET has_theme = 0,
                            primary_theme_id = NULL,
                            updated_at = GETUTCDATE()
                        WHERE has_theme = 1 OR primary_theme_id IS NOT NULL
                    """)
                    self.stats['articles_reset'] = cursor.rowcount
                    logger.info(f"  Artigos resetados: {self.stats['articles_reset']}")
                except Exception as e:
                    # Colunas podem nao existir
                    logger.warning(f"Colunas has_theme/primary_theme_id nao existem: {e}")

                conn.commit()
                logger.info("Fase 1 concluida com sucesso!")
                return True

        except Exception as e:
            logger.error(f"Erro na Fase 1: {e}")
            self.stats['errors'].append(f"Fase 1: {str(e)}")
            return False

    # ========================================
    # FASE 2: REPROCESSAMENTO
    # ========================================

    def get_articles_with_embedding(self) -> List[Dict[str, Any]]:
        """
        Busca todos os artigos que possuem embedding.

        Returns:
            Lista de dicts com id, title, preview, embedding
        """
        query = """
            SELECT
                a.id, a.title, a.preview, e.embedding, a.published_at
            FROM collected_articles a
            JOIN article_embeddings e ON a.id = e.article_id
            ORDER BY a.collected_at DESC
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()

                articles = []
                for row in rows:
                    embedding = json.loads(row[3]) if row[3] else None
                    if embedding:
                        articles.append({
                            'id': row[0],
                            'title': row[1],
                            'preview': row[2],
                            'embedding': embedding,
                            'published_at': row[4]
                        })

                return articles
        except Exception as e:
            logger.error(f"Erro ao buscar artigos com embedding: {e}")
            return []

    async def phase2_reprocess(self) -> bool:
        """
        Fase 2: Reprocessamento dos artigos com embeddings.

        Usa o ClusteringService para processar artigos em lotes.

        Returns:
            True se executou com sucesso
        """
        logger.info("=" * 60)
        logger.info("FASE 2: REPROCESSAMENTO")
        logger.info("=" * 60)

        try:
            # Buscar artigos com embedding
            logger.info("Buscando artigos com embeddings...")
            articles = self.get_articles_with_embedding()
            self.stats['articles_with_embedding'] = len(articles)
            logger.info(f"Artigos com embedding: {len(articles)}")

            if not articles:
                logger.warning("Nenhum artigo com embedding encontrado!")
                return True

            if self.dry_run:
                logger.info(f"[DRY-RUN] Simulando clustering de {len(articles)} artigos...")
                self.stats['articles_processed'] = len(articles)
                # Estimar numero de temas (aproximadamente 1 tema a cada 5-10 artigos)
                self.stats['themes_created'] = max(1, len(articles) // 7)
                return True

            # Importar ClusteringService
            from services.clustering_service import ClusteringService, CLUSTERING_SIMILARITY_THRESHOLD
            from services.database import get_db

            # Inicializar servicos
            db_service = get_db()
            clustering_service = ClusteringService(db_service)

            logger.info(f"Threshold de similaridade: {CLUSTERING_SIMILARITY_THRESHOLD}")
            logger.info(f"Processando em lotes de {self.batch_size}...")

            processed = 0
            themes_created = set()

            # Processar em lotes
            for i in range(0, len(articles), self.batch_size):
                batch = articles[i:i + self.batch_size]
                batch_num = (i // self.batch_size) + 1
                total_batches = (len(articles) + self.batch_size - 1) // self.batch_size

                logger.info(f"Processando lote {batch_num}/{total_batches} ({len(batch)} artigos)...")

                for article in batch:
                    try:
                        article_id = article['id']
                        embedding = article['embedding']
                        published_at = article.get('published_at')

                        # Encontrar melhor tema ou criar novo
                        match = clustering_service.find_best_theme(
                            embedding,
                            article_published_at=published_at
                        )

                        if match is not None:
                            # Adicionar ao tema existente
                            theme_id, similarity = match
                            success = clustering_service.add_article_to_theme(
                                article_id=UUID(str(article_id)),
                                theme_id=theme_id,
                                similarity=similarity,
                                embedding=embedding,
                                is_seed=False
                            )
                            if success:
                                processed += 1
                                if self.verbose:
                                    logger.debug(
                                        f"Artigo {article_id} -> Tema {theme_id} "
                                        f"(sim={similarity:.4f})"
                                    )
                        else:
                            # Criar novo tema
                            theme = clustering_service.create_theme(article, embedding)

                            # Adicionar artigo como seed
                            success = clustering_service.add_article_to_theme(
                                article_id=UUID(str(article_id)),
                                theme_id=theme.id,
                                similarity=1.0,
                                embedding=embedding,
                                is_seed=True
                            )
                            if success:
                                processed += 1
                                themes_created.add(str(theme.id))
                                if self.verbose:
                                    logger.debug(
                                        f"Artigo {article_id} -> Novo tema '{theme.name}' "
                                        f"(ID: {theme.id})"
                                    )

                    except Exception as e:
                        logger.warning(f"Erro ao processar artigo {article.get('id')}: {e}")
                        self.stats['errors'].append(f"Artigo {article.get('id')}: {str(e)}")

                logger.info(f"  Lote {batch_num} concluido: {processed} artigos processados")

            self.stats['articles_processed'] = processed
            self.stats['themes_created'] = len(themes_created)

            logger.info(f"Fase 2 concluida!")
            logger.info(f"  Artigos processados: {processed}")
            logger.info(f"  Temas criados: {len(themes_created)}")

            return True

        except ImportError as e:
            logger.error(f"Erro ao importar modulos: {e}")
            logger.error("Certifique-se de que o script esta sendo executado do diretorio correto")
            self.stats['errors'].append(f"Import: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Erro na Fase 2: {e}")
            self.stats['errors'].append(f"Fase 2: {str(e)}")
            return False

    # ========================================
    # FASE 3: RELATORIO
    # ========================================

    def phase3_report(self) -> Dict[str, Any]:
        """
        Fase 3: Gera relatorio com estatisticas dos temas.

        Returns:
            Dict com estatisticas completas
        """
        logger.info("=" * 60)
        logger.info("FASE 3: RELATORIO")
        logger.info("=" * 60)

        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'dry_run': self.dry_run,
            'execution_stats': self.stats.copy(),
            'theme_stats': {},
            'themes_by_size': []
        }

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Contar temas ativos
                cursor.execute("SELECT COUNT(*) FROM themes WHERE status = 'active'")
                total_themes = cursor.fetchone()[0]

                # Estatisticas de artigos por tema
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_themes,
                        AVG(CAST(article_count as FLOAT)) as avg_articles,
                        MIN(article_count) as min_articles,
                        MAX(article_count) as max_articles,
                        SUM(article_count) as total_articles
                    FROM themes
                    WHERE status = 'active'
                """)
                stats_row = cursor.fetchone()

                if stats_row and stats_row[0] > 0:
                    report['theme_stats'] = {
                        'total_themes': stats_row[0],
                        'avg_articles_per_theme': round(stats_row[1], 2) if stats_row[1] else 0,
                        'min_articles_per_theme': stats_row[2] or 0,
                        'max_articles_per_theme': stats_row[3] or 0,
                        'total_articles_in_themes': stats_row[4] or 0
                    }
                else:
                    report['theme_stats'] = {
                        'total_themes': 0,
                        'avg_articles_per_theme': 0,
                        'min_articles_per_theme': 0,
                        'max_articles_per_theme': 0,
                        'total_articles_in_themes': 0
                    }

                # Listar temas com mais de 3 artigos
                cursor.execute("""
                    SELECT id, name, slug, article_count, status, first_seen_at
                    FROM themes
                    WHERE status = 'active' AND article_count >= 3
                    ORDER BY article_count DESC
                """)
                themes_rows = cursor.fetchall()

                report['themes_by_size'] = [
                    {
                        'id': str(row[0]),
                        'name': row[1],
                        'slug': row[2],
                        'article_count': row[3],
                        'status': row[4],
                        'first_seen_at': row[5].isoformat() if row[5] else None
                    }
                    for row in themes_rows
                ]

                # Log do relatorio
                logger.info("")
                logger.info("RESUMO DO RE-CLUSTERING:")
                logger.info("-" * 40)
                logger.info(f"Modo: {'DRY-RUN (simulacao)' if self.dry_run else 'EXECUCAO REAL'}")
                logger.info("")
                logger.info("Fase 1 - Limpeza:")
                logger.info(f"  - Relacoes artigo-tema deletadas: {self.stats['article_themes_deleted']}")
                logger.info(f"  - Temas desativados: {self.stats['themes_deactivated']}")
                logger.info(f"  - Artigos resetados: {self.stats['articles_reset']}")
                logger.info("")
                logger.info("Fase 2 - Reprocessamento:")
                logger.info(f"  - Artigos com embedding: {self.stats['articles_with_embedding']}")
                logger.info(f"  - Artigos processados: {self.stats['articles_processed']}")
                logger.info(f"  - Temas criados: {self.stats['themes_created']}")
                logger.info("")
                logger.info("Estatisticas de Temas:")
                ts = report['theme_stats']
                logger.info(f"  - Total de temas ativos: {ts['total_themes']}")
                logger.info(f"  - Media de artigos por tema: {ts['avg_articles_per_theme']}")
                logger.info(f"  - Min artigos por tema: {ts['min_articles_per_theme']}")
                logger.info(f"  - Max artigos por tema: {ts['max_articles_per_theme']}")
                logger.info("")

                if report['themes_by_size']:
                    logger.info(f"Temas com 3+ artigos ({len(report['themes_by_size'])}):")
                    for theme in report['themes_by_size'][:20]:  # Top 20
                        logger.info(f"  - [{theme['article_count']:3d}] {theme['name']}")
                else:
                    logger.info("Nenhum tema com 3+ artigos encontrado")

                if self.stats['errors']:
                    logger.info("")
                    logger.warning(f"ERROS ({len(self.stats['errors'])}):")
                    for err in self.stats['errors'][:10]:
                        logger.warning(f"  - {err}")

                return report

        except Exception as e:
            logger.error(f"Erro ao gerar relatorio: {e}")
            report['error'] = str(e)
            return report

    def save_report(self, report: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """
        Salva relatorio em arquivo JSON.

        Args:
            report: Dict com dados do relatorio
            output_path: Caminho do arquivo (opcional)

        Returns:
            Caminho do arquivo salvo
        """
        if output_path is None:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            mode = 'dryrun_' if self.dry_run else ''
            output_path = os.path.join(
                script_dir,
                f'recluster_report_{mode}{timestamp}.json'
            )

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Relatorio salvo em: {output_path}")
        return output_path

    async def run(self) -> bool:
        """
        Executa o script completo de re-clustering.

        Returns:
            True se todas as fases executaram com sucesso
        """
        start_time = datetime.utcnow()

        logger.info("=" * 60)
        logger.info("SCRIPT DE RE-CLUSTERING")
        logger.info("=" * 60)
        logger.info(f"Inicio: {start_time.isoformat()}")
        logger.info(f"Modo: {'DRY-RUN' if self.dry_run else 'EXECUCAO REAL'}")
        logger.info(f"Batch size: {self.batch_size}")
        logger.info("")

        # Testar conexao
        if not self.test_connection():
            logger.error("Falha na conexao com o banco. Abortando.")
            return False

        # Fase 1: Limpeza
        if not self.phase1_cleanup():
            logger.error("Fase 1 falhou. Abortando.")
            return False

        # Fase 2: Reprocessamento
        if not await self.phase2_reprocess():
            logger.error("Fase 2 falhou. Abortando.")
            return False

        # Fase 3: Relatorio
        report = self.phase3_report()

        # Calcular duracao
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        report['duration_seconds'] = duration

        # Salvar relatorio
        self.save_report(report)

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"RE-CLUSTERING CONCLUIDO")
        logger.info(f"Duracao: {duration:.1f} segundos")
        logger.info("=" * 60)

        return len(self.stats['errors']) == 0


def main():
    """Funcao principal."""
    parser = argparse.ArgumentParser(
        description='Script de re-clustering para artigos existentes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python recluster_articles.py --dry-run          # Simula sem alterar dados
  python recluster_articles.py --verbose          # Executa com logs detalhados
  python recluster_articles.py --batch-size 50    # Processa em lotes de 50

Variaveis de ambiente necessarias:
  SQL_SERVER    - Servidor do banco (default: bi4ia-tmc.database.windows.net)
  SQL_DATABASE  - Nome do banco (default: tmc)
  SQL_USERNAME  - Usuario (default: tmc_collector)
  SQL_PASSWORD  - Senha (obrigatorio)
        """
    )

    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Simula operacoes sem alterar dados no banco'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Exibe logs detalhados durante execucao'
    )

    parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=100,
        help='Tamanho do lote para processamento (default: 100)'
    )

    args = parser.parse_args()

    # Verificar senha
    if not os.environ.get('SQL_PASSWORD'):
        logger.error("Variavel SQL_PASSWORD nao definida!")
        logger.error("Defina a variavel de ambiente antes de executar:")
        logger.error("  export SQL_PASSWORD='sua_senha'")
        sys.exit(1)

    # Criar e executar script
    script = ReclusteringScript(
        dry_run=args.dry_run,
        verbose=args.verbose,
        batch_size=args.batch_size
    )

    # Executar async
    success = asyncio.run(script.run())

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
