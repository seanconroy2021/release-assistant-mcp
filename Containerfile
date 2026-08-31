FROM registry.redhat.io/ubi10/python-312-minimal:10.2-1788165617 AS builder

USER 0

RUN microdnf install -y --nodocs --setopt=install_weak_deps=0 git-core && \
    microdnf clean all

# fix pip GHSAs before we install anything
RUN pip install --no-cache-dir --upgrade pip

RUN pip install --no-cache-dir pyyaml

COPY config.yaml /app/config.yaml
COPY scripts/clone_repos.py scripts/crawl-docs.py /tmp/
RUN python3 /tmp/clone_repos.py /data && python3 /tmp/crawl-docs.py /data/docs

COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir --no-compile . && rm -rf /tmp/*

# pip is not needed at runtime so drop it from the app-root
RUN pip uninstall -y pip

FROM registry.redhat.io/ubi10/python-312-minimal:10.2-1788165617

USER 0

# pull in any RPM security patches released after the base image was built
RUN microdnf update -y --nodocs --setopt=install_weak_deps=0 && \
    microdnf clean all

ARG BUILD_DATE=""

LABEL name="Release Assistant MCP"
LABEL build-date="${BUILD_DATE}"
LABEL description="Release Assistant MCP"
LABEL io.k8s.description="Release Assistant MCP"
LABEL io.k8s.display-name="release-assistant-mcp"
LABEL summary="Release Assistant MCP"
LABEL com.redhat.component="release-assistant-mcp"
LABEL maintainer="Sean Conroy <sconroy@redhat.com>"

COPY LICENSE /licenses/LICENSE
COPY --from=builder /opt/app-root /opt/app-root
COPY --from=builder /data /data
COPY --from=builder /app/config.yaml /app/config.yaml

# wipe any leftover pip bits that came from the base image layer
RUN python3 -c "import shutil; shutil.rmtree('/opt/app-root/lib/python3.12/site-packages/pip', True)"

ENV RELEASE_MCP_DATA_DIR=/data \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER 1001

ENTRYPOINT ["release-mcp"]
