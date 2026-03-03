#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."

# Check if alembic_version table exists AND has a version row
# If the DB was created with create_all() instead of migrations, we need to stamp it
python3 -c "
from app.database import engine
from sqlalchemy import inspect, text
inspector = inspect(engine)
tables = inspector.get_table_names()

needs_stamp = False
if 'alembic_version' not in tables:
    print('No alembic_version table found')
    needs_stamp = True
else:
    # Check if there's actually a version in the table
    with engine.connect() as conn:
        result = conn.execute(text('SELECT version_num FROM alembic_version'))
        row = result.fetchone()
        if row is None:
            print('alembic_version table exists but is empty')
            needs_stamp = True
        else:
            print(f'Current alembic version: {row[0]}')

if needs_stamp:
    # Check if base tables exist (DB was created with create_all)
    if 'notes' in tables:
        print('Existing schema detected - stamping at 6312eb89fded')
        import subprocess
        subprocess.run(['alembic', 'stamp', '6312eb89fded'], check=True)
    else:
        print('Fresh database - migrations will create schema')
"

# Now run any pending migrations
alembic upgrade head

# Start the application
echo "Starting application..."
exec gunicorn app.main:app -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
