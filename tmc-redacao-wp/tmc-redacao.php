<?php
/**
 * Plugin Name: TMC Redacao (TEST)
 * Plugin URI: https://tmc.com.br
 * Description: Ferramenta de redacao jornalistica com IA para o portal TMC.
 * Version: 1.2.0-test
 * Requires at least: 6.0
 * Requires PHP: 8.0
 * Author: TMC / JaarConsult
 * Author URI: https://jaarconsult.com.br
 * License: GPL v2 or later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain: tmc-redacao
 * Domain Path: /languages
 *
 * @package TMC_Redacao
 */

// Prevent direct access
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

// Plugin constants
define( 'TMC_REDACAO_VERSION', '1.2.0-test' );
define( 'TMC_REDACAO_PLUGIN_DIR', plugin_dir_path( __FILE__ ) );
define( 'TMC_REDACAO_PLUGIN_URL', plugin_dir_url( __FILE__ ) );
define( 'TMC_REDACAO_PLUGIN_BASENAME', plugin_basename( __FILE__ ) );

/**
 * Main plugin class
 */
final class TMC_Redacao {

    /**
     * Plugin instance
     *
     * @var TMC_Redacao|null
     */
    private static $instance = null;

    /**
     * Get plugin instance
     *
     * @return TMC_Redacao
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
        $this->load_dependencies();
        $this->init_hooks();
    }

    /**
     * Load required files
     */
    private function load_dependencies() {
        require_once TMC_REDACAO_PLUGIN_DIR . 'includes/class-tmc-redacao-admin.php';
        require_once TMC_REDACAO_PLUGIN_DIR . 'includes/class-tmc-redacao-assets.php';
    }

    /**
     * Initialize hooks
     */
    private function init_hooks() {
        // Initialize admin functionality
        if ( is_admin() ) {
            TMC_Redacao_Admin::get_instance();
            TMC_Redacao_Assets::get_instance();
        }

        // Load text domain
        add_action( 'init', array( $this, 'load_textdomain' ) );

        // Plugin activation/deactivation
        register_activation_hook( __FILE__, array( $this, 'activate' ) );
        register_deactivation_hook( __FILE__, array( $this, 'deactivate' ) );
    }

    /**
     * Load plugin text domain
     */
    public function load_textdomain() {
        load_plugin_textdomain(
            'tmc-redacao',
            false,
            dirname( TMC_REDACAO_PLUGIN_BASENAME ) . '/languages'
        );
    }

    /**
     * Plugin activation
     */
    public function activate() {
        // Set default options
        if ( false === get_option( 'tmc_redacao_api_url' ) ) {
            add_option( 'tmc_redacao_api_url', '' );
        }

        // Flush rewrite rules
        flush_rewrite_rules();
    }

    /**
     * Plugin deactivation
     */
    public function deactivate() {
        // Clean up transients
        delete_transient( 'tmc_redacao_cache' );
    }
}

/**
 * Initialize the plugin
 *
 * @return TMC_Redacao
 */
function tmc_redacao() {
    return TMC_Redacao::get_instance();
}

// Start the plugin
tmc_redacao();
