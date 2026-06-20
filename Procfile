web: cd eventProject && python manage.py collectstatic --noinput && gunicorn eventProject.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --log-file -
