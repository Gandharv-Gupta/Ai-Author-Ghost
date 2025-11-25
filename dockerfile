FROM python:3.10

WORKDIR /app

# Copy everything
COPY . .

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install supervisor to run multiple processes
RUN apt-get update && apt-get install -y supervisor

# Copy supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 5500
EXPOSE 8000

CMD ["supervisord", "-n"]
