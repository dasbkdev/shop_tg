#!/bin/bash

echo "🚀 Очистка миграций..."

find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc"  -delete

echo "🗑 Удаление базы данных..."
rm -f db.sqlite3

echo "⚙️  Создание новых миграций..."
python manage.py makemigrations

echo "🛠 Применение миграций..."
python manage.py migrate

echo "✅ Все готово!"
