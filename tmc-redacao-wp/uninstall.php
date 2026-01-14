<?php
/**
 * Uninstall script for TMC Redacao
 *
 * This file runs when the plugin is uninstalled (deleted) from WordPress.
 * It cleans up all data created by the plugin.
 *
 * @package TMC_Redacao
 */

// Exit if not called by WordPress uninstall
if ( ! defined( 'WP_UNINSTALL_PLUGIN' ) ) {
    exit;
}

// Delete plugin options
delete_option( 'tmc_redacao_api_url' );

// Delete any transients
delete_transient( 'tmc_redacao_cache' );

// Delete user meta (if any was stored)
// Uncomment and modify if you add user-specific data
// delete_metadata( 'user', 0, 'tmc_redacao_preferences', '', true );

// Clean up any scheduled cron jobs (if any)
$timestamp = wp_next_scheduled( 'tmc_redacao_cron_hook' );
if ( $timestamp ) {
    wp_unschedule_event( $timestamp, 'tmc_redacao_cron_hook' );
}

// Log uninstall (optional, for debugging)
if ( defined( 'WP_DEBUG' ) && WP_DEBUG ) {
    error_log( 'TMC Redacao: Plugin uninstalled and data cleaned up.' );
}
