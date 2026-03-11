FROM registry.redhat.io/ubi10/python-312-minimal:10.1 AS builder

USER 0

RUN microdnf install -y --nodocs --setopt=install_weak_deps=0 git-core && \
    microdnf clean all

RUN pip install --no-cache-dir pyyaml

COPY config.yaml /app/config.yaml

COPY scripts/clone_repos.py /tmp/clone_repos.py
RUN python3 /tmp/clone_repos.py /data

COPY scripts/crawl-docs.py /tmp/crawl-docs.py
RUN python3 /tmp/crawl-docs.py /data/docs

COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir --no-compile .

RUN rm -rf /tmp/*

FROM registry.redhat.io/ubi10/python-312-minimal:10.1

ARG BUILD_DATE=""
ARG CATALOG_DEV_SHA=""
ARG CATALOG_STAGE_SHA=""
ARG CATALOG_PROD_SHA=""

LABEL org.opencontainers.image.title="Release Assistant MCP" \
      org.opencontainers.image.description="MCP server for Release Service assistance" \
      org.opencontainers.image.source="https://github.com/sconroy/release-assistant-mcp" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.vendor="Sean Conroy" \
      io.k8s.display-name="Release Assistant MCP" \
      io.k8s.description="MCP server for Release Service assistance" \
      io.release.catalog.development="${CATALOG_DEV_SHA}" \
      io.release.catalog.staging="${CATALOG_STAGE_SHA}" \
      io.release.catalog.production="${CATALOG_PROD_SHA}"

COPY --from=builder /opt/app-root /opt/app-root
COPY --from=builder /data /data
COPY --from=builder /app/config.yaml /app/config.yaml

ENV RELEASE_MCP_DATA_DIR=/data \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER 1001

ENTRYPOINT ["release-mcp"]
