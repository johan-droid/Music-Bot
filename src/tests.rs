#[cfg(test)]
mod tests {
    use crate::commands::SoulKingUI;
    use crate::media_engine::{ChatQueueState, LoopMode, UNKNOWN_DURATION_LIMIT_SECS};
    use crate::router::{SourceKind, Track, TrackId};

    fn track(id: &str, title: &str) -> Track {
        Track {
            id: TrackId::new(id),
            title: title.into(),
            artist: Some("Brook".into()),
            url: "http://example.com".into(),
            duration_secs: 180,
            thumbnail_url: None,
            requested_by: 123,
            requested_by_name: "Luffy".into(),
            source: SourceKind::YouTube,
            external_id: None,
        }
    }

    #[test]
    fn test_queue_operations() {
        let mut q = ChatQueueState::new(100, 100);

        q.enqueue(track("t1", "Binks Sake"));
        q.enqueue(track("t2", "Soul King Live"));

        assert_eq!(q.queue.len(), 2);

        let next = q.next_track();
        assert!(next.is_some());
        assert_eq!(next.unwrap().title, "Binks Sake");
        assert_eq!(q.queue.len(), 1);
        assert_eq!(q.history.len(), 0);

        let next = q.next_track();
        assert_eq!(next.unwrap().title, "Soul King Live");
        assert_eq!(q.history.len(), 1);
        assert!(q.next_track().is_none());
        assert_eq!(q.history.len(), 2);
    }

    #[test]
    fn test_loop_mode_track_skip_advances() {
        let mut q = ChatQueueState::new(100, 100);
        q.loop_mode = LoopMode::Track;
        q.enqueue(track("t1", "Binks Sake"));
        q.enqueue(track("t2", "Soul King Live"));

        let first = q.next_track().unwrap();
        assert_eq!(first.title, "Binks Sake");

        let skipped = q.next_track().unwrap();
        assert_eq!(skipped.title, "Soul King Live");
        assert_eq!(q.history.len(), 1);
    }

    #[test]
    fn test_loop_mode_queue_rotates_without_duplication() {
        let mut q = ChatQueueState::new(100, 100);
        q.loop_mode = LoopMode::Queue;
        q.enqueue(track("t1", "Binks Sake"));
        q.enqueue(track("t2", "Soul King Live"));

        let first = q.next_track().unwrap();
        assert_eq!(first.title, "Binks Sake");
        assert!(q.history.is_empty());
        assert_eq!(q.queue.len(), 1);

        let second = q.next_track().unwrap();
        assert_eq!(second.title, "Soul King Live");

        let third = q.next_track().unwrap();
        assert_eq!(third.title, "Binks Sake");
        assert_eq!(q.queue.len(), 1);
    }

    #[test]
    fn test_prev_track() {
        let mut q = ChatQueueState::new(100, 100);
        q.enqueue(track("t1", "Binks Sake"));
        q.enqueue(track("t2", "Soul King Live"));
        q.next_track();
        q.next_track();

        let prev = q.prev_track().unwrap();
        assert_eq!(prev.title, "Binks Sake");
        assert!(q.current.is_some());
    }

    #[test]
    fn test_queue_full() {
        let mut q = ChatQueueState::new(1, 100);
        assert!(q.enqueue(track("t1", "A")).is_some());
        assert!(q.enqueue(track("t2", "B")).is_none());
    }

    #[test]
    fn test_stop_reset() {
        let mut q = ChatQueueState::new(100, 100);
        q.enqueue(track("t1", "Binks Sake"));
        q.next_track();
        q.is_paused = true;

        q.reset();
        assert!(q.current.is_none());
        assert!(q.queue.is_empty());
        assert!(q.history.is_empty());
        assert!(!q.is_paused);
    }

    #[test]
    fn test_default_volume() {
        let q = ChatQueueState::new(100, 60);
        assert_eq!(q.volume, 60);
    }

    #[test]
    fn test_tick_auto_advances() {
        let mut q = ChatQueueState::new(100, 100);
        q.enqueue(track("t1", "Binks Sake"));
        q.next_track();
        assert!(q.current.is_some());
        for _ in 0..180 {
            q.tick();
        }
        assert!(q.current.is_none(), "track should have completed");
    }

    #[test]
    fn test_tick_paused_does_not_advance() {
        let mut q = ChatQueueState::new(100, 100);
        q.enqueue(track("t1", "Binks Sake"));
        q.next_track();
        q.is_paused = true;
        for _ in 0..5 {
            q.tick();
        }
        assert!(q.current.is_some());
        assert_eq!(q.position_secs, 0);
    }

    #[test]
    fn test_tick_loop_track_replays() {
        let mut q = ChatQueueState::new(100, 100);
        q.loop_mode = LoopMode::Track;
        q.enqueue(track("t1", "Binks Sake"));
        q.next_track();
        for _ in 0..180 {
            q.tick();
        }
        assert!(q.current.is_some(), "track loop should replay the same track");
        assert_eq!(q.current.as_ref().unwrap().title, "Binks Sake");
    }

    #[test]
    fn test_progress_bar() {
        let bar = SoulKingUI::build_progress_bar(60, 120, 10);
        assert!(bar.contains("01:00 / 02:00"));
        assert!(bar.contains("▓▓▓▓▓░░░░░"));
    }

    #[test]
    fn test_progress_bar_zero_duration() {
        let bar = SoulKingUI::build_progress_bar(0, 0, 10);
        assert!(bar.contains("00:00 / 00:00"));
    }

    #[test]
    fn test_tick_unknown_duration_auto_advances() {
        let mut q = ChatQueueState::new(100, 100);
        let mut unknown = track("t0", "Unknown Length");
        unknown.duration_secs = 0;
        q.current = Some(unknown);

        for _ in 0..UNKNOWN_DURATION_LIMIT_SECS {
            q.tick();
        }
        assert!(q.current.is_none(), "unknown-duration track should be capped and advanced");
    }

    #[test]
    fn test_set_position_clamps_to_duration() {
        let mut q = ChatQueueState::new(100, 100);
        q.current = Some(track("t1", "Binks Sake"));
        q.set_position(60);
        assert_eq!(q.position_secs, 60);
        q.set_position(u64::MAX);
        assert_eq!(q.position_secs, 179);
        q.current.as_mut().unwrap().duration_secs = 0;
        q.set_position(5);
        assert_eq!(q.position_secs, 5);
    }

    #[test]
    fn test_clear_current_rolls_back() {
        let mut q = ChatQueueState::new(100, 100);
        q.enqueue(track("t1", "Binks Sake"));
        q.next_track();
        assert!(q.current.is_some());
        q.set_position(30);

        let removed = q.clear_current();
        assert_eq!(removed.unwrap().title, "Binks Sake");
        assert!(q.current.is_none());
        assert_eq!(q.position_secs, 0);
        assert_eq!(q.queue.len(), 0);
    }

    #[test]
    fn test_skip_empty_queue_returns_error_and_preserves_queue() {
        let mut q = ChatQueueState::new(100, 100);
        assert!(q.current.is_none());
        let res = q.skip();
        assert!(res.is_err());
        assert_eq!(q.engine_state, crate::media_engine::EngineState::Idle);
    }

    #[test]
    fn test_skip_active_track_advances_to_next() {
        let mut q = ChatQueueState::new(100, 100);
        q.enqueue(track("t1", "Song A"));
        q.enqueue(track("t2", "Song B"));
        q.next_track();

        assert_eq!(q.current.as_ref().unwrap().title, "Song A");
        assert_eq!(q.queue.len(), 1);

        let next = q.skip().unwrap();
        assert!(next.is_some());
        assert_eq!(next.unwrap().title, "Song B");
        assert_eq!(q.current.as_ref().unwrap().title, "Song B");
        assert_eq!(q.queue.len(), 0);
        assert_eq!(q.history.len(), 1);
        assert_eq!(q.history[0].title, "Song A");
        assert_eq!(q.engine_state, crate::media_engine::EngineState::Playing);
    }

    #[test]
    fn test_skip_final_track_settles_to_idle() {
        let mut q = ChatQueueState::new(100, 100);
        q.enqueue(track("t1", "Song A"));
        q.next_track();

        let res = q.skip().unwrap();
        assert!(res.is_none());
        assert!(q.current.is_none());
        assert!(q.queue.is_empty());
        assert_eq!(q.engine_state, crate::media_engine::EngineState::Idle);
    }

    #[test]
    fn test_race_condition_transition_lock_prevents_duplicate_skip_or_eof() {
        let mut q = ChatQueueState::new(100, 100);
        q.enqueue(track("t1", "Song A"));
        q.enqueue(track("t2", "Song B"));
        q.next_track();

        // 1. Begin transition to SKIPPING
        assert!(q.begin_transition(crate::media_engine::EngineState::Skipping));
        assert!(q.transition_in_progress);

        // 2. Simultaneous duplicate transition attempt (e.g. EOF + /skip race)
        assert!(!q.begin_transition(crate::media_engine::EngineState::Finished));

        // 3. End transition safely
        q.end_transition(crate::media_engine::EngineState::Playing);
        assert!(!q.transition_in_progress);
    }

    #[test]
    fn test_stop_clears_queue_and_resets_to_idle() {
        let mut q = ChatQueueState::new(100, 100);
        q.enqueue(track("t1", "Song A"));
        q.enqueue(track("t2", "Song B"));
        q.next_track();

        q.reset();
        assert!(q.current.is_none());
        assert!(q.queue.is_empty());
        assert!(q.history.is_empty());
        assert_eq!(q.engine_state, crate::media_engine::EngineState::Idle);
    }

    #[test]
    fn test_play_while_playing_enqueues_without_interrupting_current() {
        let mut q = ChatQueueState::new(100, 100);
        q.enqueue(track("t1", "Song A"));
        q.next_track();

        // Enqueue Song B while Song A is playing
        let pos = q.enqueue(track("t2", "Song B"));
        assert_eq!(pos, Some(1));
        assert_eq!(q.current.as_ref().unwrap().title, "Song A");
        assert_eq!(q.queue.len(), 1);
        assert_eq!(q.engine_state, crate::media_engine::EngineState::Playing);
    }

    #[tokio::test]
    async fn test_db_repository_memory_first_user_settings_and_playlists() {
        use crate::db::{DbRepository, MemoryFirstDbRepository, Playlist};

        let db = MemoryFirstDbRepository::new(Some("mongodb+srv://atlas-cluster.example.com/brook".into()));
        assert!(db.is_connected());

        let settings = db.get_user_settings(42).await.unwrap();
        assert_eq!(settings.user_id, 42);
        assert_eq!(settings.volume, 100);

        let mut updated = settings.clone();
        updated.volume = 80;
        db.save_user_settings(updated).await.unwrap();

        let fetched = db.get_user_settings(42).await.unwrap();
        assert_eq!(fetched.volume, 80);

        let playlist = Playlist {
            name: "Favorites".into(),
            owner_id: 42,
            track_urls: vec!["https://www.youtube.com/watch?v=x5jfluo1_Yc".into()],
        };
        db.save_playlist(playlist.clone()).await.unwrap();

        let found = db.get_playlist(42, "Favorites").await.unwrap();
        assert!(found.is_some());
        assert_eq!(found.unwrap().track_urls.len(), 1);
    }

    #[tokio::test]
    async fn test_db_repository_analytics_logging() {
        use crate::db::{DbRepository, MemoryFirstDbRepository};

        let db = MemoryFirstDbRepository::new(None);
        assert!(!db.is_connected());
        db.log_analytics("track_play", "yt:x5jfluo1_Yc").await.unwrap();
    }
}