# Chennai neighbourhood directory v1

Retrieved 13 November 2026. The frozen `chennai_neighbourhoods_v1.json` contains **207 distinct, normalized area names** with spelling aliases. It is application reference data, independent of clinic inventory, and is imported into Django `Region` rows by migrations. Administrators can edit/add areas and aliases; requests never fetch remote sources or recreate deleted areas.

## Sources and attribution

1. [Karthik / yankarto, Chennai neighborhood coordinates dataset](https://github.com/yankarto/Chennai-neighborhood-coordinates-dataset/tree/49a56f4900a71e16733c59e1806b3837169a29e3), commit `49a56f4900a71e16733c59e1806b3837169a29e3`. Vendored original: `chennai_source.csv` (176 rows; Windows-1252 encoding). Its README explicitly permits learning and other project use. Only area names are imported. Coordinates are deliberately unused: the upstream dataset has visibly inconsistent coordinates (for example, Broadway).
2. [Wikipedia contributors, Areas of Chennai, revision 1376771538](https://en.wikipedia.org/w/index.php?title=Areas_of_Chennai&oldid=1376771538). Its Location table is transcribed into `chennai_wikipedia_areas.txt` (166 rows). This supplements central-city localities absent from the CSV, including Nungambakkam, Kilpauk and Royapettah. Attribution, [revision history](https://en.wikipedia.org/w/index.php?title=Areas_of_Chennai&action=history), and [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The combined normalized directory retains this attribution and is distributed under CC BY-SA 4.0 for the Wikipedia-derived content; this does not change the application's code license.
3. [Wikipedia contributors, List of neighbourhoods of Chennai, revision 1326017160](https://en.wikipedia.org/w/index.php?title=List_of_neighbourhoods_of_Chennai&oldid=1326017160), regional list, supplies Uthandi. Same CC BY-SA 4.0 attribution applies.

## Coverage and transformations

The directory covers named neighbourhoods across north, central, south/east, and west Chennai, with selected adjacent metropolitan localities found in the source city lists (for example, Avadi and Tambaram). It is **not** an official GCC-boundary dataset, a ward map, or a claim to enumerate every informal colony/street. Administrative areas and everyday neighbourhood names have different boundaries. More localities can be added immediately in Django Admin without changing code. Area matching uses the clinic's saved neighbourhood, not GPS radius or inferred nearby locations.

The build excludes rows explicitly labelled `Suburban Chennai`, `Northern/Western/Southern-Eastern Suburbs`, and `Suburbs along ECR and OMR` from the coordinate CSV, then unions the city Location table and Uthandi supplement. The table itself contains some adjacent metro places; these are intentionally documented rather than mislabelled as guaranteed municipal limits. No clinics or patients are implied by an area existing.

Whitespace (including non-breaking spaces) is normalized, names are deduplicated, and documented spelling variants merge into canonical rows (for example, Chetput/Chetpet, Chrompet/Chromepet, Thuraipakkam/Thoraipakkam). Original spellings remain searchable as aliases. The transformations are in `build_dataset.py`. Regenerate the frozen version only when intentionally revising the dataset; migrations refer to v1 and must remain reproducible:

```powershell
python backend\care\data\build_dataset.py
```

Existing Region IDs are preserved. Legacy Velachery and Mogappair rows receive aliases through a non-destructive merge migration. Never use a directory refresh to delete clinics or reassign existing appointments.
