#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."

# Check if alembic_version table exists (indicates Alembic was used before)
# If not, stamp the current state as the base revision before upgrading
python3 -c "
from app.database import engine
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
if 'alembic_version' not in tables:
    print('First time running Alembic - stamping existing schema')
    import subprocess
    # Stamp as the last migration before our new one
    subprocess.run(['alembic', 'stamp', '6312eb89fded'], check=True)
"

# Now run any pending migrations
alembic upgrade head

# Start the application
echo "Starting application..."
exec gunicorn app.main:app -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
