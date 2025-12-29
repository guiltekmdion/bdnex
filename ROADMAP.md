# BDneX - Feuille de Route / Roadmap

Ce document décrit les améliorations prévues et les fonctionnalités planifiées pour BDneX.

*This document describes the planned improvements and features for BDneX.*

## Priorité Haute / High Priority

### Base de données SQLite
**État / Status**: 📝 Planifié / Planned  
**Description FR**: Implémenter une base de données SQLite pour garder une trace des BD déjà traitées, évitant ainsi les retraitements inutiles et accélérant les opérations sur de grandes bibliothèques.

**Description EN**: Implement a SQLite database to keep track of already processed comics, avoiding unnecessary reprocessing and speeding up operations on large libraries.

**Bénéfices / Benefits**:
- Évite le retraitement des mêmes fichiers / Avoids reprocessing same files
- Historique des modifications / History of modifications  
- Recherche rapide dans la bibliothèque / Fast library search
- Gestion des métadonnées hors-ligne / Offline metadata management

---

### Mode Interactif Amélioré
**État / Status**: 📝 Planifié / Planned  
**Description FR**: Interface CLI enrichie avec menus de sélection, prévisualisation des métadonnées, et confirmation visuelle des correspondances.

**Description EN**: Enhanced CLI interface with selection menus, metadata preview, and visual match confirmation.

**Fonctionnalités / Features**:
- Menu de sélection avec touches fléchées / Arrow key selection menus
- Prévisualisation des couvertures en ASCII art / ASCII art cover previews
- Comparaison côte-à-côte des métadonnées / Side-by-side metadata comparison
- Édition manuelle des métadonnées / Manual metadata editing
- Confirmation par lots / Batch confirmation

**Technologies envisagées / Considered technologies**: InquirerPy (déjà utilisé), Rich, Textual

---

### Convention de Renommage
**État / Status**: 📝 Planifié / Planned  
**Description FR**: Renommage automatique des fichiers basé sur les métadonnées récupérées, avec des modèles de noms configurables par l'utilisateur.

**Description EN**: Automatic file renaming based on retrieved metadata, with user-configurable naming templates.

**Modèles par défaut / Default templates**:
```
Series/%Series - %Number - %Title (%Year)
Authors/%Author/%Series/%Series - %Number
Publishers/%Publisher/%Series/%Year - %Title
```

**Options configurables / Configurable options**:
- Gestion des caractères spéciaux / Special character handling
- Limitation de longueur des noms / Name length limits
- Format de numérotation (01, 1, T01, etc.) / Numbering format
- Inclusion/exclusion d'éléments / Element inclusion/exclusion

---

## Priorité Moyenne / Medium Priority

### Sources de Données Additionnelles
**État / Status**: 🔍 En recherche / In research  
**Description FR**: Support pour d'autres sources de métadonnées de BD françaises au-delà de bedetheque.com.

**Description EN**: Support for additional French comics metadata sources beyond bedetheque.com.

**Sources envisagées / Potential sources**:
- [BDfugue](https://www.bdfugue.com/) - Librairie BD en ligne / Online BD store
- [BDGest](https://www.bdgest.com/) - Base de données BD / BD database
- [Manga-News](https://www.manga-news.com/) - Pour les mangas / For manga
- [Comics.org](https://www.comics.org/) - Base internationale / International database
- [League of Comic Geeks](https://leagueofcomicgeeks.com/) - Communauté / Community

**Approche technique / Technical approach**:
- Système de plugins modulaire / Modular plugin system
- Interface commune pour tous les scrapers / Common interface for all scrapers
- Priorité configurable des sources / Configurable source priority
- Fusion intelligente des métadonnées / Intelligent metadata merging

---

### Gestionnaire de Catalogue
**État / Status**: 📝 Planifié / Planned  
**Description FR**: Interface pour parcourir, rechercher et gérer la bibliothèque balisée.

**Description EN**: Interface to browse, search, and manage the tagged library.

**Fonctionnalités prévues / Planned features**:
- Navigation par série, auteur, éditeur / Browse by series, author, publisher
- Recherche avancée avec filtres / Advanced search with filters
- Statistiques de bibliothèque / Library statistics
- Identification des métadonnées manquantes / Identify missing metadata
- Export de listes (CSV, JSON) / List export (CSV, JSON)
- Marquage des BD lues/non lues / Mark comics as read/unread

---

### Support de Reprise
**État / Status**: 📝 Planifié / Planned  
**Description FR**: Capacité de reprendre le traitement par lots là où il s'est arrêté en cas d'interruption.

**Description EN**: Ability to resume batch processing where it left off in case of interruption.

**Implémentation / Implementation**:
- Fichier de progression `.bdnex_progress` / Progress file `.bdnex_progress`
- Sauvegarde automatique toutes les N BD / Auto-save every N comics
- Option `--resume` pour reprendre / `--resume` option to continue
- Gestion des erreurs avec retry / Error handling with retry

---

## Priorité Basse / Low Priority

### Interface Web
**État / Status**: 💡 Idée / Idea  
**Description FR**: Application web pour gérer la bibliothèque via navigateur.

**Description EN**: Web application to manage library via browser.

**Stack technique envisagée / Potential tech stack**:
- Backend: Flask ou FastAPI
- Frontend: React ou Vue.js
- Base de données: SQLite (partagée avec CLI)
- API REST pour interactions / REST API for interactions

**Fonctionnalités / Features**:
- Dashboard avec statistiques / Dashboard with statistics
- Galerie de couvertures / Cover gallery
- Recherche et filtrage / Search and filtering
- Traitement des fichiers uploadés / Process uploaded files
- Configuration via interface / Configuration via UI

---

### Application GUI Desktop
**État / Status**: 💡 Idée / Idea  
**Description FR**: Application de bureau avec interface graphique native.

**Description EN**: Desktop application with native graphical interface.

**Technologies envisagées / Considered technologies**:
- PyQt6 / PySide6
- Tkinter (plus simple)
- Electron + Python backend

---

### Système de Plugins
**État / Status**: 💡 Idée / Idea  
**Description FR**: Architecture extensible permettant aux utilisateurs de créer leurs propres sources de métadonnées.

**Description EN**: Extensible architecture allowing users to create their own metadata sources.

**Caractéristiques / Features**:
- API de plugin documentée / Documented plugin API
- Chargement dynamique des plugins / Dynamic plugin loading
- Dépôt de plugins communautaires / Community plugin repository
- Hooks pour personnaliser le comportement / Hooks to customize behavior

---

### Détection de Doublons
**État / Status**: 💡 Idée / Idea  
**Description FR**: Identifier et gérer les BD en double dans la bibliothèque.

**Description EN**: Identify and manage duplicate comics in the library.

**Méthodes de détection / Detection methods**:
- Correspondance de métadonnées / Metadata matching
- Comparaison de hash de fichiers / File hash comparison
- Similarité de couvertures / Cover similarity
- Comparaison de contenu / Content comparison

---

### Listes de Lecture
**État / Status**: 💡 Idée / Idea  
**Description FR**: Créer, gérer et partager des listes de lecture de BD.

**Description EN**: Create, manage, and share comic reading lists.

**Fonctionnalités / Features**:
- Créer des listes thématiques / Create themed lists
- Ordre de lecture personnalisé / Custom reading order
- Export/import de listes / List export/import
- Partage de listes (JSON, M3U-like) / List sharing (JSON, M3U-like)
- Marquage de progression / Progress tracking

---

### Support Multilingue Complet
**État / Status**: 📝 Planifié / Planned  
**Description FR**: Interface et messages en français et anglais.

**Description EN**: Interface and messages in French and English.

**Implémentation / Implementation**:
- Fichiers de traduction gettext / gettext translation files
- Détection automatique de la langue / Automatic language detection
- Option `--lang` pour forcer la langue / `--lang` option to force language
- Documentation bilingue complète / Complete bilingual documentation

---

## Améliorations Techniques / Technical Improvements

### Tests et Qualité / Tests and Quality
**Objectifs / Goals**:
- [x] Couverture de tests >80% (actuellement 86% ✅) / Test coverage >80% (currently 86% ✅)
- [ ] Couverture de tests >95% / Test coverage >95%
- [ ] Tests d'intégration avec vraies BD / Integration tests with real comics
- [ ] Tests de performance / Performance tests
- [ ] CI/CD automatisé amélioré / Enhanced automated CI/CD
- [ ] Analyse de qualité du code (SonarQube, CodeClimate) / Code quality analysis

---

### Performance
**Améliorations prévues / Planned improvements**:
- [ ] Traitement parallèle des BD / Parallel comic processing
- [ ] Cache intelligent des sitemaps / Intelligent sitemap caching
- [ ] Optimisation des comparaisons d'images / Image comparison optimization
- [ ] Indexation de la base de données / Database indexing
- [ ] Téléchargements asynchrones / Asynchronous downloads

---

### Documentation
**Améliorations / Improvements**:
- [x] README français / French README ✅
- [x] README anglais détaillé / Detailed English README ✅
- [x] Feuille de route / Roadmap ✅
- [ ] Tutoriels vidéo / Video tutorials
- [ ] Documentation API / API documentation
- [ ] Guide de contribution détaillé / Detailed contribution guide
- [ ] Wiki avec exemples / Wiki with examples
- [ ] FAQ étendue / Extended FAQ

---

## Comment Contribuer / How to Contribute

Nous sommes ouverts aux contributions sur toutes ces fonctionnalités ! / We're open to contributions on all these features!

**Pour proposer une nouvelle fonctionnalité / To propose a new feature**:
1. Ouvrir une issue GitHub avec le tag `enhancement` / Open a GitHub issue with `enhancement` tag
2. Décrire le cas d'usage et les bénéfices / Describe the use case and benefits
3. Discuter de l'approche technique / Discuss the technical approach
4. Soumettre une PR si approuvée / Submit a PR if approved

**Pour travailler sur une fonctionnalité existante / To work on an existing feature**:
1. Commenter sur l'issue correspondante / Comment on the corresponding issue
2. Demander à être assigné / Ask to be assigned
3. Fork et créer une branche / Fork and create a branch
4. Soumettre une PR avec tests / Submit a PR with tests

---

## Légende / Legend

- 💡 **Idée** / **Idea**: Concept initial, pas encore spécifié
- 🔍 **En recherche** / **In research**: Investigation des options techniques
- 📝 **Planifié** / **Planned**: Spécifié et prêt pour implémentation
- 🚧 **En développement** / **In development**: Travail en cours
- ✅ **Complété** / **Completed**: Implémenté et testé

---

**Dernière mise à jour / Last updated**: 2024-12-29  
**Version**: 0.1 (POC)

Pour toute question ou suggestion, n'hésitez pas à ouvrir une issue GitHub ! / For questions or suggestions, feel free to open a GitHub issue!
