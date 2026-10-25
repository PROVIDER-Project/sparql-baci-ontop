#!/bin/sh
set -eu
sh /opt/build/resolve-artifact.sh org.aksw.data.baci baci-hs92-v202601-2024-duckdb \
    "$BACI_VERSION" duckdb.zst baci.duckdb.zst
sh /opt/build/resolve-artifact.sh org.duckdb duckdb_jdbc \
    "$DUCKDB_JDBC_VERSION" jar duckdb_jdbc.jar
