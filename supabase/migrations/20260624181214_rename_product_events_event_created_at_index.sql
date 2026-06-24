DO $$
BEGIN
    IF to_regclass('public.idx_product_events_event_created_at') IS NULL
       AND to_regclass('public.idx_product_events_event_name_time') IS NOT NULL
    THEN
        ALTER INDEX public.idx_product_events_event_name_time
        RENAME TO idx_product_events_event_created_at;
    END IF;
END
$$;