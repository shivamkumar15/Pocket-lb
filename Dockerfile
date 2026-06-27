FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY README.md .
COPY pocket_lb/ pocket_lb/

RUN pip install --no-cache-dir -e .

EXPOSE 2456

CMD ["pocket-lb"]
