FROM python:3.12-slim
WORKDIR /service
RUN pip install --no-cache-dir "fastapi>=0.115,<1" "uvicorn>=0.30,<1"
COPY app.py ./app.py
EXPOSE 8001
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
