<?php
/**
 * Settings page view
 *
 * @package TMC_Redacao
 */

// Prevent direct access
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

// Double-check capability
if ( ! current_user_can( 'manage_options' ) ) {
    wp_die( esc_html__( 'Acesso negado.', 'tmc-redacao' ), 403 );
}
?>
<div class="wrap">
    <h1><?php esc_html_e( 'TMC Redacao - Configuracoes', 'tmc-redacao' ); ?></h1>

    <?php settings_errors( 'tmc_redacao_settings' ); ?>

    <form method="post" action="options.php">
        <?php
        settings_fields( 'tmc_redacao_settings' );
        do_settings_sections( TMC_Redacao_Admin::SETTINGS_SLUG );
        submit_button( __( 'Salvar Configuracoes', 'tmc-redacao' ) );
        ?>
    </form>

    <hr />

    <h2><?php esc_html_e( 'Informacoes do Sistema', 'tmc-redacao' ); ?></h2>
    <table class="widefat" style="max-width: 600px;">
        <tbody>
            <tr>
                <td><strong><?php esc_html_e( 'Versao do Plugin', 'tmc-redacao' ); ?></strong></td>
                <td><?php echo esc_html( TMC_REDACAO_VERSION ); ?></td>
            </tr>
            <tr>
                <td><strong><?php esc_html_e( 'Versao do WordPress', 'tmc-redacao' ); ?></strong></td>
                <td><?php echo esc_html( get_bloginfo( 'version' ) ); ?></td>
            </tr>
            <tr>
                <td><strong><?php esc_html_e( 'Versao do PHP', 'tmc-redacao' ); ?></strong></td>
                <td><?php echo esc_html( phpversion() ); ?></td>
            </tr>
            <tr>
                <td><strong><?php esc_html_e( 'Status da API', 'tmc-redacao' ); ?></strong></td>
                <td>
                    <?php
                    $api_url = get_option( 'tmc_redacao_api_url', '' );
                    if ( empty( $api_url ) ) {
                        echo '<span style="color: #dc3232;">' . esc_html__( 'Nao configurada', 'tmc-redacao' ) . '</span>';
                    } else {
                        echo '<span style="color: #46b450;">' . esc_html__( 'Configurada', 'tmc-redacao' ) . '</span>';
                    }
                    ?>
                </td>
            </tr>
        </tbody>
    </table>

    <h3><?php esc_html_e( 'Teste de Conexao', 'tmc-redacao' ); ?></h3>
    <p>
        <button type="button" id="tmc-test-api" class="button button-secondary" <?php echo empty( $api_url ) ? 'disabled' : ''; ?>>
            <?php esc_html_e( 'Testar Conexao com API', 'tmc-redacao' ); ?>
        </button>
        <span id="tmc-test-result" style="margin-left: 10px;"></span>
    </p>

    <script>
        document.getElementById('tmc-test-api')?.addEventListener('click', async function() {
            const resultEl = document.getElementById('tmc-test-result');
            const apiUrl = '<?php echo esc_js( $api_url ); ?>';

            if (!apiUrl) {
                resultEl.innerHTML = '<span style="color: #dc3232;">URL da API nao configurada</span>';
                return;
            }

            resultEl.innerHTML = '<span style="color: #666;">Testando...</span>';

            try {
                const response = await fetch(apiUrl + '/health', {
                    method: 'GET',
                    headers: { 'Content-Type': 'application/json' }
                });

                if (response.ok) {
                    const data = await response.json();
                    resultEl.innerHTML = '<span style="color: #46b450;">Conexao OK - ' + (data.status || 'healthy') + '</span>';
                } else {
                    resultEl.innerHTML = '<span style="color: #dc3232;">Erro: HTTP ' + response.status + '</span>';
                }
            } catch (error) {
                resultEl.innerHTML = '<span style="color: #dc3232;">Erro de conexao: ' + error.message + '</span>';
            }
        });
    </script>
</div>
