# Artifacts are resolved by `make resolve` before Docker packaging.
ARG ENDPOINT_VERSION=0.0.1
ARG BACI_VERSION=0.0.1
ARG DUCKDB_JDBC_VERSION=1.5.6.0

FROM debian:bookworm-slim AS extraction-tools
RUN apt-get update \
    && apt-get install -y --no-install-recommends zstd \
    && rm -rf /var/lib/apt/lists/*
FROM extraction-tools AS database
COPY target/artifacts/baci.duckdb.zst target/artifacts/baci.duckdb.zst.sha1 /artifacts/
RUN zstd --decompress /artifacts/baci.duckdb.zst -o /artifacts/baci.duckdb \
    && test -s /artifacts/baci.duckdb \
    && rm /artifacts/baci.duckdb.zst \
    && chmod 0444 /artifacts/baci.duckdb \
    && touch -d @0 /artifacts/baci.duckdb

# Stable data layer first, before driver or endpoint-specific configuration.
# This target can also be built/tagged for downstream FROM-based customization.
FROM ontop/ontop:5.5.0 AS data-base
COPY --from=database --chown=ontop:ontop /artifacts/baci.duckdb /data/baci.duckdb
COPY --from=database --chown=ontop:ontop /artifacts/baci.duckdb.zst.sha1 /opt/ontop/input/

FROM data-base AS endpoint-base
COPY --chown=ontop:ontop target/artifacts/duckdb_jdbc.jar /opt/ontop/jdbc/duckdb_jdbc.jar
COPY --chown=ontop:ontop target/artifacts/duckdb_jdbc.jar.sha1 /opt/ontop/input/

# Small endpoint-specific layers follow all shared data/runtime layers.
FROM endpoint-base AS endpoint
ARG ENDPOINT_VERSION

COPY --chown=ontop:ontop ontop/baci.r2rml.ttl ontop/baci.properties ontop/baci-constraints.lst ontop/baci-lenses.json /opt/ontop/input/
COPY --chown=ontop:ontop README.md ontop/baci-country-mapping.meta.md /opt/ontop/input/

ENV ONTOP_MAPPING_FILE=/opt/ontop/input/baci.r2rml.ttl \
    ONTOP_PROPERTIES_FILE=/opt/ontop/input/baci.properties \
    ONTOP_CONSTRAINT_FILE=/opt/ontop/input/baci-constraints.lst \
    ONTOP_LENSES_FILE=/opt/ontop/input/baci-lenses.json \
    ONTOP_LOG_LEVEL=debug
# Inherit Ontop's unprivileged user, entrypoint, port and healthcheck.

ARG BACI_VERSION
ARG DUCKDB_JDBC_VERSION
LABEL org.opencontainers.image.title="PROVIDER BACI SPARQL endpoint" \
      org.opencontainers.image.source="https://github.com/PROVIDER-Project/sparql-baci-ontop" \
      org.opencontainers.image.description="Ontop endpoint with a preloaded BACI HS92 V202601, 2024 only database" \
      org.opencontainers.image.version="${ENDPOINT_VERSION}" \
      org.aksw.baci.artifact.version="${BACI_VERSION}" \
      org.aksw.baci.artifact.checksum.algorithm="SHA-1" \
      org.aksw.baci.data.license="https://www.data.gouv.fr/pages/legal/licences/etalab-2.0" \
      org.aksw.baci.data.terms="https://www.cepii.fr/DATA_DOWNLOAD/baci/doc/baci_webpage.html" \
      org.aksw.baci.jdbc.version="${DUCKDB_JDBC_VERSION}"
