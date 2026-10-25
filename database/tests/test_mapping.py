"""Actual DuckDB/JDBC ingestion and optional Ontop 5.5 query tests.

Set DUCKDB_JDBC_JAR to the JDBC jar; set ONTOP_CLI to an extracted CLI's ontop
script (with the same JDBC jar in its jdbc directory) for RDF integration tests.
"""
import csv
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
JAR = Path(os.environ.get('DUCKDB_JDBC_JAR', ROOT / 'target/test-dependencies/duckdb_jdbc-1.5.6.0.jar'))
CLI = os.environ.get('ONTOP_CLI')


@unittest.skipUnless(JAR.is_file() and shutil.which('java') and shutil.which('javac') and shutil.which('zstd'),
                     'Requires JDK, zstd and DuckDB JDBC (DUCKDB_JDBC_JAR)')
class MappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classes = tempfile.TemporaryDirectory()
        subprocess.run(['javac', '-d', cls.classes.name, str(ROOT / 'tests/DuckDbScripts.java')], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.classes.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.database = self.directory / 'baci.duckdb'
        self.sql = self.directory / 'load.sql'
        self.sql.write_text((ROOT / 'load.sql').read_text()
                            .replace('/opt/ontop/input/years.csv', str(self.directory / 'years.csv'))
                            .replace('/data/', str(self.directory) + '/')
                            .replace('/opt/ontop/input/', str(ROOT) + '/'))
        (self.directory / 'years.csv').write_text('year\n2024\n2024\n')
        self.rows = [
            [2024, 276, 251, '010111', 1.25, 0],
            [2024, 58, 276, '010119', 2, 'NA'],
            [2024, 736, 276, '010119', 3, 1.5],
            [2024, 490, 276, '010119', 4, ''],
            [2024, 999, 276, '010120', 0, 0],
            [2024, 276, 251, '010121', '', 1],
        ]
        self.countries = [
            [276, 'Germany', 'DE', 'DEU'], [251, 'France', 'FR', 'FRA'],
            [56, 'Belgium', 'BE', 'BEL'], [58, 'Belgium-Luxembourg (...1998)', 'BE', 'BEL'],
            [729, 'Sudan', 'SD', 'SDN'], [736, 'Sudan (...2011)', 'SD', 'SDN'],
            [490, 'Other Asia, nes', '', 'S19'], [697, 'Europe EFTA, nes', '', 'R20'],
            [711, 'Southern African Customs Union (...1999)', '', 'ZA1'],
            [516, 'Namibia', '', 'NAM'],
        ]
        self.write_csv('country_codes_V202601.csv.zst',
                       ['country_code','country_name','country_iso2','country_iso3'], self.countries)
        self.write_csv('product_codes_HS92_V202601.csv.zst', ['code','description'],
                       [['010111','Pure-bred breeding horses'],['010119','Other live horses']])
        self.write_facts()
        # A stale cached year must not leak into the selected data.
        self.write_csv('BACI_HS92_Y2023_V202601.csv.zst', ['t','i','j','k','v','q'],
                       [[2023, 276, 251, '010111', 999, 2]])

    def write_csv(self, name, header, rows):
        plain = self.directory / (name + '.csv')
        with plain.open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(header)
            writer.writerows(rows)
        subprocess.run(['zstd', '-qf', str(plain), '-o', str(self.directory / name)], check=True)
        plain.unlink()

    def write_facts(self):
        self.write_csv('BACI_HS92_Y2024_V202601.csv.zst', ['t','i','j','k','v','q'], self.rows)

    def run_sql(self, path):
        return subprocess.run(['java', '-cp', self.classes.name + os.pathsep + str(JAR),
                               'DuckDbScripts', str(self.database), str(path)],
                              capture_output=True, text=True, timeout=120)

    def load(self):
        result = self.run_sql(self.sql)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_sql(self, sql):
        path = self.directory / 'assert.sql'
        path.write_text(sql)
        result = self.run_sql(path)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_ingestion_country_policy_and_rebuild(self):
        self.load()
        self.assert_sql("""
SELECT CASE WHEN count(*)=6 AND min(YEAR)='2024' THEN true ELSE error('selection') END FROM baci;
SELECT CASE WHEN PRODUCT_CODE='010111' AND TRADE_VALUE=1.25 AND QUANTITY=0 AND QUANTITY_LEXICAL='0.0' THEN true ELSE error('values') END FROM baci WHERE OBSERVATION_LOCAL_NAME='2024-276-251-010111';
SELECT CASE WHEN count(*)=2 THEN true ELSE error('missing quantities') END FROM baci WHERE QUANTITY IS NULL;
SELECT CASE WHEN count(*)=5 THEN true ELSE error('null value lens') END FROM baci WHERE TRADE_VALUE IS NOT NULL;
SELECT CASE WHEN count(*)=5 THEN true ELSE error('country identity count') END FROM baci_area_country;
SELECT CASE WHEN count(*)=0 THEN true ELSE error('historical or residual country link') END FROM baci_area_country WHERE AREA_CODE IN ('58','736','490','697','711','999');
SELECT CASE WHEN count(*)=1 THEN true ELSE error('Namibia without ISO2') END FROM baci_area_country WHERE AREA_CODE='516' AND COUNTRY_CODE='NAM';
SELECT CASE WHEN count(*)=6 THEN true ELSE error('auditable omissions') END FROM baci_area_country_unresolved;
SELECT CASE WHEN count(*)=1 THEN true ELSE error('unknown area retained') END FROM baci_area WHERE AREA_CODE='999' AND AREA_NAME IS NULL;
SELECT CASE WHEN count(*)=4 THEN true ELSE error('product codes including missing definitions') END FROM baci_product;
SELECT CASE WHEN count(*)=7 AND sum(CAST(is_unique AS INTEGER))=1 THEN true ELSE error('lookup indexes') END FROM duckdb_indexes() WHERE table_name='baci';
""")
        self.load()

    def test_duplicate_fact_rolls_back(self):
        self.load()
        self.rows.append(list(self.rows[0]))
        self.write_facts()
        self.assertNotEqual(self.run_sql(self.sql).returncode, 0)
        self.assert_sql("SELECT CASE WHEN count(*)=6 THEN true ELSE error('rollback') END FROM baci;")

    def test_missing_selected_year_rolls_back(self):
        self.load()
        (self.directory / 'years.csv').write_text('year\n2022\n')
        self.assertNotEqual(self.run_sql(self.sql).returncode, 0)
        self.assert_sql("SELECT CASE WHEN count(*)=6 THEN true ELSE error('rollback') END FROM baci;")

    def test_wrong_year_or_invalid_product_fails(self):
        for field, invalid in [(0, 2023), (3, '10111')]:
            with self.subTest(field=field):
                original = self.rows[0][field]
                self.rows[0][field] = invalid
                self.write_facts()
                self.assertNotEqual(self.run_sql(self.sql).returncode, 0)
                self.rows[0][field] = original

    def test_duplicate_country_definition_rolls_back(self):
        self.load()
        self.countries.append(list(self.countries[0]))
        self.write_csv('country_codes_V202601.csv.zst',
                       ['country_code','country_name','country_iso2','country_iso3'], self.countries)
        self.assertNotEqual(self.run_sql(self.sql).returncode, 0)
        self.assert_sql("SELECT CASE WHEN count(*)=6 THEN true ELSE error('rollback') END FROM baci;")

    def test_multiple_selected_years(self):
        (self.directory / 'years.csv').write_text('year\n2023\n2024\n')
        self.load()
        self.assert_sql("SELECT CASE WHEN count(*)=7 AND count(DISTINCT YEAR)=2 THEN true ELSE error('multiple years') END FROM baci;")

    @unittest.skipUnless(CLI and Path(CLI).is_file(), 'Set ONTOP_CLI for RDF integration tests')
    def test_ontop_rdf(self):
        self.load()
        properties = self.directory / 'baci.properties'
        properties.write_text((ROOT.parent / 'endpoint/ontop/baci.properties').read_text()
                              .replace('/data/baci.duckdb', str(self.database)))
        queries = [
            ('SELECT (COUNT(*) AS ?n) WHERE { ?o a <http://purl.org/linked-data/cube#Observation> }', ['5']),
            ('SELECT ?p ?v ?q WHERE { <https://example.org/baci/observation/HS92_V202601/2024-276-251-010111> <https://example.org/baci/vocab/product> ?p; <http://purl.org/linked-data/sdmx/2009/measure#obsValue> ?v; <https://example.org/baci/vocab/quantity> ?q }', ['https://example.org/baci/product/HS92/010111', '1.25', '0.0']),
            ('SELECT (SUM(?v) AS ?sum) WHERE { ?o <http://purl.org/linked-data/sdmx/2009/measure#obsValue> ?v FILTER(?v > 1) }', ['10.25']),
            ('SELECT ?area WHERE { ?area <https://example.org/baci/vocab/hasCountry> <https://example.org/country/BEL> }', ['https://example.org/baci/area/56']),
            ('SELECT (COUNT(*) AS ?n) WHERE { ?o <http://purl.org/linked-data/sdmx/2009/measure#obsValue> ?v FILTER NOT EXISTS { ?o <https://example.org/baci/vocab/quantity> ?q } }', ['2']),
            ('SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o FILTER(STRSTARTS(STR(?s), "https://example.org/country/")) }', ['0']),
        ]
        queries.append(('SELECT (DATATYPE(?year) AS ?yt) (DATATYPE(?v) AS ?vt) (DATATYPE(?q) AS ?qt) WHERE { <https://example.org/baci/observation/HS92_V202601/2024-276-251-010111> <http://purl.org/linked-data/sdmx/2009/dimension#refPeriod> ?year; <http://purl.org/linked-data/sdmx/2009/measure#obsValue> ?v; <https://example.org/baci/vocab/quantity> ?q }', ['http://www.w3.org/2001/XMLSchema#gYear', 'http://www.w3.org/2001/XMLSchema#double', 'http://www.w3.org/2001/XMLSchema#double']))
        for query, expected in queries:
            with self.subTest(query=query):
                path = self.directory / 'query.rq'
                output = self.directory / 'result.csv'
                path.write_text(query)
                result = subprocess.run(['bash', CLI, 'query', '-m', str(ROOT.parent / 'endpoint/ontop/baci.r2rml.ttl'),
                                         '-p', str(properties), '-c', str(ROOT.parent / 'endpoint/ontop/baci-constraints.lst'),
                                         '--lenses', str(ROOT.parent / 'endpoint/ontop/baci-lenses.json'), '-q', str(path),
                                         '-o', str(output)], capture_output=True, text=True, timeout=120)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue(output.exists(), result.stdout + result.stderr)
                rows = list(csv.reader(output.read_text().splitlines()))
                self.assertEqual(rows[1:], [expected], output.read_text())


if __name__ == '__main__':
    unittest.main()
