# Usamos uma imagem slim do Python para economizar espaço
FROM python:3.11-slim

# Evita que o Python gere arquivos .pyc e força o log a sair em tempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

# Instalamos dependências do sistema necessárias para compilar pacotes (como psycopg2)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala as dependências Python
COPY requirements.txt /code/
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copia o código do projeto
COPY ./app /code/app
COPY ./alembic /code/alembic
COPY ./alembic.ini /code/alembic.ini

# Expõe a porta padrão do FastAPI
EXPOSE 8000

# Comando para iniciar o servidor (Uvicorn)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

