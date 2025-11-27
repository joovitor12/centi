# SQL Scripts

This directory contains SQL scripts for direct database execution.

## Migration Scripts

### `create_recurring_appointments_table.sql`

Creates the `recurring_appointments` table for storing recurring appointment templates.

**Note:** This script is provided as a reference. If you're using Alembic migrations, you don't need to run this manually unless you want to apply changes directly to the database.

**Usage in Supabase SQL Editor:**
1. Open your Supabase dashboard
2. Go to SQL Editor
3. Copy and paste the contents of `create_recurring_appointments_table.sql`
4. Execute the script

**What it creates:**
- Table `recurring_appointments` with all necessary columns
- Indexes for performance optimization (`ix_recurring_appointments_id`, `ix_recurring_appointments_is_active`)
- Column comments for documentation

**Verification:**
After running the script, verify the table was created:
```sql
SELECT * FROM information_schema.tables WHERE table_name = 'recurring_appointments';
```
