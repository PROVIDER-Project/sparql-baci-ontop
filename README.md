# BACI HS92 over SPARQL (Ontop + DuckDB)

Serve the deployed **CEPII BACI HS92 V202601** Maven data as a virtual
QB/SDMX RDF graph. This follows the sibling `sparql-tiva-ontop` and
`sparql-faostat-ontop` projects: download compressed CSV artifacts, ingest
relational tables into DuckDB, then serve read-only JDBC through Ontop R2RML.
RDF is never materialized.

## Start

Requires Docker and Docker Compose v2.

```sh
docker compose up -d
```

The default selection is **2024**, the latest year in this release. The SPARQL
endpoint is **http://localhost:8082/sparql** (`ONTOP_PORT` overrides the port).
Ontop is pinned to 5.5.0 and both DuckDB CLI and JDBC to 1.5.6 / 1.5.6.0,
matching the reference projects. Runtime files are ignored by Git.

Three services run in sequence:

1. `fetch` runs `loader/fetch.sh`. It downloads the selected years, both code
   tables, the original readme, and JDBC. Completed nonempty files are cached;
   downloads use `.part` files and are renamed only on success. Only after all
   downloads succeed is `data/years.csv` replaced with the selected years.
2. `load` runs `loader/load-duckdb.sh` and `ontop/load.sql`, transactionally
   rebuilding facts, code lists, country links and indexes in
   `run/baci.duckdb`. It marks success only after DuckDB exits successfully.
3. `ontop` opens the database read-only, using the R2RML mapping, lenses and
   uniqueness constraints. `ontop.cardinalityMode=STRICT` preserves RDF/SPARQL
   multiplicities. Query logging includes reformulated SQL.

The load is skipped if both a nonempty database and its `.complete` marker
exist. The marker is manual: changes to the year selection, source files,
country policy or SQL require the rebuild below.

Select multiple years before the first start:

```sh
BACI_YEARS='2023 2024' docker compose up -d
# All 30 years (requires substantially more load time, memory and disk):
BACI_YEARS="$(seq -s ' ' 1995 2024)" docker compose up -d
```

Persist the desired values in a local `.env` file if needed (see `.env.example`).
The fetcher accepts only whitespace-separated years 1995..2024. SQL reads
exactly the files listed in `years.csv`; old cached files are not included.
Duplicate year selections are deduplicated. A missing selected file, mismatched
row year, malformed product code or duplicate observation key fails the load.

### Rebuild or change years

Stop Ontop before loading: its JDBC connections hold the database read-only.
Keep the same `BACI_YEARS` setting for later ordinary starts.

```sh
docker compose stop ontop
BACI_YEARS='2023 2024' docker compose run --rm fetch
rm -f run/baci.duckdb.complete
docker compose run --rm load && docker compose up -d --no-deps --force-recreate ontop
```

Do not run the load command if fetching failed. A failed transactional rebuild
preserves the previous committed tables and leaves no completion marker.
Source and database volumes survive `docker compose down`.

## Deployed artifacts

Coordinates: `org.aksw.data.thirdparty.fr.cepii.baci:HS92_V202601:1`.
The default `BACI_BASE_URL` is:

```text
https://maven.inf-ai.duckdns.org/releases/org/aksw/data/thirdparty/fr/cepii/baci/HS92_V202601/1
```

Artifact filenames beneath this URL:

- `HS92_V202601-1-BACI_HS92_Y{YEAR}_V202601.csv.zst`
- `HS92_V202601-1-country_codes_V202601.csv.zst`
- `HS92_V202601-1-product_codes_HS92_V202601.csv.zst`
- `HS92_V202601-1-readme.txt`

Override `BACI_BASE_URL` when using another Maven mirror; keep the coordinates
and filenames. JDBC comes from Maven Central:
`org/duckdb/duckdb_jdbc/1.5.6.0/duckdb_jdbc-1.5.6.0.jar`.
The default 2024 source is about 104 MB compressed. The full 30-year release is
about 2.7 GB compressed; the relational database and indexes need additional
space. Full-release load resource usage has not been benchmarked.

## Country mapping: included data, with explicit exceptions

**No auxiliary country artifact is required for ordinary country links.** The
BACI artifact already contains `country_codes_V202601.csv.zst`, with:

```text
country_code,country_name,country_iso2,country_iso3
```

Facts use `i` and `j` to reference `country_code`. These are **BACI/Comtrade area
codes**, not universally ISO numeric/M49 codes. For example France is `251`,
India `699`, Norway `579`, Switzerland `757`, and USA `842`. Do not derive ISO3
by padding these numbers and joining an ISO numeric table.

Both dimensions point to BACI-specific area resources, for example:

```turtle
<https://example.org/baci/observation/HS92_V202601/2024-276-251-010111>
  <https://example.org/baci/vocab/exporter> <https://example.org/baci/area/276> ;
  <https://example.org/baci/vocab/importer> <https://example.org/baci/area/251> .

<https://example.org/baci/area/276>
  <https://example.org/baci/vocab/hasCountry> <https://example.org/country/DEU> .
```

The `https://example.org/country/{ISO3}` resources are the same join targets
used by TiVA and FAOSTAT. No descriptive triples are asserted on those shared
resources. Labels and original ISO columns describe the BACI **area** instead.
The source country and product labels are preserved, including existing
mojibake in a few country names; they are not silently corrected.

The complete supplied table has **238 areas**. The pinned-release policy
produces **226 country links** and **12 explicitly unresolved areas**. An absent
ISO2 does not disqualify a valid source ISO3 (e.g. Namibia).

| BACI code | Source ISO3 | Why no automatic shared-country identity |
| --- | --- | --- |
| 58 | BEL | Historical Belgium–Luxembourg union, not Belgium alone |
| 200 | CSK | Historical Czechoslovakia |
| 278 | DDR | Historical German Democratic Republic |
| 280 | DEU | Historical Federal Republic of Germany |
| 490 | S19 | “Other Asia, nes”; source code is not ISO3 TWN |
| 530 | ANT | Historical Netherlands Antilles |
| 697 | R20 | “Europe EFTA, nes” residual |
| 711 | ZA1 | Historical Southern African Customs Union |
| 736 | SDN | Historical Sudan including South Sudan |
| 810 | SUN | Historical USSR |
| 849 | PUS | Historical US Miscellaneous Pacific Islands |
| 891 | SCG | Historical Serbia and Montenegro |

The versioned policy is `ontop/baci-country-exclusions.csv`. SQL preserves the
source table separately, requires unique numeric-code and eligible ISO3
mappings, and records all omissions in `baci_area_country_unresolved` with
reasons. The reasons are also queryable through `baci:countryLinkOmission`.
Unknown observed numeric codes retain area resources and facts, receive no
country link, and are reported as missing source definitions. Country and
product tables cover the complete source code lists, even for a fact subset.

BACI's `S19` remains a source notation, never a `/country/S19` identity.
Using code 490 as a Taiwan proxy is a separate analytical decision. Likewise,
historical areas may require dated memberships or successor relations rather
than identity. If those links are needed, add a separately documented,
versioned concordance with source, validity dates, relation type and confidence;
a reusable Maven artifact would be appropriate. Do not turn the historical
`BEL` and `SDN` aliases into current-country identities or use `owl:sameAs`.
No values are allocated among successor countries by this mapping.

Sources: the pinned artifact's country table and `Readme.txt`;
[CEPII BACI documentation](https://www.cepii.fr/DATA_DOWNLOAD/baci/doc/baci_webpage.html).
The country-link exclusions are this project's conservative policy, not an
additional official CEPII concordance. Its ISO3 shape check is paired with the
reviewed exclusions for V202601; it is not a general ISO registry validator.
Re-audit the table and policy before changing the pinned source version.

## RDF model and units

Namespaces intentionally follow the example.org conventions in the siblings.
They should be consolidated together when the provider vocabulary is finalized.

One row is one `qb:Observation`, keyed by `(t, i, j, k)`. The IRI is:

```text
https://example.org/baci/observation/HS92_V202601/{YEAR}-{EXPORTER}-{IMPORTER}-{HS6}
```

A unique index enforces this key. All components are constrained to digits, so
hyphens are unambiguous without escaping. The mapping keeps a visible constant
prefix and a single stored `OBSERVATION_LOCAL_NAME` for selective subject lookup.

| Predicate | Source | RDF object / meaning |
| --- | --- | --- |
| `qb:dataSet` | constant | `.../baci/dataset/HS92_V202601` |
| `baci:exporter` | `i` | `.../baci/area/{code}` |
| `baci:importer` | `j` | `.../baci/area/{code}` |
| `baci:product` | `k` | `.../baci/product/HS92/{six-digit-code}` |
| `sdmx-dimension:refPeriod` | `t` | `xsd:gYear` |
| `sdmx-measure:obsValue` | `v` | `xsd:double`, **thousand USD** |
| `baci:quantity` | `q` | `xsd:double`, **metric tonnes** |
| `sdmx-attribute:unitMeasure` | constant | `.../baci/unit/USD`, applies to value |
| `sdmx-attribute:unitMult` | constant | integer `3`, applies to value |
| `baci:quantityUnit` | constant | `.../baci/unit/tonne`, no multiplier |

`baci:` is `https://example.org/baci/vocab/`. The dataset mapping includes the
QB structure, dimension/measure/attribute declarations, code schemes, units,
CEPII attribution and Etalab 2.0 licence metadata. Values are **not converted**;
multiply `obsValue` by 1000 only if dollar amounts are wanted. Never apply the
value multiplier to quantities. Product codes use VARCHAR throughout so
`010111` retains its leading zero. Areas use BACI's unpadded numeric notation.

Empty or `NA` quantities produce no quantity triple. Zero quantities remain
zero. A null trade value is retained relationally but is excluded by the
observation lens. This avoids dropping a value observation when only its
quantity is missing.

The code-list tables enforce primary keys. Observations have an enforced unique
local-name index, plus exporter, importer, product, year and lexical-value
indexes. Stored lexical columns avoid query-time casts on exact RDF object
lookups; numeric columns remain available for SQL. `ANALYZE` runs after loading.
Indexes do not make unbound triple scans cheap. Broad queries or common values
can still require scans and duplicate elimination under STRICT semantics.

## Query

```sh
curl -fsS 'http://localhost:8082/sparql' \
  --data-urlencode 'query@queries/trade.sparql' \
  -H 'Accept: application/sparql-results+json'
```

`queries/trade.sparql` finds Germany-to-France flows through shared country
links and returns value plus optional quantity. `queries/unresolved-areas.sparql`
shows omitted country links and reasons. `queries/country-join.sparql` illustrates
a join with TiVA when both graphs are available to a federation; a standalone
BACI endpoint does not itself contain TiVA data. Use FAOSTAT's
`https://example.org/faostat/vocab/hasCountry` for the analogous country join.
Country alignment does not make BACI gross trade, TiVA value added, and FAOSTAT
production measures directly comparable.

## Validation

```sh
python3 -m unittest discover -s tests -v
```

Fetch and completion-marker tests use fake executables and need only Python 3.
The SQL tests use real compressed fixtures, `zstd`, a JDK, and the JDBC jar in
`jdbc/` (or `DUCKDB_JDBC_JAR`). For actual Ontop query tests, extract the 5.5.0
CLI, put the JDBC jar in its `jdbc/`, and set `ONTOP_CLI` to its `ontop` script:

```sh
DUCKDB_JDBC_JAR=/path/to/duckdb_jdbc-1.5.6.0.jar \
ONTOP_CLI=/path/to/ontop-cli/ontop \
python3 -m unittest discover -s tests -v
```

Checks cover year selection and stale caches, atomic failed-download retries,
rollback after invalid/missing files and duplicate keys, country aliases and
unknown areas, leading zeros, null/zero quantities, observation counts,
numeric SPARQL filters/aggregation, shared-country joins and absence of country
descriptions. The SQL tests and RDF tests skip with an explicit reason if their
external prerequisites are absent.

Initial validation used DuckDB JDBC 1.5.6.0 and Ontop 5.5.0, plus a 10,000-row
sample of the real 2024 data and the complete country/product tables (238 areas,
226 country links, 12 omissions, 5022 products). Compose configuration was
validated. The full 30-year database and Docker services were not started.
