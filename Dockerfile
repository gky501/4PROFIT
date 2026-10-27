FROM python:3.12-slim
WORKDIR /app
COPY server.py .
COPY public ./public
RUN mkdir data && useradd -r app && chown -R app:app /app
USER app
ENV HOST=0.0.0.0 PORT=8080 DATABASE_PATH=/app/data/site.db
EXPOSE 8080
CMD ["python", "server.py"]
