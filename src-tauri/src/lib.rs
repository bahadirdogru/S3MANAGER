mod commands;
mod config;
mod error;
mod metadata;
mod s3;
mod transfers;

use tauri::Manager;
use tauri_plugin_log::{Target, TargetKind};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let state = commands::AppState::new();
    let log_dir = state.settings.dir.clone();

    tauri::Builder::default()
        .plugin(
            tauri_plugin_log::Builder::new()
                .level(if cfg!(debug_assertions) { log::LevelFilter::Debug } else { log::LevelFilter::Info })
                // Keep third-party HTTP/SDK noise out of the user-visible log.
                .level_for("aws_smithy_runtime", log::LevelFilter::Warn)
                .level_for("aws_sdk_s3", log::LevelFilter::Warn)
                .level_for("hyper_util", log::LevelFilter::Warn)
                .level_for("rustls", log::LevelFilter::Warn)
                .targets([
                    Target::new(TargetKind::Stdout),
                    Target::new(TargetKind::Folder { path: log_dir, file_name: Some("app".into()) }),
                ])
                .max_file_size(2_000_000)
                .build(),
        )
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_opener::init())
        .manage(state)
        .invoke_handler(tauri::generate_handler![
            commands::get_startup,
            commands::default_endpoint,
            commands::connect,
            commands::disconnect,
            commands::ping,
            commands::list_page,
            commands::get_acls,
            commands::set_acl,
            commands::object_info,
            commands::update_metadata,
            commands::preview,
            commands::create_folder,
            commands::delete_items,
            commands::copy_item,
            commands::move_item,
            commands::rename_item,
            commands::share_link,
            commands::expand_upload,
            commands::start_upload,
            commands::start_download,
            commands::cancel_transfer,
            commands::cancel_all_transfers,
            commands::active_transfers,
            commands::list_multipart,
            commands::abort_multipart,
            commands::get_upload_metadata,
            commands::save_upload_metadata,
            commands::save_theme,
            commands::check_update,
            commands::dismiss_update,
            commands::read_log,
        ])
        .on_window_event(|window, event| {
            // Stop in-flight transfers (and abort their multipart uploads) on close.
            if let tauri::WindowEvent::Destroyed = event {
                window.app_handle().state::<commands::AppState>().transfers.cancel_all();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running S3MANAGER");
}
