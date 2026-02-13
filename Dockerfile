# Usa uma imagem Python leve e moderna
FROM python:3.10-slim

# Define diretório de trabalho dentro do container
WORKDIR /app

# Instala dependências do sistema (necessário para compilar pandas/numpy em alguns casos)
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala as bibliotecas Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do projeto para dentro do container
COPY . .

# Comando para rodar o bot
CMD ["python", "main.py"]