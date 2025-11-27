-- Migration: Create recurring_appointments table
-- Execute this SQL script directly in your Supabase database
-- This script is provided as a reference and can be used if needed

CREATE TABLE IF NOT EXISTS recurring_appointments (
    id SERIAL PRIMARY KEY,
    description TEXT NOT NULL,
    start_time VARCHAR NOT NULL,
    end_time VARCHAR,
    recurrence_pattern VARCHAR(50) NOT NULL,
    recurrence_interval INTEGER NOT NULL DEFAULT 1,
    recurrence_byday VARCHAR(100),
    recurrence_bymonthday INTEGER,
    end_date VARCHAR,
    max_occurrences INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    google_calendar_event_id VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create index on id for faster lookups
CREATE INDEX IF NOT EXISTS ix_recurring_appointments_id ON recurring_appointments(id);

-- Create index on is_active for filtering active/inactive recurring appointments
CREATE INDEX IF NOT EXISTS ix_recurring_appointments_is_active ON recurring_appointments(is_active);

-- Add comments to columns for documentation
COMMENT ON TABLE recurring_appointments IS 'Stores templates for recurring appointments that repeat automatically';
COMMENT ON COLUMN recurring_appointments.description IS 'Description of the recurring appointment';
COMMENT ON COLUMN recurring_appointments.start_time IS 'First occurrence time in ISO format';
COMMENT ON COLUMN recurring_appointments.end_time IS 'Event duration end time in ISO format (optional, defaults to 1 hour after start)';
COMMENT ON COLUMN recurring_appointments.recurrence_pattern IS 'Pattern type: daily, weekly, monthly, yearly';
COMMENT ON COLUMN recurring_appointments.recurrence_interval IS 'Interval for recurrence (e.g., every 2 weeks = 2)';
COMMENT ON COLUMN recurring_appointments.recurrence_byday IS 'Days of week for weekly patterns (e.g., MO,WE,FR or MO)';
COMMENT ON COLUMN recurring_appointments.recurrence_bymonthday IS 'Day of month for monthly patterns (e.g., 15)';
COMMENT ON COLUMN recurring_appointments.end_date IS 'When recurrence should stop (optional)';
COMMENT ON COLUMN recurring_appointments.max_occurrences IS 'Maximum number of occurrences (optional)';
COMMENT ON COLUMN recurring_appointments.is_active IS 'Whether the recurring appointment is active (can be paused/resumed)';
COMMENT ON COLUMN recurring_appointments.google_calendar_event_id IS 'ID of the recurring event in Google Calendar';

-- Verify table was created
SELECT 'Table recurring_appointments created successfully' AS status;
