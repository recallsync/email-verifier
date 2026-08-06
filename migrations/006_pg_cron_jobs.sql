-- pg_cron maintenance jobs (requires pg_cron extension)
DO $outer$
DECLARE
    r RECORD;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        RAISE NOTICE 'pg_cron not available — maintenance runs via in-app tick fallback';
        RETURN;
    END IF;

    FOR r IN
        SELECT jobid FROM cron.job
        WHERE jobname IN (
            'recover-stale-rows',
            'mark-interrupted-lists',
            'refresh-stats',
            'purge-old-lists'
        )
    LOOP
        PERFORM cron.unschedule(r.jobid);
    END LOOP;

    PERFORM cron.schedule(
        'recover-stale-rows',
        '*/5 * * * *',
        $job$
            UPDATE list_rows
            SET status = 'pending', picked_at = NULL
            WHERE status = 'processing'
              AND picked_at < now() - interval '10 minutes';
        $job$
    );

    PERFORM cron.schedule(
        'mark-interrupted-lists',
        '*/5 * * * *',
        $job$
            UPDATE lists
            SET status = 'interrupted', updated_at = now()
            WHERE status = 'processing'
              AND updated_at < now() - interval '15 minutes'
              AND NOT EXISTS (
                  SELECT 1 FROM list_rows
                  WHERE list_id = lists.id AND status = 'processing'
              );
        $job$
    );

    PERFORM cron.schedule(
        'refresh-stats',
        '0 3 * * *',
        $$REFRESH MATERIALIZED VIEW CONCURRENTLY stats;$$
    );

    PERFORM cron.schedule(
        'purge-old-lists',
        '0 4 * * 0',
        $job$
            DELETE FROM lists
            WHERE status IN ('completed', 'cancelled', 'failed')
              AND completed_at < now() - interval '90 days';
        $job$
    );
END;
$outer$;
