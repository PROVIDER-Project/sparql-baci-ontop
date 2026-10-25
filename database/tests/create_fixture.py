"""Write small zstd inputs for opt-in Maven/Docker lifecycle validation."""
import csv
from pathlib import Path
import subprocess
import sys

def write(directory, name, header, rows):
    plain = directory / (name + '.plain')
    with plain.open('w', newline='') as f:
        writer = csv.writer(f); writer.writerow(header); writer.writerows(rows)
    subprocess.run(['zstd', '-qf', str(plain), '-o', str(directory / name)], check=True)
    plain.unlink()

if __name__ == '__main__':
    directory = Path(sys.argv[1]); directory.mkdir(parents=True, exist_ok=True)
    write(directory, 'BACI_HS92_Y2024_V202601.csv.zst', ['t','i','j','k','v','q'], [
        [2024,276,251,'010111',1.25,0], [2024,58,276,'010119',2,'NA'],
        [2024,736,276,'010119',3,1.5], [2024,490,276,'010119',4,''],
        [2024,999,276,'010120',0,0], [2024,276,251,'010121','',1]])
    write(directory, 'country_codes_V202601.csv.zst',
          ['country_code','country_name','country_iso2','country_iso3'], [
          [276,'Germany','DE','DEU'],[251,'France','FR','FRA'],[56,'Belgium','BE','BEL'],
          [58,'Belgium-Luxembourg','BE','BEL'],[729,'Sudan','SD','SDN'],
          [736,'Historical Sudan','SD','SDN'],[490,'Other Asia, nes','','S19'],
          [516,'Namibia','','NAM']])
    write(directory, 'product_codes_HS92_V202601.csv.zst', ['code','description'],
          [['010111','Pure-bred breeding horses'],['010119','Other live horses']])
    (directory / 'Readme.txt').write_text('Synthetic fixture; never publish as source data.\n')
