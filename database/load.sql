-- BACI HS92 V202601. Materialize relational tables only, never RDF.
-- The manifest selects files explicitly: stale cached years are not ingested.
BEGIN TRANSACTION;
CREATE OR REPLACE TABLE baci_year (YEAR INTEGER PRIMARY KEY CHECK (YEAR BETWEEN 1995 AND 2024));
INSERT INTO baci_year SELECT DISTINCT year FROM read_csv('/opt/ontop/input/years.csv', header=true, columns={'year':'INTEGER'});
SELECT CASE WHEN count(*) > 0 THEN true ELSE error('No BACI years selected') END FROM baci_year;
SET VARIABLE baci_files = (SELECT list('/data/BACI_HS92_Y' || YEAR || '_V202601.csv.zst' ORDER BY YEAR) FROM baci_year);

CREATE OR REPLACE TABLE baci (
    YEAR VARCHAR NOT NULL CHECK (regexp_full_match(YEAR, '(199[5-9]|20[01][0-9]|202[0-4])')),
    EXPORTER_CODE VARCHAR NOT NULL CHECK (regexp_full_match(EXPORTER_CODE, '[0-9]+')),
    IMPORTER_CODE VARCHAR NOT NULL CHECK (regexp_full_match(IMPORTER_CODE, '[0-9]+')),
    PRODUCT_CODE VARCHAR NOT NULL CHECK (regexp_full_match(PRODUCT_CODE, '[0-9]{6}')),
    TRADE_VALUE DOUBLE, QUANTITY DOUBLE,
    OBSERVATION_LOCAL_NAME VARCHAR NOT NULL,
    TRADE_VALUE_LEXICAL VARCHAR, QUANTITY_LEXICAL VARCHAR
);
INSERT INTO baci
SELECT CAST(t AS VARCHAR), CAST(i AS VARCHAR), CAST(j AS VARCHAR), k, v, q,
       CAST(t AS VARCHAR) || '-' || CAST(i AS VARCHAR) || '-' || CAST(j AS VARCHAR) || '-' || k,
       CAST(v AS VARCHAR), CAST(q AS VARCHAR)
FROM read_csv(getvariable('baci_files'), header=true, auto_detect=false,
    columns={'t':'INTEGER','i':'INTEGER','j':'INTEGER','k':'VARCHAR','v':'DOUBLE','q':'DOUBLE'},
    nullstr=['', 'NA'], filename=true)
WHERE CASE WHEN filename = '/data/BACI_HS92_Y' || t || '_V202601.csv.zst'
    THEN true ELSE error('BACI row year does not match its selected file') END;
-- Truthful uniqueness for the observation lens; a duplicate fails the transaction.
CREATE UNIQUE INDEX baci_observation_local_name_idx ON baci (OBSERVATION_LOCAL_NAME);
CREATE INDEX baci_year_idx ON baci (YEAR);
CREATE INDEX baci_exporter_idx ON baci (EXPORTER_CODE);
CREATE INDEX baci_importer_idx ON baci (IMPORTER_CODE);
CREATE INDEX baci_product_idx ON baci (PRODUCT_CODE);
CREATE INDEX baci_value_idx ON baci (TRADE_VALUE_LEXICAL);
CREATE INDEX baci_quantity_idx ON baci (QUANTITY_LEXICAL);

CREATE OR REPLACE TABLE baci_country_definition (
    AREA_CODE VARCHAR PRIMARY KEY, AREA_NAME VARCHAR NOT NULL,
    SOURCE_ISO2 VARCHAR, SOURCE_ISO3 VARCHAR
);
INSERT INTO baci_country_definition
SELECT CAST(country_code AS VARCHAR), country_name, country_iso2, country_iso3
FROM read_csv('/data/country_codes_V202601.csv.zst', header=true, auto_detect=false,
    columns={'country_code':'INTEGER','country_name':'VARCHAR','country_iso2':'VARCHAR','country_iso3':'VARCHAR'}, nullstr='');
CREATE OR REPLACE TABLE baci_country_exclusion (AREA_CODE VARCHAR PRIMARY KEY, REASON VARCHAR NOT NULL);
INSERT INTO baci_country_exclusion
SELECT area_code, reason FROM read_csv('/opt/ontop/input/baci-country-exclusions.csv', header=true,
    columns={'area_code':'VARCHAR','reason':'VARCHAR'});

-- Include all supplied definitions and observed endpoints. No fact is dropped.
CREATE OR REPLACE TABLE baci_area (
    AREA_CODE VARCHAR PRIMARY KEY, AREA_NAME VARCHAR, SOURCE_ISO2 VARCHAR, SOURCE_ISO3 VARCHAR
);
INSERT INTO baci_area
WITH codes AS (
    SELECT AREA_CODE FROM baci_country_definition
    UNION SELECT EXPORTER_CODE FROM baci
    UNION SELECT IMPORTER_CODE FROM baci
)
SELECT c.AREA_CODE, d.AREA_NAME, d.SOURCE_ISO2, d.SOURCE_ISO3
FROM codes c LEFT JOIN baci_country_definition d USING (AREA_CODE);

-- Eligibility is audited for V202601. ISO3-shaped text alone is not proof of
-- identity: historical/residual codes are excluded even with current ISO3s.
CREATE OR REPLACE TABLE baci_area_country (
    AREA_CODE VARCHAR PRIMARY KEY, COUNTRY_CODE VARCHAR NOT NULL UNIQUE
);
INSERT INTO baci_area_country
SELECT a.AREA_CODE, a.SOURCE_ISO3 FROM baci_area a
LEFT JOIN baci_country_exclusion e USING (AREA_CODE)
WHERE e.AREA_CODE IS NULL AND regexp_full_match(a.SOURCE_ISO3, '[A-Z]{3}');
CREATE OR REPLACE TABLE baci_area_country_unresolved (
    AREA_CODE VARCHAR PRIMARY KEY, SOURCE_ISO3 VARCHAR, REASON VARCHAR NOT NULL
);
INSERT INTO baci_area_country_unresolved
SELECT a.AREA_CODE, a.SOURCE_ISO3,
    coalesce(e.REASON, CASE WHEN a.AREA_NAME IS NULL THEN 'Missing source country definition'
                          ELSE 'Missing or nonstandard source ISO3 code' END)
FROM baci_area a LEFT JOIN baci_country_exclusion e USING (AREA_CODE)
LEFT JOIN baci_area_country c USING (AREA_CODE) WHERE c.AREA_CODE IS NULL;

CREATE OR REPLACE TABLE baci_product (PRODUCT_CODE VARCHAR PRIMARY KEY, DESCRIPTION VARCHAR);
INSERT INTO baci_product
WITH definitions AS (
    SELECT code, description FROM read_csv('/data/product_codes_HS92_V202601.csv.zst', header=true,
        columns={'code':'VARCHAR','description':'VARCHAR'}, auto_detect=false)
), codes AS (
    SELECT code AS PRODUCT_CODE FROM definitions UNION SELECT PRODUCT_CODE FROM baci
)
SELECT c.PRODUCT_CODE, d.description FROM codes c LEFT JOIN definitions d ON c.PRODUCT_CODE=d.code;
-- Duplicated definitions fail the primary key rather than fanning out.
ANALYZE;
COMMIT;
