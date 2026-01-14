<?php
/**
 * Asset management for TMC Redacao
 *
 * @package TMC_Redacao
 */

// Prevent direct access
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

/**
 * Assets class
 */
class TMC_Redacao_Assets {

    /**
     * Instance
     *
     * @var TMC_Redacao_Assets|null
     */
    private static $instance = null;

    /**
     * Get instance
     *
     * @return TMC_Redacao_Assets
     */
    public static function get_instance() {
        if ( null === self::$instance ) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    /**
     * Constructor
     */
    private function __construct() {
        add_action( 'admin_enqueue_scripts', array( $this, 'enqueue_assets' ) );
    }

    /**
     * Enqueue scripts and styles
     *
     * @param string $hook Current admin page hook.
     */
    public function enqueue_assets( $hook ) {
        // Only load on our plugin pages
        if ( ! $this->is_plugin_page( $hook ) ) {
            return;
        }

        // Enqueue the React app styles
        wp_enqueue_style(
            'tmc-redacao-app',
            TMC_REDACAO_PLUGIN_URL . 'assets/css/tmc-redacao.css',
            array(),
            TMC_REDACAO_VERSION
        );

        // Enqueue the React app script
        wp_enqueue_script(
            'tmc-redacao-app',
            TMC_REDACAO_PLUGIN_URL . 'assets/js/tmc-redacao.js',
            array(),
            TMC_REDACAO_VERSION,
            true // Load in footer
        );

        // Pass configuration to React app
        wp_localize_script(
            'tmc-redacao-app',
            'tmcRedacaoConfig',
            $this->get_script_config()
        );
    }

    /**
     * Check if current page is a plugin page
     *
     * @param string $hook Current admin page hook.
     * @return bool
     */
    private function is_plugin_page( $hook ) {
        $plugin_pages = array(
            'toplevel_page_' . TMC_Redacao_Admin::MENU_SLUG,
            'tmc-redacao_page_' . TMC_Redacao_Admin::SETTINGS_SLUG,
        );

        return in_array( $hook, $plugin_pages, true );
    }

    /**
     * Get script configuration
     *
     * @return array
     */
    private function get_script_config() {
        return array(
            'user'       => TMC_Redacao_Admin::get_user_data(),
            'apiBaseUrl' => get_option( 'tmc_redacao_api_url', '' ),
            'nonce'      => wp_create_nonce( 'tmc_redacao_nonce' ),
            'restNonce'  => wp_create_nonce( 'wp_rest' ),
            'pluginUrl'  => TMC_REDACAO_PLUGIN_URL,
            'isWordPress' => true,
            'adminUrl'   => admin_url(),
            'siteUrl'    => site_url(),
        );
    }
}
