# BDneX - Batch Processing Guide

## Modes de traitement

### Mode unique (par défaut)
Traite un seul fichier BD avec interface interactive.

```bash
python -m bdnex -f "chemin/vers/bd.cbz"
```

### Mode batch `-b` / `--batch`
- ✓ Traite multiple fichiers BD en parallèle (4 workers par défaut)
- ✓ Désactive l'interface challenge UI interactive
- ✓ Accepte automatiquement les correspondances > 70% de confiance
- ✓ Collecte les fichiers avec faible confiance pour révision à la fin
- ✗ Ne montre pas d'interface manuelle pour chaque fichier

```bash
python -m bdnex -d "dossier/BD" -b
```

**Cas d'usage**: Traiter une collection de 100+ BD sans intervention

### Mode strict `-s` / `--strict`
- ✓ Rejette automatiquement les correspondances < 70% de confiance
- ✓ Accélère le traitement
- ✗ Saute les fichiers ambigus (ils ne reçoivent pas de métadonnées)

```bash
python -m bdnex -d "dossier/BD" -s
```

**Cas d'usage**: Traiter rapidement en acceptant de perdre les fichiers ambigus

### Mode batch + strict
- ✓ Parallélisation
- ✓ Rejette les fichiers ambigus
- ✓ Sortie CSV/JSON avec rapport

```bash
python -m bdnex -d "dossier/BD" -b -s
```

## Caractéristiques avancées

### 1. Multiprocessing
- **4 workers par défaut** (configurable via code)
- Chaque worker traite 1 fichier de manière isolée
- Les résultats sont collectés via `imap_unordered()`
- Accélération : ~4x plus rapide pour 100 BD

### 2. Retry Logic avec Exponential Backoff
- **Jusqu'à 3 tentatives** en cas d'erreur réseau
- Délais: 1s, 2s, 4s
- Évite les blocages temporaires

### 3. Cache persistant des sitemaps
- **TTL: 24h**
- Stockage: `~/.config/bdnex/batch_results/cache/sitemaps_cache.json`
- Premier démarrage: 5-10s (télécharge les sitemaps)
- Démarrages suivants: < 1s (utilise le cache)

### 4. Logging détaillé

#### JSON Output
```json
{
  "batch_start": "2025-12-29T14:30:00",
  "batch_end": "2025-12-29T14:45:00",
  "duration_seconds": 900,
  "total_files": 150,
  "successful": 145,
  "failed": 5,
  "low_confidence": 3,
  "results": [...]
}
```

Stockage: `~/.config/bdnex/batch_results/batch_YYYYMMDD_HHMMSS.json`

#### CSV Output
Format tabulaire pour Excel/analyse

Stockage: `~/.config/bdnex/batch_results/batch_YYYYMMDD_HHMMSS.csv`

## Workflow recommandé pour une grande collection

### Étape 1: Initialiser les sitemaps
```bash
python -m bdnex -i
```
Télécharge les sitemaps de Bédéthèque (10-30s)

### Étape 2: Traitement batch avec mode normal
```bash
python -m bdnex -d "/dossier/BD" -b
```
- Traite en parallèle
- Génère rapport JSON/CSV
- Les fichiers avec faible confiance sont loggés

### Étape 3: Analyser le rapport
```bash
cat ~/.config/bdnex/batch_results/batch_LATEST.json
# ou avec Excel:
# ~/.config/bdnex/batch_results/batch_LATEST.csv
```

### Étape 4 (optionnel): Traiter manuellement les fichiers ambigus
```bash
python -m bdnex -f "/dossier/BD/fichier_ambigue.cbz"
# Mode interactif avec challenge UI
```

## Performances

### Benchmarks (sur collection de 100 BD)
| Mode | Temps | Notes |
|------|-------|-------|
| Single file | 10-20s | 1 fichier avec UI |
| Batch (4 workers) | ~3-4 min | 100 fichiers, parallèle |
| Batch + Strict | ~2 min | Sans UI interactive |
| Batch + Cache hit | ~2 min | Sitemaps en cache |

### Optimisations possibles
- Augmenter à 8 workers: `AdvancedBatchProcessor(..., num_workers=8)`
- Réduire à 1 worker: Test mode, débugage
- Passer `interactive=False`: Élimine l'attente de réponse manuelle

## Mode non-interactif pour les scripts

En mode batch, les erreurs n'ouvrent pas de prompt interactif:
- `search_album_from_sitemaps_interactive()` lève une exception au lieu de bloquer
- Les retries gèrent automatiquement les erreurs réseau
- Les fichiers échoués sont loggés dans le CSV pour analyse

```python
from bdnex.lib.advanced_batch_processor import AdvancedBatchProcessor

processor = AdvancedBatchProcessor(batch_mode=True, strict_mode=True)
results = processor.process_files_parallel(file_list)
processor.print_summary(results)
```

## Dépannage

### Cache expiré
Le cache se réinitialise automatiquement après 24h. Pour forcer une réinitialisation:
```bash
rm ~/.config/bdnex/batch_results/cache/sitemaps_cache.json
python -m bdnex -i
```

### Trop lent en batch
- Vérifier: `stat ~/.config/bdnex/batch_results/cache/sitemaps_cache.json`
- Si ancien (> 24h): Réinitialiser le cache
- Si premier run: Normal (5-10s pour télécharger sitemaps)

### Erreurs réseau persistantes
- Retry logic automatique (3 tentatives)
- Vérifier la connexion: `ping bedetheque.com`
- Vérifier les logs JSON pour détails

### Un fichier bloque le traitement parallèle
- Les workers sont isolés, un crash n'affecte pas les autres
- Vérifier le CSV pour la raison de l'erreur
- Retraiter ce fichier en mode single: `python -m bdnex -f "fichier.cbz"`
