<?php
/**
 * Admin page view - React app container
 *
 * @package TMC_Redacao
 */

// Prevent direct access
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

// Double-check capability
if ( ! current_user_can( 'edit_posts' ) ) {
    wp_die( esc_html__( 'Acesso negado.', 'tmc-redacao' ), 403 );
}
?>
<div class="wrap tmc-redacao-wrap">
    <?php
    // Check if API URL is configured
    $api_url = get_option( 'tmc_redacao_api_url', '' );
    if ( empty( $api_url ) ) :
    ?>
        <div class="notice notice-warning">
            <p>
                <strong><?php esc_html_e( 'Configuracao necessaria:', 'tmc-redacao' ); ?></strong>
                <?php
                printf(
                    /* translators: %s: Link to settings page */
                    esc_html__( 'Por favor, configure a URL da API nas %s antes de usar a ferramenta.', 'tmc-redacao' ),
                    '<a href="' . esc_url( admin_url( 'admin.php?page=tmc-redacao-settings' ) ) . '">' . esc_html__( 'configuracoes', 'tmc-redacao' ) . '</a>'
                );
                ?>
            </p>
        </div>
    <?php endif; ?>

    <!-- React App Root -->
    <div id="tmc-redacao-root" class="tmc-app">
        <!-- Loading state while React loads -->
        <div class="tmc-loading" style="display: flex; align-items: center; justify-content: center; min-height: 400px; flex-direction: column; gap: 16px;">
            <div class="tmc-loading-spinner" style="width: 40px; height: 40px; border: 3px solid #f3f3f3; border-top: 3px solid #FF6B00; border-radius: 50%; animation: tmc-spin 1s linear infinite;"></div>
            <p style="color: #666; font-size: 14px;"><?php esc_html_e( 'Carregando TMC Redacao...', 'tmc-redacao' ); ?></p>
        </div>
    </div>

    <style>
        @keyframes tmc-spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* Hide WordPress notices inside our app */
        .tmc-redacao-wrap > .notice:not(.notice-warning) {
            display: none;
        }

        /* Ensure our app has proper isolation from WP admin */
        .tmc-redacao-wrap {
            margin-left: -20px;
            margin-right: -20px;
            margin-top: -10px;
        }

        /* Compensate for WordPress admin bar */
        @media screen and (min-width: 783px) {
            .tmc-app {
                margin-top: 0;
            }
        }
    </style>
</div>
