use std::sync::Arc;
use teloxide::prelude::*;
use teloxide::types::{InlineKeyboardButton, InlineKeyboardMarkup, Message, ParseMode};
use teloxide::utils::command::BotCommands;

use crate::ai::AiReceiver;
use crate::media_engine::{LoopMode, MediaEngine};
use crate::router::{MusicRouter, Platform, Track, TrackResolver, UrlResolver, VideoResolver};

pub fn escape_html(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
}

pub fn format_time(secs: u64) -> String {
    format!("{:02}:{:02}", secs / 60, secs % 60)
}

pub struct SoulKingUI;

impl SoulKingUI {
    pub fn build_progress_bar(current_secs: u64, total_secs: u64, length: usize) -> String {
        if total_secs == 0 {
            return format!("[{}{}] 00:00 / 00:00", "▓".repeat(length / 2), "░".repeat(length - length / 2));
        }

        let progress = (current_secs as f64 / total_secs as f64).min(1.0);
        let filled = (progress * length as f64).round() as usize;
        let empty = length.saturating_sub(filled);

        format!(
            "▶ [{}{}] {} / {}",
            "▓".repeat(filled),
            "░".repeat(empty),
            format_time(current_secs),
            format_time(total_secs)
        )
    }

    pub fn format_now_playing(
        track: &Track,
        current_secs: u64,
        is_paused: bool,
        loop_mode: &LoopMode,
        voice_state: crate::media_engine::VoiceState,
        queue: &[Track],
    ) -> String {
        let status = if is_paused { "⏸️ PAUSED" } else { "🎸 PERFORMING LIVE" };
        let loop_status = match loop_mode {
            LoopMode::Off => "Off ➡️",
            LoopMode::Track => "Repeat Track 🔂",
            LoopMode::Queue => "Repeat Setlist 🔁",
        };

        let progress = Self::build_progress_bar(current_secs, track.duration_secs, 14);
        let artist_str = track.artist.as_deref().unwrap_or("Unknown Artist");

        let mut queue_preview = String::new();
        if !queue.is_empty() {
            queue_preview.push_str("\n\n<b>📜 UP NEXT IN QUEUE:</b>\n");
            for (i, t) in queue.iter().take(3).enumerate() {
                queue_preview.push_str(&format!(
                    "  {}. <code>{}</code>\n",
                    i + 1,
                    escape_html(&t.title)
                ));
            }
            if queue.len() > 3 {
                queue_preview.push_str(&format!("  <i>...and {} more</i>\n", queue.len() - 3));
            }
        }

        format!(
            "☠️ <b>SOUL KING CONCERT STAGE</b> ☠️\n\
             ──────────────────────────────\n\
             <blockquote>\
             🎵 <b>Track:</b> <code>{title}</code>\n\
             🎙️ <b>Artist:</b> {artist}\n\
             👑 <b>Requested by:</b> {requested}\n\
             📻 <b>Source:</b> {source:?}\n\
             🔊 <b>Voice Chat:</b> {voice_state}\n\
             ⏱️ <b>Time:</b> <code>{cur} / {tot}</code>\n\
             🔁 <b>Loop:</b> {loop_status}   ⚡ <b>Status:</b> {status}\n\n\
             {progress}\
             {queue_preview}\
             </blockquote>\n\
             <i>🎻 Yohohoho! Binks' Sake! Feel it in your bones! 🎻</i>",
            title = escape_html(&track.title),
            artist = escape_html(artist_str),
            requested = escape_html(&track.requested_by_name),
            source = track.source,
            voice_state = voice_state.display_text(),
            cur = format_time(current_secs),
            tot = format_time(track.duration_secs),
            loop_status = loop_status,
            status = status,
            progress = progress,
            queue_preview = queue_preview,
        )
    }

    pub fn format_enqueued(track: &Track, pos: usize) -> String {
        format!(
            "🎵 <b>Added to Setlist (Position #{pos})!</b>\n\
             ──────────────────────────────\n\
             <blockquote>\
             <code>{title}</code> — {artist}\n\
             Requested by: {requested}\
             </blockquote>",
            pos = pos,
            title = escape_html(&track.title),
            artist = escape_html(track.artist.as_deref().unwrap_or("Unknown Artist")),
            requested = escape_html(&track.requested_by_name)
        )
    }

    pub fn now_playing_keyboard(is_paused: bool) -> InlineKeyboardMarkup {
        let pause_btn = if is_paused {
            InlineKeyboardButton::callback("▶️ Resume", "cb_toggle_pause")
        } else {
            InlineKeyboardButton::callback("⏸️ Pause", "cb_toggle_pause")
        };
        let row1 = vec![
            pause_btn,
            InlineKeyboardButton::callback("⏭️ Skip", "cb_skip"),
            InlineKeyboardButton::callback("⏹️ Stop", "cb_stop"),
        ];
        let row2 = vec![
            InlineKeyboardButton::callback("🔄 Loop", "cb_loop"),
            InlineKeyboardButton::callback("🔀 Shuffle", "cb_shuffle"),
        ];
        InlineKeyboardMarkup::new(vec![row1, row2])
    }

    pub fn format_queue(current: Option<&Track>, queue: &[Track], _loop_mode: &LoopMode) -> String {
        let mut out = String::from(
            "☠️ <b>BROOK'S CONCERT SETLIST</b> ☠️\n\
             ──────────────────────────────\n\
             <blockquote>",
        );

        match current {
            Some(curr) => {
                out.push_str(&format!(
                    "▶️ <b>Now Playing:</b> <code>{}</code>\n   👤 {}\n\n",
                    escape_html(&curr.title),
                    escape_html(&curr.requested_by_name)
                ));
            }
            None => {
                out.push_str("⏸️ Stage is idle.\n\n");
            }
        }

        if queue.is_empty() {
            out.push_str("<i>(No upcoming tracks queued)</i>");
        } else {
            out.push_str("<b>Upcoming Tracks:</b>\n");
            for (i, t) in queue.iter().enumerate().take(10) {
                out.push_str(&format!(
                    "{}. <code>{}</code> — {}\n",
                    i + 1,
                    escape_html(&t.title),
                    escape_html(&t.requested_by_name)
                ));
            }
            if queue.len() > 10 {
                out.push_str(&format!("\n<i>...and {} more</i>", queue.len() - 10));
            }
        }

        out.push_str(
            "</blockquote>\n\
             <i>🎻 Yohohoho! The setlist never ends! 🎻</i>",
        );
        out
    }

    pub fn format_start(name: &str) -> String {
        format!(
            "☠️ <b>YOHOHOHO!</b> Welcome, <b>{name}</b>! ☠️\n\
             ──────────────────────────────\n\
             <blockquote>\
             🎻 I'm <b>Soul King Brook</b>, the musician of the Straw Hat Pirates!\n\n\
             🎵 Play your favorite tunes, vibe to any mood, and let your soul\n\
             dance to Binks' Sake!\n\n\
             💡 Start with <code>/help</code> or jump straight in with <code>/play &lt;song name&gt;</code>.\
             </blockquote>\n\
             <i>🎻 Yohohoho! SKULL JOKE! 🎻</i>",
            name = escape_html(name)
        )
    }

    pub fn format_help() -> String {
        "☠️ <b>SOUL KING COMMAND MENU</b> ☠️\n\
         ──────────────────────────────\n\
         <blockquote>\
         /play &lt;query/URL&gt; — Play music track (title goes to AI Receiver -> Router)\n\
         /vplay &lt;query/URL&gt; — Play video track (goes to Video Resolver)\n\
         /pause — Pause playback\n\
         /resume — Resume playback\n\
         /skip — Skip current track\n\
         /prev — Play previous track\n\
         /stop — Stop playback & clear stage\n\
         /seek &lt;secs&gt; — Seek to position\n\
         /volume &lt;0-200&gt; — Set volume\n\
         /queue — View queue setlist\n\
         /now — View now playing card\n\
         /loop — Toggle loop mode\n\
         /shuffle — Shuffle queue\n\
         </blockquote>".to_string()
    }
}

#[allow(dead_code)]
pub struct PermissionManager {
    pub owner_id: Option<i64>,
}

#[allow(dead_code)]
impl PermissionManager {
    pub fn new(owner_id: Option<i64>) -> Self {
        Self { owner_id }
    }

    pub fn is_owner(&self, user_id: i64) -> bool {
        self.owner_id.map(|id| id == user_id).unwrap_or(false)
    }
}

#[derive(BotCommands, Clone, Debug)]
#[command(description = "Soul King Bot Commands:")]
pub enum BotCommand {
    #[command(description = "Start the bot", rename = "start")]
    Start,
    #[command(description = "Show help menu", rename = "help")]
    Help,
    #[command(description = "Play audio title or URL", rename = "play")]
    Play(String),
    #[command(description = "Play video title or URL", rename = "vplay")]
    Vplay(String),
    #[command(description = "Pause playback", rename = "pause")]
    Pause,
    #[command(description = "Resume playback", rename = "resume")]
    Resume,
    #[command(description = "Skip current track", rename = "skip")]
    Skip,
    #[command(description = "Play previous track", rename = "prev")]
    Prev,
    #[command(description = "Stop playback & clear queue", rename = "stop")]
    Stop,
    #[command(description = "Seek position in seconds", rename = "seek")]
    Seek(u64),
    #[command(description = "Set volume level (1-100)", rename = "volume")]
    Volume(u32),
    #[command(description = "Show current queue", rename = "queue")]
    Queue,
    #[command(description = "Show currently playing track", rename = "now")]
    Now,
    #[command(description = "Cycle loop mode", rename = "loop")]
    Loop,
    #[command(description = "Shuffle queue", rename = "shuffle")]
    Shuffle,
    #[command(description = "Show player debug diagnostics", rename = "playerdebug")]
    PlayerDebug,
}

pub async fn handle_command(
    bot: Bot,
    msg: Message,
    cmd: BotCommand,
    ai: Arc<AiReceiver>,
    router: Arc<MusicRouter>,
    url_resolver: Arc<UrlResolver>,
    video_resolver: Arc<VideoResolver>,
    media_engine: Arc<MediaEngine>,
) -> anyhow::Result<()> {
    let chat_id = msg.chat.id.0;
    let _ = media_engine.reconcile_session(chat_id).await;
    let user_id = msg.from.as_ref().map(|u| u.id.0 as i64).unwrap_or(0);
    let user_name = msg.from.as_ref().map(|u| u.first_name.clone()).unwrap_or_else(|| "User".into());

    match cmd {
        BotCommand::Start => {
            let text = SoulKingUI::format_start(&user_name);
            bot.send_message(msg.chat.id, text).parse_mode(ParseMode::Html).await?;
        }
        BotCommand::Help => {
            let text = SoulKingUI::format_help();
            bot.send_message(msg.chat.id, text).parse_mode(ParseMode::Html).await?;
        }
        BotCommand::Play(query) => {
            if query.trim().is_empty() {
                bot.send_message(msg.chat.id, "Please specify a song title or URL e.g. <code>/play Binks Sake</code>").parse_mode(ParseMode::Html).await?;
                return Ok(());
            }

            let track_result = if Platform::from_url(&query).is_some() {
                // Route Path: /play URL -> URL Resolver
                url_resolver.resolve_url(&query, user_id, &user_name).await
            } else {
                // Route Path: /play title -> AI Receiver -> Music Router -> Providers
                let processed_query = ai.process_query(&query).await?;
                router.search(&processed_query, user_id, &user_name).await
            };

            match track_result {
                Ok(track) => {
                    let pb_state = media_engine.state(chat_id).await?;
                    let is_connected_and_playing = pb_state.voice_state == crate::media_engine::VoiceState::Connected
                        && pb_state.engine_state == crate::media_engine::EngineState::Playing
                        && pb_state.current.is_some();

                    if let Some(pos) = media_engine.repo.enqueue(chat_id, track.clone()).await? {
                        if is_connected_and_playing {
                            let text = SoulKingUI::format_enqueued(&track, pos);
                            bot.send_message(msg.chat.id, text).parse_mode(ParseMode::Html).await?;
                        } else {
                            let next = media_engine.repo.next_track(chat_id).await?;
                            if let Some(t) = next {
                                media_engine.play(chat_id, &t).await?;
                                let text = SoulKingUI::format_now_playing(&t, 0, false, &LoopMode::Off, pb_state.voice_state, &pb_state.queue);
                                let sent = bot.send_message(msg.chat.id, text)
                                    .parse_mode(ParseMode::Html)
                                    .reply_markup(SoulKingUI::now_playing_keyboard(false))
                                    .await?;
                                let _ = media_engine.repo.set_player_message_id(chat_id, Some(sent.id.0)).await;
                            }
                        }
                    }
                }
                Err(e) => {
                    bot.send_message(msg.chat.id, format!("❌ <b>Search failed:</b> {e}")).parse_mode(ParseMode::Html).await?;
                }
            }
        }
        BotCommand::Vplay(query) => {
            if query.trim().is_empty() {
                bot.send_message(msg.chat.id, "Please specify a video title or URL e.g. <code>/vplay video title</code>").parse_mode(ParseMode::Html).await?;
                return Ok(());
            }

            // Route Path: /vplay title/URL -> Video Resolver
            match video_resolver.resolve_video(&query, user_id, &user_name).await {
                Ok(track) => {
                    let pb_state = media_engine.state(chat_id).await?;
                    let is_connected_and_playing = pb_state.voice_state == crate::media_engine::VoiceState::Connected
                        && pb_state.engine_state == crate::media_engine::EngineState::Playing
                        && pb_state.current.is_some();

                    if let Some(pos) = media_engine.repo.enqueue(chat_id, track.clone()).await? {
                        if is_connected_and_playing {
                            let text = SoulKingUI::format_enqueued(&track, pos);
                            bot.send_message(msg.chat.id, text).parse_mode(ParseMode::Html).await?;
                        } else {
                            let next = media_engine.repo.next_track(chat_id).await?;
                            if let Some(t) = next {
                                media_engine.play(chat_id, &t).await?;
                                let text = SoulKingUI::format_now_playing(&t, 0, false, &LoopMode::Off, pb_state.voice_state, &pb_state.queue);
                                let sent = bot.send_message(msg.chat.id, text)
                                    .parse_mode(ParseMode::Html)
                                    .reply_markup(SoulKingUI::now_playing_keyboard(false))
                                    .await?;
                                let _ = media_engine.repo.set_player_message_id(chat_id, Some(sent.id.0)).await;
                            }
                        }
                    }
                }
                Err(e) => {
                    bot.send_message(msg.chat.id, format!("❌ <b>Video resolution failed:</b> {e}")).parse_mode(ParseMode::Html).await?;
                }
            }
        }
        BotCommand::Pause => {
            media_engine.pause(chat_id).await?;
            bot.send_message(msg.chat.id, "⏸️ <b>Playback Paused</b>").parse_mode(ParseMode::Html).await?;
        }
        BotCommand::Resume => {
            media_engine.resume(chat_id).await?;
            bot.send_message(msg.chat.id, "▶️ <b>Playback Resumed</b>").parse_mode(ParseMode::Html).await?;
        }
        BotCommand::Skip => {
            let pb_state = media_engine.state(chat_id).await?;
            match media_engine.skip(chat_id).await {
                Ok(Some(next)) => {
                    let text = SoulKingUI::format_now_playing(&next, 0, false, &LoopMode::Off, pb_state.voice_state, &pb_state.queue);
                    let sent = bot.send_message(msg.chat.id, text)
                        .parse_mode(ParseMode::Html)
                        .reply_markup(SoulKingUI::now_playing_keyboard(false))
                        .await?;
                    let _ = media_engine.repo.set_player_message_id(chat_id, Some(sent.id.0)).await;
                }
                Ok(None) => {
                    bot.send_message(msg.chat.id, "⏹️ <b>End of Queue — Stage Cleared</b>").parse_mode(ParseMode::Html).await?;
                    let _ = media_engine.repo.set_player_message_id(chat_id, None).await;
                }
                Err(e) => {
                    bot.send_message(msg.chat.id, format!("⚠️ <b>{e}</b>")).parse_mode(ParseMode::Html).await?;
                }
            }
        }
        BotCommand::Prev => {
            let pb_state = media_engine.state(chat_id).await?;
            if let Some(prev) = media_engine.prev(chat_id).await? {
                let text = SoulKingUI::format_now_playing(&prev, 0, false, &LoopMode::Off, pb_state.voice_state, &pb_state.queue);
                let sent = bot.send_message(msg.chat.id, text)
                    .parse_mode(ParseMode::Html)
                    .reply_markup(SoulKingUI::now_playing_keyboard(false))
                    .await?;
                let _ = media_engine.repo.set_player_message_id(chat_id, Some(sent.id.0)).await;
            } else {
                bot.send_message(msg.chat.id, "⚠️ <b>No previous track in history</b>").parse_mode(ParseMode::Html).await?;
            }
        }
        BotCommand::Stop => {
            media_engine.stop(chat_id).await?;
            let _ = media_engine.repo.set_player_message_id(chat_id, None).await;
            bot.send_message(msg.chat.id, "⏹️ <b>Playback Stopped & Stage Cleared</b>").parse_mode(ParseMode::Html).await?;
        }
        BotCommand::Seek(secs) => {
            media_engine.seek(chat_id, secs).await?;
            bot.send_message(msg.chat.id, format!("⏩ <b>Seeked to {secs}s</b>")).parse_mode(ParseMode::Html).await?;
        }
        BotCommand::Volume(vol) => {
            media_engine.set_volume(chat_id, vol).await?;
            bot.send_message(msg.chat.id, format!("🔊 <b>Volume set to {vol}%</b>")).parse_mode(ParseMode::Html).await?;
        }
        BotCommand::Queue => {
            let state = media_engine.state(chat_id).await?;
            let text = SoulKingUI::format_queue(state.current.as_ref(), &state.queue, &state.loop_mode);
            bot.send_message(msg.chat.id, text).parse_mode(ParseMode::Html).await?;
        }
        BotCommand::Now => {
            let state = media_engine.state(chat_id).await?;
            if let Some(curr) = state.current {
                let text = SoulKingUI::format_now_playing(&curr, state.position_secs, state.is_paused, &state.loop_mode, state.voice_state, &state.queue);
                let sent = bot.send_message(msg.chat.id, text)
                    .parse_mode(ParseMode::Html)
                    .reply_markup(SoulKingUI::now_playing_keyboard(state.is_paused))
                    .await?;
                let _ = media_engine.repo.set_player_message_id(chat_id, Some(sent.id.0)).await;
            } else {
                bot.send_message(msg.chat.id, "⏸️ <b>No track currently playing</b>").parse_mode(ParseMode::Html).await?;
            }
        }
        BotCommand::Loop => {
            let mode = media_engine.repo.cycle_loop_mode(chat_id).await?;
            bot.send_message(msg.chat.id, format!("🔁 <b>Loop Mode: {}</b>", mode.display_text())).parse_mode(ParseMode::Html).await?;
        }
        BotCommand::Shuffle => {
            media_engine.repo.shuffle(chat_id).await?;
            bot.send_message(msg.chat.id, "🔀 <b>Queue Shuffled</b>").parse_mode(ParseMode::Html).await?;
        }
        BotCommand::PlayerDebug => {
            let state = media_engine.state(chat_id).await?;
            let curr_title = state.current.as_ref().map(|t| t.title.as_str()).unwrap_or("None");
            let last_err = state.last_error.as_deref().unwrap_or("None");
            let text = format!(
                "🛠️ <b>Player Debug Diagnostics</b>\n\
                 ━━━━━━━━━━━━━━━━━━━━━\n\
                 💬 <b>Chat ID:</b> <code>{chat_id}</code>\n\
                 🔊 <b>Voice State:</b> {}\n\
                 ⚙️ <b>Engine State:</b> {}\n\
                 🎵 <b>Current Track:</b> {}\n\
                 📊 <b>Queue Length:</b> {}\n\
                 📜 <b>History Length:</b> {}\n\
                 🔢 <b>Playback Generation:</b> {}\n\
                 🌐 <b>VC Generation:</b> {}\n\
                 ⏸️ <b>Is Paused:</b> {}\n\
                 🔊 <b>Volume:</b> {}%\n\
                 ⚠️ <b>Last Error:</b> {}",
                state.voice_state.display_text(),
                state.engine_state.display_text(),
                curr_title,
                state.queue_len,
                state.history_len,
                state.playback_generation,
                state.vc_generation,
                state.is_paused,
                state.volume,
                last_err
            );
            bot.send_message(msg.chat.id, text).parse_mode(ParseMode::Html).await?;
        }
    }
    Ok(())
}

pub async fn handle_callback_query(
    bot: Bot,
    q: teloxide::types::CallbackQuery,
    media_engine: Arc<MediaEngine>,
) -> anyhow::Result<()> {
    let Some(msg) = q.message else { return Ok(()); };
    let chat_id = msg.chat().id.0;
    let msg_id = msg.id();
    let data = q.data.as_deref().unwrap_or("");

    match data {
        "cb_toggle_pause" => {
            let state = media_engine.state(chat_id).await?;
            if state.is_paused {
                let _ = media_engine.resume(chat_id).await;
                let _ = bot.answer_callback_query(&q.id).text("▶️ Playback Resumed").await;
            } else {
                let _ = media_engine.pause(chat_id).await;
                let _ = bot.answer_callback_query(&q.id).text("⏸️ Playback Paused").await;
            }
        }
        "cb_skip" => {
            let _ = media_engine.skip(chat_id).await;
            let _ = bot.answer_callback_query(&q.id).text("⏭️ Track Skipped").await;
        }
        "cb_stop" => {
            let _ = media_engine.stop(chat_id).await;
            let _ = media_engine.repo.set_player_message_id(chat_id, None).await;
            let _ = bot.answer_callback_query(&q.id).text("⏹️ Playback Stopped").await;
        }
        "cb_loop" => {
            let mode = media_engine.repo.cycle_loop_mode(chat_id).await?;
            let _ = bot.answer_callback_query(&q.id).text(format!("🔁 Loop Mode: {}", mode.display_text())).await;
        }
        "cb_shuffle" => {
            let _ = media_engine.repo.shuffle(chat_id).await;
            let _ = bot.answer_callback_query(&q.id).text("🔀 Queue Shuffled").await;
        }
        _ => {}
    }

    if let Ok(state) = media_engine.state(chat_id).await {
        if let Some(curr) = &state.current {
            let text = SoulKingUI::format_now_playing(
                curr,
                state.position_secs,
                state.is_paused,
                &state.loop_mode,
                state.voice_state,
                &state.queue,
            );
            let keyboard = SoulKingUI::now_playing_keyboard(state.is_paused);
            let _ = bot.edit_message_text(msg.chat().id, msg_id, text)
                .parse_mode(ParseMode::Html)
                .reply_markup(keyboard)
                .await;
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bot_command_parsing() {
        let cmd = BotCommand::parse("/play reha", "mybot");
        assert!(cmd.is_ok(), "Failed to parse /play reha: {:?}", cmd);
        let cmd2 = BotCommand::parse("/start", "mybot");
        assert!(cmd2.is_ok(), "Failed to parse /start: {:?}", cmd2);
    }
}
