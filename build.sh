#!/usr/bin/env bash
# Script de build usado na hospedagem (ex.: Render).
# Start command: gunicorn projeto.wsgi:application
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
