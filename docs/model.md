# BACI HS92 V202601 (2024): model and country links

Command examples run from the repository root.

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

The versioned policy is `database/baci-country-exclusions.csv`. SQL preserves the
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
