"""Reproduce the frozen v1 directory from the attributed, checked-in source files."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALIASES = {
    'Chetput': 'Chetpet', 'Chrompet': 'Chromepet', 'Guduvancheri': 'Guduvanchery',
    'ICF': 'ICF Colony', 'Kattivakkam': 'Kathivakkam', 'MGR Nagar': 'M.G.R. Nagar',
    'MKB Nagar': 'M.K.B. Nagar', 'Moulivakkam': 'Mowlivakkam', 'Pattravakkam': 'Pattaravakkam',
    'Purasaiwalkam': 'Purasawalkam', 'Ramavaram': 'Ramapuram', 'Tharamani': 'Taramani',
    'Thirumullaivoyal': 'Thirumullaivayal', 'Thiruninravur': 'Thirunindravur',
    'Thiruvallur': 'Tiruvallur', 'Tiruverkadu': 'Thiruverkadu', 'Thiruvotriyur': 'Tiruvottiyur',
    'Thuraipakkam': 'Thoraipakkam', 'Tiruvallikeni': 'Triplicane',
    'manapakkam': 'Manapakkam', 'Mathur MMDA': 'Mathur', 'St.Thomas Mount': 'St. Thomas Mount',
}
rows = {}

def add(name, source):
    name = ' '.join(name.split())
    canonical = ALIASES.get(name, name)
    item = rows.setdefault(canonical, {'area': canonical, 'aliases': [], 'sources': []})
    if canonical != name and name not in item['aliases']:
        item['aliases'].append(name)
    if source not in item['sources']:
        item['sources'].append(source)

for row in csv.DictReader((ROOT / 'chennai_source.csv').read_text(encoding='cp1252').splitlines()):
    if 'Suburb' not in row['Location']:
        add(row['Area'], 'coordinates-dataset')
for name in (ROOT / 'chennai_wikipedia_areas.txt').read_text(encoding='utf-8').splitlines():
    if name.strip():
        add(name, 'areas-of-chennai')
# Additional city neighbourhoods listed in the companion regional directory.
for name in ['Uthandi']:
    add(name, 'regional-supplement')
for canonical, aliases in {'T. Nagar': ['T Nagar', 'Thyagaraya Nagar'], 'K.K. Nagar': ['KK Nagar'], 'Mogappair': ['Mugappair'], 'Puzhuthivakkam - Ullagaram': ['Puzhuthivakkam', 'Ullagaram']}.items():
    rows[canonical]['aliases'].extend(aliases)
data = {'version': 1, 'retrieved': '2026-11-13', 'coverage': 'Chennai city neighbourhoods and selected adjoining metropolitan localities; not ward boundaries or an exhaustive gazetteer of every colony.', 'sources': {
    'coordinates-dataset': 'https://github.com/yankarto/Chennai-neighborhood-coordinates-dataset/tree/49a56f4900a71e16733c59e1806b3837169a29e3',
    'areas-of-chennai': 'https://en.wikipedia.org/w/index.php?title=Areas_of_Chennai&oldid=1376771538',
    'regional-supplement': 'https://en.wikipedia.org/wiki/List_of_neighbourhoods_of_Chennai',
}, 'regions': sorted(rows.values(), key=lambda row: row['area'].casefold())}
(ROOT / 'chennai_neighbourhoods_v1.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(f"Wrote {len(rows)} distinct neighbourhoods")
