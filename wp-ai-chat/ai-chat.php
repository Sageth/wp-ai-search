<?php
/*
 * Plugin Name: AI Search Assistant
 * Plugin URI: https://camdenhistory.com
 * Description: AI Search using ChatGPT
 * Author: Sage Russell
 * Author URI: https://camdenhistory.com
 * Version: 0.1.0

*/

function wp_ai_chat_enqueue_assets() {
    if (is_singular() && has_shortcode(get_post()->post_content, 'ai_chat')) {
        wp_enqueue_script(
            'wp-ai-chat-js',
            plugin_dir_url(__FILE__) . 'js/ai-chat.js',
            array(),
            '1.0',
            true
        );
        wp_enqueue_style(
            'wp-ai-chat-css',
            plugin_dir_url(__FILE__) . 'css/ai-chat.css',
            array(),
            '1.0'
        );
    }
}
add_action('wp_enqueue_scripts', 'wp_ai_chat_enqueue_assets');

function wp_ai_chat_shortcode() {
    ob_start(); ?>
    <div id="ai-chat-container">
        <div id="ai-chat-messages"></div>
        <div id="ai-typing" style="display:none;">💬 Typing...</div>
        <div id="ai-chat-input">
            <input type="text" id="ai-query" placeholder="Ask me anything..." />
            <button id="ai-submit">Ask</button>
        </div>
    </div>
    <?php
    return ob_get_clean();
}
add_shortcode('ai_chat', 'wp_ai_chat_shortcode');