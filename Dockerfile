FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY README.md .
COPY glmllb/ glmllb/

RUN pip install --no-cache-dir -e .

EXPOSE 2456

CMD ["glmllb"]
