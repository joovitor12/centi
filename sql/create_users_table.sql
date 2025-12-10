-- Create users table for multi-user OAuth support
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) UNIQUE NOT NULL,
    calendar_access_token JSONB NOT NULL,
    listen_address VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on user_email for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_user_email ON users(user_email);

-- Create index on listen_address for email worker queries
CREATE INDEX IF NOT EXISTS idx_users_listen_address ON users(listen_address);

