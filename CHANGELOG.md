# 📝 Changelog - Christlumen Platform

Tous les changements notables de ce projet seront documentés dans ce fichier.

## [2.0.0] - 2024-03-02

### 🎨 Redesign Complet - Christlumen

#### ✨ Ajouté
- **Nouveau nom**: Renommage complet de "MyChurch" vers "Christlumen"
- **Thème Dark élégant**: Interface sombre moderne avec accents dorés
- **Logo Christlumen**: Intégration du logo officiel (livre ouvert + croix + soleil)
- **CSS personnalisé**: Plus de 600 lignes de CSS custom pour un design premium
- **Documentation complète**: README.md, QUICKSTART.md, CHANGELOG.md
- **Fichier .env.example**: Template de configuration
- **Fichier .gitignore**: Amélioré pour ignorer tous les fichiers sensibles

#### 🎨 Design & UI
- Interface dark avec fond noir profond (#1a1a1a, #0f0f0f)
- Accents dorés (#f59e0b, #fbbf24, #fb923c) rappelant la lumière
- Texte blanc (#f5f5f5) pour un contraste parfait
- Sidebar fixe sombre avec items dorés au survol
- Navbar avec bordure dorée élégante
- Cards avec ombres et effets hover
- Tables avec headers gradient or
- Boutons avec gradients dorés et animations
- Formulaires dark avec bordures lumineuses au focus
- Scrollbar personnalisée dorée
- Animations fluides sur tous les éléments
- Login page avec thème dark luxueux

#### 🔧 Modifications Techniques
- Renommage du dossier `mychurch/` → `christlumen/`
- Mise à jour de tous les imports et références
- Configuration Jazzmin modernisée
- Thème "darkly" activé par défaut
- Variables CSS pour personnalisation facile
- Fichiers statiques réorganisés

#### 📁 Structure
```
static/admin/
├── css/
│   └── christlumen-custom.css  (Nouveau CSS personnalisé)
└── img/
    ├── christlumen-logo.jpeg   (Logo officiel)
    └── christlumen-icon.jpeg   (Favicon)
```

#### 🐛 Corrections
- Fix du problème de contraste (texte blanc sur fond blanc)
- Fix du fichier requirements.txt (encodage corrigé)
- Fix de la configuration des fichiers statiques
- Fix des chemins de logo dans settings.py

#### ⚙️ Configuration
- **Jazzmin Settings**:
  - Thème: darkly
  - Sidebar: sidebar-dark-warning
  - Navbar: navbar-dark
  - Accent: accent-warning
  - Boutons primaires: btn-warning (doré)
- **Variables CSS**: Palette de couleurs Christlumen
- **Static Files**: Configuration STATIC_ROOT et STATICFILES_DIRS

---

## [1.0.0] - 2024-02-XX

### Initial Release - MyChurch Platform

#### ✨ Fonctionnalités de Base
- Authentification par téléphone avec OTP
- Gestion des églises
- Gestion des contenus (audio, vidéo, livres)
- Système de dons et offrandes
- Programmes et événements
- Témoignages
- Chat en temps réel (WebSockets)
- Tickets et réservations
- Commandes de livres
- Paiements
- Notifications
- Collaborations entre églises
- Plans d'abonnement

#### 🛠️ Technologies
- Django 5.2.8
- Django REST Framework 3.16.1
- Channels 4.0.0 (WebSockets)
- Django Jazzmin 3.0.1
- drf-spectacular 0.29.0
- JWT Authentication
- PostgreSQL / SQLite

#### 📊 Modèles de Données
- User, Church, ChurchAdmin
- Content, Category, Programme
- Donation, DonationCategory, Payment
- Ticket, TicketType, TicketReservation
- Testimony, TestimonyLike
- ChatRoom, ChatMessage
- Notification, OTP
- BookOrder
- Subscription, SubscriptionPlan
- ChurchCollaboration

#### 🔌 API Endpoints
- `/api/auth/` - Authentification
- `/api/churches/` - Églises
- `/api/contents/` - Contenus
- `/api/programmes/` - Programmes
- `/api/donations/` - Dons
- `/api/testimonies/` - Témoignages
- `/api/chat/` - Chat
- Documentation API avec Swagger et ReDoc

---

## Types de Changements

- **✨ Ajouté** : Pour les nouvelles fonctionnalités
- **🔧 Modifié** : Pour les changements dans les fonctionnalités existantes
- **❌ Déprécié** : Pour les fonctionnalités qui seront supprimées
- **🗑️ Supprimé** : Pour les fonctionnalités supprimées
- **🐛 Corrigé** : Pour les corrections de bugs
- **🔒 Sécurité** : Pour les correctifs de sécurité
- **🎨 Design** : Pour les changements visuels
- **⚡ Performance** : Pour les améliorations de performance
- **📝 Documentation** : Pour les changements dans la documentation

---

**Christlumen** - *La lumière du Christ* ✨
