FROM python:3.11-slim-bookworm AS builder

# Set working directory
ENV DIR=/app
WORKDIR $DIR

# Install Poetry
RUN pip install --no-cache-dir poetry

# Configure Poetry to create virtualenv in project
RUN poetry config virtualenvs.in-project true

# Copy dependency files (include poetry.lock!)
COPY pyproject.toml poetry.lock* $DIR/

# Install dependencies (without installing the project itself)
RUN poetry install --no-root --no-interaction --no-ansi

# Copy the application code
COPY src $DIR/src

# Set environment variable (can be overridden at runtime)
ENV AZURE_CONNECTION_STRING=""

# Create non-root user and fix ownership
RUN useradd -u 1000 -m appuser \
 && chown -R appuser:appuser $DIR
USER appuser

# Expose port for Streamlit
EXPOSE 8501

# Launch the Streamlit app
CMD ["poetry", "run", "streamlit", "run", "src/st_front.py", "--server.port=8501", "--server.address=0.0.0.0"]
