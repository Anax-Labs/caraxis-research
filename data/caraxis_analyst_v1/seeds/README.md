# Seeds

Seed files are normalized inputs for `scripts/build_dataset.py`.

| Path | Source | Refresh |
|---|---|---|
| `attack/techniques.json` | MITRE ATT&CK Enterprise | `python scripts/fetch_seeds.py` |
| `cve/samples.json` | NVD API | `python scripts/fetch_seeds.py` |
| `sigma/samples.yaml` | Bundled Sigma examples | Add rules manually or from SigmaHQ (DRL 1.1) |

Bundled samples let you generate a pilot dataset offline. Use `fetch_seeds.py` on Colab or any network-connected machine for larger seed sets.
