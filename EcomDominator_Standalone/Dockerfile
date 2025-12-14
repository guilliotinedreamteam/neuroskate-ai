FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (needed for psycopg2, etc)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy project files
COPY pyproject.toml poetry.lock* /app/

# Install dependencies (no dev dependencies for prod, but we might want them for this demo)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy source code
COPY . /app

# Expose ports (Streamlit: 8501, API: 8000)
EXPOSE 8501 8000

# Default command (can be overridden in docker-compose)
CMD ["python", "-m", "ecom_dominator.main"]
