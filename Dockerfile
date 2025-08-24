FROM python:3.10-slim

# Install uv astral
RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-cache

COPY src/ ./src

# Create a non-root user and switch to it
RUN useradd -m appuser
USER appuser

CMD ["uv", "run", "python", "src/loan_agent.py", "dev"]