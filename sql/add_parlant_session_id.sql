-- Add parlant_session_id column to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS parlant_session_id TEXT;

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_parlant_session_id ON users(parlant_session_id);

