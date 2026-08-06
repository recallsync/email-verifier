CREATE MATERIALIZED VIEW IF NOT EXISTS stats AS
SELECT
    COALESCE(SUM(processed_rows), 0)::BIGINT AS total_emails_verified,
    COUNT(*) FILTER (WHERE status = 'completed')::INTEGER AS total_lists_completed,
    COUNT(*)::INTEGER AS total_lists
FROM lists;

CREATE UNIQUE INDEX IF NOT EXISTS idx_stats_singleton ON stats ((true));

REFRESH MATERIALIZED VIEW stats;
