FROM python:3.12-slim

# Evita buffer de log
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV DJANGO_SETTINGS_MODULE=flash_project.settings

# Diretório de trabalho
WORKDIR /app

# Dependências de sistema (opencv / rembg precisam disso)
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
 && rm -rf /var/lib/apt/lists/*

# Copia requirements
COPY requirements.txt .

# Instala dependências Python
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia projeto
COPY . .

# Coleta arquivos estáticos
RUN python manage.py collectstatic --noinput || true

# Expõe porta
EXPOSE 8000

# Comando de produção
CMD sh -c "python manage.py migrate && gunicorn flash_project.wsgi:application --bind 0.0.0.0:8000"


