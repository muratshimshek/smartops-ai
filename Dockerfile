FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ARG INSTALL_RAG=false
COPY requirements.txt requirements-rag.txt ./
RUN if [ "$INSTALL_RAG" = "true" ]; then pip install --no-cache-dir -r requirements-rag.txt; else pip install --no-cache-dir -r requirements.txt; fi
COPY app ./app
RUN addgroup --system smartops && adduser --system --ingroup smartops smartops && chown -R smartops:smartops /app
USER smartops
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

