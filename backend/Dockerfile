# Python 3.14 -- samakan dengan environment lokal Raymond yang sudah
# terverifikasi jalan (lihat requirements.txt untuk versi dependency exact).
FROM python:3.14-slim

WORKDIR /app

# Copy requirements dulu (terpisah dari copy source code) supaya Docker
# bisa cache layer install dependency -- rebuild jadi jauh lebih cepat
# kalau yang berubah cuma kode, bukan requirements.txt.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]