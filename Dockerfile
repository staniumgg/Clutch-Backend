# Usa imagen oficial de Python 3.11 slim
FROM python:3.11-slim

# Evita crear archivos pyc y fuerza salida en consola (útil en Docker)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala ffmpeg y dependencias del sistema
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo de dependencias y lo instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del proyecto
COPY . .

# Expone el puerto donde corre FastAPI/Uvicorn
EXPOSE 8000

# Comando para arrancar la app con uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

