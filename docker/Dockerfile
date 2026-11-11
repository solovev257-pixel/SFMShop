# Этап 1: ставим зависимости
FROM python:3.13-slim AS builder
WORKDIR /app
# сначала только список библиотек: этот слой берётся из кэша, пока requirements.txt не менялся
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Этап 2: финальный образ, только готовые пакеты и код
FROM python:3.13-slim
WORKDIR /app

# приложение работает не от root; папку /app отдаём ему, чтобы оно могло писать app.log
RUN useradd --create-home appuser && chown appuser:appuser /app
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .
ENV PATH=/home/appuser/.local/bin:$PATH
USER appuser

EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
