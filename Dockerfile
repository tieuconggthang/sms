# ---- Base image ----
FROM python:3.12-slim

# Không tạo .pyc và log realtime ra stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ---- System deps (optional but recommended) ----
# serial/usb tools + timezone data (optional)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# ---- Install python deps first (cache friendly) ----
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# ---- Copy source code ----
COPY src /app/src

# (Optional) copy env example; khi chạy sẽ dùng --env-file .env
COPY .env.example /app/.env.example

# Vì project chạy theo module com.nasa..., ta set working dir là /app/src
WORKDIR /app/src

# ---- Run app ----
CMD ["python", "-m", "com.nasa.app.main"]
