-- Add user_email column to appointments table for multi-user support
-- This ensures each appointment is associated with the correct user

ALTER TABLE appointments
ADD COLUMN IF NOT EXISTS user_email VARCHAR(255);

-- Create index for faster queries by user
CREATE INDEX IF NOT EXISTS idx_appointments_user_email ON appointments(user_email);

-- Update existing appointments (if any) - they will be orphaned but won't break
-- In production, you may want to assign them to a default user or delete them

