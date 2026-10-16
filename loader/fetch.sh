#!/bin/sh
set -eu
set -f
# Each artifact is downloaded to a partial file and renamed only on success.
data_dir=${DATA_DIR:-/data}
jdbc_dir=${JDBC_DIR:-/jdbc}
base=${BACI_BASE_URL:-https://maven.inf-ai.duckdns.org/releases/org/aksw/data/thirdparty/fr/cepii/baci/HS92_V202601/1}
base=${base%/}
mkdir -p "$data_dir" "$jdbc_dir"
fetch() {
    target=$1
    url=$2
    if [ ! -s "$target" ]; then
        curl -fL --retry 3 --connect-timeout 20 -o "$target.part" "$url"
        test -s "$target.part"
        mv "$target.part" "$target"
    fi
}
# Validate the complete selection before downloading.
has_year=0
for year in ${BACI_YEARS:-2024}; do
    case "$year" in
        199[5-9]|20[01][0-9]|202[0-4]) has_year=1 ;;
        *) echo "fetch: invalid BACI year: $year (expected 1995..2024)" >&2; exit 1 ;;
    esac
done
if [ "$has_year" = 0 ]; then
    echo 'fetch: select at least one year' >&2
    exit 1
fi
printf 'year\n' > "$data_dir/years.csv.part"
for year in ${BACI_YEARS:-2024}; do
    file="BACI_HS92_Y${year}_V202601.csv.zst"
    fetch "$data_dir/$file" "$base/HS92_V202601-1-$file"
    printf '%s\n' "$year" >> "$data_dir/years.csv.part"
done
for file in country_codes_V202601.csv.zst product_codes_HS92_V202601.csv.zst; do
    fetch "$data_dir/$file" "$base/HS92_V202601-1-$file"
done
fetch "$data_dir/Readme.txt" "$base/HS92_V202601-1-readme.txt"
fetch "$jdbc_dir/duckdb_jdbc-1.5.6.0.jar" 'https://repo.maven.apache.org/maven2/org/duckdb/duckdb_jdbc/1.5.6.0/duckdb_jdbc-1.5.6.0.jar'
# Commit the selection only after every required download has succeeded.
# Repeated years are harmless; SQL reads a distinct list.
mv "$data_dir/years.csv.part" "$data_dir/years.csv"
echo 'fetch: ready'
