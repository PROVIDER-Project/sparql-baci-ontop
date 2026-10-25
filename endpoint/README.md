# BACI HS92 V202601, 2024 only: Ontop endpoint

The Dockerfile packages a resolved `baci.duckdb.zst` and JDBC, expanding the
database at build time. Startup requires no download or database ingestion.
Maven data coordinate: `org.aksw.data.baci:baci-hs92-v202601-2024-duckdb:duckdb.zst:0.0.1`. The first artifact must be installed locally
or deployed before the endpoint resolver can find it.

## Build and publish

Run in this folder:

```sh
make help
make resolve
make build
make test
make up
make logs
make down
# Explicit publication, after authenticating:
make login GHCR_USER=YOUR_GITHUB_USERNAME
make publish VERSION=0.0.1 DATABASE_VERSION=0.0.1
```

`make build` always runs resolution first. `make up` builds then recreates this
provider's Compose service, on `http://localhost:8082/sparql` by default.
There is no runtime database volume, JDBC bind mount or loading service.
The default image is `ghcr.io/provider-project/sparql-baci-ontop:0.0.1`;
building that tag locally does not publish it. Compose keeps the explicit project
name `sparql-baci-ontop`. `PORT` overrides the host port.

## Versions and Maven configuration

`VERSION` selects the image version, `DATABASE_VERSION` the preloaded artifact
version, and `DUCKDB_JDBC_VERSION` the JDBC version (default 1.5.6.0). `REPOSITORY`
or `IMAGE` overrides the image destination. `DATA_REPOSITORY_URL` defaults to
https://maven.inf-ai.duckdns.org/releases . Keep released database versions immutable.
Mappings and configuration come from this checkout.

The same resolver used by FAOSTAT runs standalone Dependency Plugin 3.11.0 in a
disposable Maven 3.9.11 / JDK 17 container. It resolves local installs/cached
artifacts first, then configured repositories. Checksums are checked on remote
resolution; SHA-1 sidecars record the resolved inputs in the endpoint image.
The helper runs as your host UID/GID so output stays host-owned.

- `M2_DIR` defaults to this folder's `.cache/maven`; its `repository/` is mounted
  writable. Missing artifacts and plugin dependencies are cached there.
- `M2_SETTINGS` defaults to `$HOME/.m2/settings.xml`, independently of the cache.
- `M2_SECURITY` defaults to `$HOME/.m2/settings-security.xml`. Existing settings
  files mount read-only under the helper's Maven user home; missing files are optional.
- `.env` uses Make assignment syntax (unquoted paths). Copy `.env.example` to
  `.env` for local overrides. Command-line values override `.env`, then environment
  values, then defaults. `ENV_FILE` selects another config file.
- `MAVEN_OFFLINE=true` works once the selected artifacts and plugin dependencies
  are available in the selected cache. `MAVEN_IMAGE` overrides the helper image.

```sh
make build M2_DIR="$HOME/.m2"
make build M2_DIR=/mnt/datasets/baci-m2
make show-config
```

Global resolver settings supply Central and the data repository. User settings
provide mirrors, profiles and server credentials. The explicit Maven local-repo
argument overrides a settings.xml localRepository value. Host environment variables
referenced by settings are not automatically forwarded into the helper.

Resolved inputs are staged under `target/artifacts/`. Both that directory and
`.cache/` are gitignored; neither cache nor settings enters the runtime image.
Docker images and layers still use Docker's normal storage. Avoid simultaneous
builds sharing this output directory. Delete `.cache/maven/` to clear Maven's cache
or `target/` to clear staged inputs.

Direct `docker build` or `docker compose build` requires matching artifacts
already staged by `make resolve`. Use `make build` for the complete workflow;
`make -C endpoint …` from the root and `make -f /absolute/path/Makefile …` work too.

## Runtime and checks

Ontop 5.5.0 runs as its unprivileged `ontop` user. DuckDB is mode 0444, opened
read-only through JDBC, with writable spill files under `/tmp/duckdb`. Runtime
layers add the database first, JDBC second and endpoint mappings/provenance last.
The `endpoint-base` target is available for downstream mapping customizations.
The `.dockerignore` allowlist excludes credentials and all unrelated local files.

`make check` exercises orchestration without a Docker daemon or network.
`make test` also builds the image and runs real SPARQL/image checks in an isolated
container with networking disabled and no host bind mounts. It does not restart
an existing deployment. Optional `EXPECTED_OBSERVATIONS` and `EXPECTED_COUNTRY_LINKS`
assert exact counts when testing known fixtures or a validated release.

Source attribution and transformation policy are in [the database README](../database/README.md)
and the metadata copied into `/opt/ontop/input/`. Select this image in the shared
`../../helm-charts/charts/ontop` chart; the chart needs no source/database logic.

## Attribution

CEPII BACI V202601 (30 January 2026), HS92. Citation: Gaulier and Zignago (2010),
BACI: International Trade Database at the Product-Level, CEPII Working Paper
2010-23. Data licence: [Etalab 2.0](https://www.data.gouv.fr/pages/legal/licences/etalab-2.0).
See [country provenance](baci-country-mapping.meta.md) and the root README.
