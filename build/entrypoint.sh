#!/bin/sh

set -e

echo "Checking database connection..."
set +e
while true; do
    if python manage.py shell -c 'import django.db; django.db.connection.ensure_connection()'; then
        echo "Database is ready!"
        break
    else
        echo "Database not ready yet, retrying in 1 second..."
        sleep 1
    fi
done
set -e

if [ "$#" -gt 0 ]; then
    exec "$@"
fi

python manage.py migrate --noinput
python manage.py seed_demo_data

exec python manage.py runserver 0.0.0.0:8000
