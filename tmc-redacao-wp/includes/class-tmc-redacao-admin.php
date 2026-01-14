<?php
/**
 * Admin functionality for TMC Redacao
 *
 * @package TMC_Redacao
 */

// Prevent direct access
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

/**
 * Admin class
 */
class TMC_Redacao_Admin {

    /**
     * Instance
     *
     * @var TMC_Redacao_Admin|null
     */
    private static $instance = null;

    /**
     * Menu slug for the main page
     *
     * @var string
     */
    const MENU_SLUG = 'tmc-redacao';

    /**
     * Menu slug for the settings page
     *
     * @var string
     */
    const SETTINGS_SLUG = 'tmc-redacao-settings';

    /**
     * Required capability
     *
     * @var string
     */
    const REQUIRED_CAPABILITY = 'edit_posts';

    /**
     * Get instance
     *
     * @return TMC_Redacao_Admin
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
        add_action( 'admin_menu', array( $this, 'register_admin_menu' ) );
        add_action( 'admin_init', array( $this, 'register_settings' ) );
    }

    /**
     * Register admin menu
     */
    public function register_admin_menu() {
        // Main menu page (React app)
        add_menu_page(
            __( 'TMC Redacao', 'tmc-redacao' ),
            __( 'TMC Redacao', 'tmc-redacao' ),
            self::REQUIRED_CAPABILITY,
            self::MENU_SLUG,
            array( $this, 'render_admin_page' ),
            'dashicons-edit-page',
            30
        );

        // Settings submenu
        add_submenu_page(
            self::MENU_SLUG,
            __( 'Configuracoes', 'tmc-redacao' ),
            __( 'Configuracoes', 'tmc-redacao' ),
            'manage_options',
            self::SETTINGS_SLUG,
            array( $this, 'render_settings_page' )
        );
    }

    /**
     * Register plugin settings
     */
    public function register_settings() {
        // Register settings
        register_setting(
            'tmc_redacao_settings',
            'tmc_redacao_api_url',
            array(
                'type'              => 'string',
                'sanitize_callback' => 'esc_url_raw',
                'default'           => '',
            )
        );

        // Add settings section
        add_settings_section(
            'tmc_redacao_api_section',
            __( 'Configuracoes da API', 'tmc-redacao' ),
            array( $this, 'render_api_section' ),
            self::SETTINGS_SLUG
        );

        // Add API URL field
        add_settings_field(
            'tmc_redacao_api_url',
            __( 'URL da API', 'tmc-redacao' ),
            array( $this, 'render_api_url_field' ),
            self::SETTINGS_SLUG,
            'tmc_redacao_api_section'
        );
    }

    /**
     * Render main admin page (React app container)
     */
    public function render_admin_page() {
        // Check capability
        if ( ! current_user_can( self::REQUIRED_CAPABILITY ) ) {
            wp_die(
                esc_html__( 'Voce nao tem permissao para acessar esta pagina.', 'tmc-redacao' ),
                403
            );
        }

        // Include the view
        include TMC_REDACAO_PLUGIN_DIR . 'views/admin-page.php';
    }

    /**
     * Render settings page
     */
    public function render_settings_page() {
        // Check capability
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_die(
                esc_html__( 'Voce nao tem permissao para acessar esta pagina.', 'tmc-redacao' ),
                403
            );
        }

        // Include the view
        include TMC_REDACAO_PLUGIN_DIR . 'views/settings-page.php';
    }

    /**
     * Render API section description
     */
    public function render_api_section() {
        echo '<p>' . esc_html__( 'Configure a URL da API do Azure Functions para conectar com o backend.', 'tmc-redacao' ) . '</p>';
    }

    /**
     * Render API URL field
     */
    public function render_api_url_field() {
        $api_url = get_option( 'tmc_redacao_api_url', '' );
        ?>
        <input
            type="url"
            id="tmc_redacao_api_url"
            name="tmc_redacao_api_url"
            value="<?php echo esc_attr( $api_url ); ?>"
            class="regular-text"
            placeholder="https://your-function-app.azurewebsites.net/api"
        />
        <p class="description">
            <?php esc_html_e( 'Exemplo: https://tmc-redacao-api.azurewebsites.net/api', 'tmc-redacao' ); ?>
        </p>
        <?php
    }

    /**
     * Get current user data for React app
     *
     * @return array
     */
    public static function get_user_data() {
        $current_user = wp_get_current_user();

        return array(
            'id'          => $current_user->ID,
            'displayName' => $current_user->display_name,
            'email'       => $current_user->user_email,
            'roles'       => $current_user->roles,
            'avatar'      => get_avatar_url( $current_user->ID, array( 'size' => 96 ) ),
        );
    }
}
