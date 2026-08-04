FROM python:3.12-slim

WORKDIR /app

# Install dependency dulu (layer terpisah supaya cache Docker efektif)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin source code
COPY zfic/ ./zfic/
COPY templates_data/ ./templates_data/
COPY tools/ ./tools/
COPY examples/ ./examples/
COPY pyproject.toml README.md ./

# Install package itu sendiri (mode non-editable untuk image produksi)
RUN pip install --no-cache-dir .

# Direktori untuk audit log persisten -- mount volume ke sini
RUN mkdir -p /data
ENV ZFIC_AUDIT_LOG_PATH=/data/audit.jsonl
ENV ZFIC_CONTEXT_DATA_DIR=/app/templates_data
ENV PORT=8080

EXPOSE 8080

# Non-root user untuk keamanan container
RUN useradd -m zficuser && chown -R zficuser:zficuser /app /data
USER zficuser

# gunicorn untuk produksi (bukan Flask dev server)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "zfic.app:app"]
