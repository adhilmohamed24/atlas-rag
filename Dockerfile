FROM python:3.12-slim
RUN useradd -m -u 1000 user
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=user:user . .
RUN mkdir -p /app/data && chown user:user /app/data
USER user
ENV HOME=/home/user PYTHONUNBUFFERED=1 DATA_DIR=/app/data
EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
