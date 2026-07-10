FROM eclipse-temurin:17-jdk AS java-build
WORKDIR /src
COPY java-bridge/src ./java-bridge/src
COPY scripts/build_java_bridge.sh ./scripts/build_java_bridge.sh
RUN chmod +x ./scripts/build_java_bridge.sh && ./scripts/build_java_bridge.sh

FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MCP_PORT=3000 \
    BRIDGE_PORT=8080 \
    TARIFMATCHER_BASE_URL=http://127.0.0.1:8080
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jre-headless ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY --from=java-build /src/java-bridge/build/tarifmatcher-bridge.jar /app/java-bridge/tarifmatcher-bridge.jar
COPY scripts/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh
EXPOSE 3000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
