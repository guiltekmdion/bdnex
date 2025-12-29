# BDneX Quick Start Guide

Bienvenue dans BDneX! Ce guide vous aide à commencer en 5 minutes.

---

## 📥 Installation

### Requirements
- Python 3.8+
- pip ou conda
- ~500MB d'espace disque

### Installation

```bash
# Option 1: Via pip (simple)
pip install bdnex

# Option 2: Via git (développement)
git clone https://github.com/guiltekmdion/bdnex.git
cd bdnex
pip install -e .

# Vérifier l'installation
bdnex --version
```

---

## 🚀 Your First Run

### Interactive Mode (Easy)

```bash
# Processer un fichier BD
bdnex --input mon_bd.cbz

# L'application demande la confirmation pour chaque match
# Utiliser les flèches ↑↓ pour naviguer et ENTER pour confirmer
```

**Résultat**: Crée `ComicInfo.xml` avec les métadonnées

### Batch Mode (Lots de fichiers)

```bash
# Processer 100 fichiers en parallèle
bdnex --batch --input dossier_bd/

# L'application montre la progression
# À la fin, affiche les fichiers problématiques pour révision
```

**Résultat**:
- Crée `ComicInfo.xml` pour chaque BD
- Génère rapport `batch_results/batch_*.json`

### Strict Mode (Pas de questions)

```bash
# Utiliser le meilleur match automatiquement
bdnex --strict --input mon_bd.cbz

# Aucune intervention, utilise le match avec le meilleur score
```

---

## ⚙️ Configuration

### Fichier de Configuration

La première fois, BDneX crée `~/.bdnex/bdnex.yaml`:

```yaml
# Nombre de travailleurs parallèles (4 par défaut)
num_workers: 4

# Qualité minimale pour accepter un match (0-100)
minimum_score: 60

# Télécharger les couvertures
download_covers: true

# Format de nommage
# {album_id} {album_title} - {series_number}
naming_pattern: "{album_id} {album_title}"
```

### Personnalisation

Éditer le fichier de config:
- Windows: `%USERPROFILE%\.bdnex\bdnex.yaml`
- Linux/Mac: `~/.bdnex/bdnex.yaml`

---

## 💡 Common Use Cases

### Case 1: Processer une collection complète

```bash
cd /chemin/vers/ma/collection/
bdnex --batch --input .

# Crée ComicInfo.xml pour chaque BD
# Génère rapport détaillé à la fin
```

### Case 2: Vérifier les résultats d'un batch précédent

```bash
# Revenir au défi pour les fichiers problématiques
bdnex --challenge --from-batch batch_session_1

# Utiliser l'interface interactive pour confirmer/corriger
```

### Case 3: Actualiser les métadonnées

```bash
# Force le re-processing même si déjà traité
bdnex --force --input mon_bd.cbz

# Télécharge les nouvelles infos de la base de données
```

---

## 🎯 Understanding the Output

### ComicInfo.xml

Fichier standard pour les BD (utilisé par Calibre, ComiXology, etc.):

```xml
<?xml version="1.0" encoding="utf-8"?>
<ComicInfo xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Series>Asterix</Series>
  <Title>Le Gaulois</Title>
  <Number>1</Number>
  <Year>1961</Year>
  <Count>72</Count>
  <Summary>Les aventures d'Astérix...</Summary>
  <CoverImage>JPEG;base64,/9j/4AAQSkZJRg...</CoverImage>
</ComicInfo>
```

### Batch Report

Après un batch, consulter `batch_results/batch_*.json`:

```json
{
  "session_id": "20240115_093022",
  "mode": "batch",
  "start_time": "2024-01-15T09:30:22Z",
  "end_time": "2024-01-15T09:35:45Z",
  "files_processed": 50,
  "files_successful": 48,
  "success_rate": 96.0,
  "files_needing_attention": [
    {
      "filename": "unknown_comic.cbz",
      "reason": "no_match",
      "attempts": 1,
      "recommended_action": "manual_search"
    }
  ]
}
```

---

## 🔧 Troubleshooting

### Problem: "Cannot find album"

**Solution**: Vérifier le titre BD
```bash
# Activer le mode verbose pour voir les recherches
bdnex --input mon_bd.cbz --verbose
```

### Problem: "Network error" ou "Cannot fetch sitemap"

**Solution**: Vérifier la connexion Internet
```bash
# Bdnex reessaie 3 fois avec délai exponentiel
# Attendre quelques secondes et réessayer
bdnex --input mon_bd.cbz --retry
```

### Problem: "No permission to write"

**Solution**: Vérifier les droits d'accès
```bash
# Windows
icacls "D:\BD_Collection" /grant "%USERNAME%":F /t

# Linux/Mac
chmod -R u+w /chemin/vers/collection/
```

### Problem: "Archive is corrupted"

**Solution**: Le fichier CBD/CBZ peut être corrompu
```bash
# Tester le fichier
unzip -t mon_bd.cbz  # CBZ est un ZIP

# Ou avec 7-Zip
7z t mon_bd.cbr
```

---

## 📊 Monitoring Performance

### Check Progress

Pendant un batch, le terminal affiche:

```
Processing files...
[████████████░░░░░░░░] 60% (30/50)
```

### View Statistics

Après un batch:

```bash
# Afficher les stats du dernier batch
bdnex --stats --last

# Afficher les stats d'une session spécifique
bdnex --stats --session batch_session_1
```

### Logs

Logs détaillés disponibles dans:
- Windows: `%USERPROFILE%\.bdnex\logs\`
- Linux/Mac: `~/.bdnex/logs/`

---

## 🔄 Advanced Features (Batch Mode)

### Parallel Processing

```bash
# Utiliser 8 workers au lieu du défaut 4
bdnex --batch --workers 8 --input collection/

# Sur un CPU 4-core, max = 4 (ne pas exagérer)
```

### Resume Interrupted Batch

```bash
# Reprendre un batch interrompu
bdnex --batch --resume batch_session_1 --input collection/

# Saute les fichiers déjà traités
```

### Skip Already Processed

```bash
# Traiter uniquement les nouveaux fichiers
bdnex --batch --skip-processed --input collection/
```

---

## 📚 Learning More

### Next Steps

1. **Lire** `BATCH_PROCESSING.md` - Guide complet du mode batch
2. **Explorer** `ROADMAP.md` - Fonctionnalités futures
3. **Consulter** `README.md` - Vue d'ensemble du projet

### Getting Help

```bash
# Aide générale
bdnex --help

# Aide sur une commande spécifique
bdnex --batch --help

# Version
bdnex --version
```

### Community

- GitHub Issues: https://github.com/guiltekmdion/bdnex/issues
- Discussions: https://github.com/guiltekmdion/bdnex/discussions

---

## 🎓 Understanding BDneX

### What BDneX Does

1. **Identify** - Reconnaît la BD via le titre du fichier
2. **Search** - Cherche dans la base de données BDthèque
3. **Match** - Propose le meilleur match avec score de confiance
4. **Confirm** - Vous demande si c'est correct (mode interactif)
5. **Save** - Sauvegarde les métadonnées dans `ComicInfo.xml`
6. **Download** - Télécharge optionnellement la couverture

### Data Sources

- **Primary**: [Bédéthèque](https://www.bedetheque.com) - Base de données française
- **Covers**: Extraites de la page Bédéthèque
- **Local**: Cache persistent (24h) pour performances

### Privacy

BDneX:
- ✅ Stocke les données locally dans `~/.bdnex/`
- ✅ Cache HTTP pendant 24h
- ✅ N'envoie que les titres à Bédéthèque (HTTPS)
- ❌ Ne transmet aucune information personnelle
- ❌ Ne modifie pas les fichiers BD d'origine

---

## 🚀 Tips & Tricks

### Tip 1: Batch + Interactive

```bash
# D'abord faire un batch pour les BDs simples
bdnex --batch --input collection/

# Puis traiter les erreurs en mode interactif
bdnex --challenge --from-batch batch_session_1
```

### Tip 2: Naming Conventions

```yaml
# Dans ~/.bdnex/bdnex.yaml
# Utiliser {series} {number} {title}
naming_pattern: "{series} - {number:03d} - {title}"

# Résultat: Asterix - 001 - Le Gaulois
```

### Tip 3: Batch Dry-Run

```bash
# Voir ce qui serait fait sans modifier
bdnex --batch --dry-run --input collection/

# Affiche les actions proposées
```

### Tip 4: Resume Long Batches

```bash
# Batch peut prendre du temps pour 1000+ fichiers
# C'est OK d'interrompre avec Ctrl+C

# Plus tard, reprendre
bdnex --batch --resume last --input collection/
```

---

## 🎉 You're Ready!

Vous avez maintenant tout ce qu'il faut pour:
- ✅ Processer une seule BD
- ✅ Processer un lot de BDs
- ✅ Personnaliser le comportement
- ✅ Gérer les erreurs
- ✅ Monitorer la performance

**Prochaines étapes**:

1. Processer votre première BD: `bdnex --input test.cbz`
2. Explorer les options: `bdnex --help`
3. Lire le guide batch complet: `BATCH_PROCESSING.md`
4. Rejoindre la communauté: discussions GitHub

---

## ❓ FAQ

**Q: Puis-je modifier les fichiers BD?**
A: Non, BDneX crée/modifie uniquement `ComicInfo.xml` à l'intérieur de l'archive.

**Q: Dois-je être connecté?**
A: Oui, pour la première recherche. Ensuite, le cache offline fonctionne 24h.

**Q: Quel est le meilleur score?**
A: 95%+ = très probable, 75-94% = probable, <75% = demande confirmation

**Q: Comment désactiver les couvertures?**
A: Dans `~/.bdnex/bdnex.yaml`: `download_covers: false`

**Q: Puis-je utiliser avec Calibre?**
A: Oui! Calibre lit automatiquement `ComicInfo.xml`

---

**Happy reading! 📚🎨**

Pour plus de détails: https://github.com/guiltekmdion/bdnex
