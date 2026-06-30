FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install system deps required by geospatial packages
RUN apt-get update \
	&& apt-get install -y --no-install-recommends libgeos-dev libproj-dev gcc build-essential \
	&& rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (do not copy tests into production image)
COPY app ./app
COPY ml ./ml
COPY models ./models

# Create a non-root user and give ownership of the app directory
RUN useradd --create-home --shell /bin/false appuser \
	&& chown -R appuser:appuser /app

USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


