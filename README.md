# BACI HS92 V202601 (2024) over SPARQL

Serve BACI HS92 V202601 (2024) as a virtual RDF data cube using Ontop and DuckDB.
The [database build](database/README.md) publishes a compressed Maven artifact;
the [endpoint build](endpoint/README.md) packages it with the mappings.

## Build and run

Requires Maven, a JDK, GNU Make and Docker with BuildKit/Compose.
From the repository root:

```sh
mvn -f database/pom.xml -P local deploy
make -C endpoint up
```

The `local` profile publishes the dataset to `database/target/m2` and skips
installation into your normal Maven repository. Without it, `mvn install` and
`mvn deploy` also put the dataset alongside your other Maven artifacts
(usually in `~/.m2/repository`). Source and plugin dependencies still use Maven's
configured cache in either case.

The endpoint uses `database/target/m2` by default when present, with its own
Maven cache and remote repositories available too. Override this folder with
`DATABASE_REPOSITORY`, or set it empty to disable it:

```sh
make -C endpoint build DATABASE_REPOSITORY=/path/to/m2
```

Settings can also go in `endpoint/.env`; see
[endpoint configuration](endpoint/README.md#configuration).
The service runs at [localhost:8082/sparql](http://localhost:8082/sparql).
Use `make -C endpoint down` to stop it and `make -C endpoint help` for all targets.

## Publish

Database and endpoint versions are independent. Endpoint release defaults live
in `endpoint/build.conf`; `make … VERSION=...` overrides them.
Set a new POM version for each
immutable data release, then publish with Maven credentials from `settings.xml`:

```sh
mvn -f database/pom.xml deploy \
  -DaltDeploymentRepository=aksw-data-releases::https://maven.inf-ai.duckdns.org/releases
make -C endpoint login GHCR_USER=YOUR_GITHUB_USERNAME
make -C endpoint publish VERSION=0.0.2 DATABASE_VERSION=0.0.1
```

Current database coordinates:
`org.aksw.data.baci:baci-hs92-v202601-2024-duckdb:duckdb.zst:0.0.1`.
Building an endpoint locally does not publish it.

## Design and scope

The build follows [FAOSTAT](../sparql-faostat-ontop/README.md): source data and
scripts are bind mounted into the generation containers; completion markers
skip repeated loading and compression. The endpoint image contains an unpacked,
read-only database, with data layers before JDBC and configuration.

BACI contains **2024 only**. `database/years.csv` selects the year; code lists
remain complete. Country links use BACI area codes and a reviewed exclusion
policy, rather than treating numeric area codes as ISO/M49 identities.

After changing database inputs or loading settings, rebuild with
`mvn -f database/pom.xml -P local clean deploy`. This removes `target/m2` too.
Use new release versions for changed published data; Maven may reuse cached
releases. See [model and country-link details](docs/model.md).
The sibling [Helm chart](../helm-charts/charts/ontop/README.md) deploys the
selected endpoint image independently.

## Tests

See [database tests](database/README.md#tests) for fixtures and script checks.
`make -C endpoint check` verifies orchestration; `make -C endpoint test` also
builds and queries an isolated endpoint container.

## Sources and licence

Original project material is licensed under [Apache-2.0](LICENSE).
[Licensing notes](LICENSING.md) distinguish third-party/data terms and declare
that the information about those terms was derived with AI assistance.

CEPII BACI V202601 (30 January 2026), HS92, 2024. Citation: Gaulier and Zignago
(2010), *BACI: International Trade Database at the Product-Level*, CEPII Working
Paper 2010-23. Data licence: [Etalab 2.0](https://www.data.gouv.fr/pages/legal/licences/etalab-2.0).
Retain source attribution and transformation notices. Country-link exclusions
are PROVIDER policy, not an official CEPII concordance. See the
[country provenance record](database/baci-country-mapping.meta.md).
