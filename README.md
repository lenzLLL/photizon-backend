# 🌟 Christlumen Platform

**Christlumen** - *La Lumière du Christ* - Une plateforme moderne de gestion d'églises, contenus spirituels, événements, dons et bien plus.

![Christlumen Logo](api/meda/logo.jpeg)

## 📋 Description

Christlumen est une plateforme complète qui permet aux églises de :
- Gérer leurs membres et administrateurs
- Publier et partager des contenus spirituels
- Organiser des programmes et événements
- Recevoir des dons et offrandes
- Vendre des livres et ressources
- Gérer des tickets et réservations
- Communiquer avec les membres via chat

## 🎨 Design

Le dashboard admin utilise un **thème dark élégant** avec des accents **dorés** inspirés de la lumière du Christ :
- Interface moderne et professionnelle
- Contraste parfait pour une lisibilité maximale
- Animations fluides et effets de hover élégants
- Design responsive et mobile-friendly
- Logo Christlumen intégré avec effet glow doré

## 🚀 Installation

### Prérequis
- Python 3.11+
- pip
- virtualenv

### Étapes d'installation

1. **Cloner le projet**
```bash
cd /Users/macbookpro/Desktop/Developments/Personnals/photizon-backend
```

2. **Activer l'environnement virtuel**
```bash
source venv/bin/activate
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Appliquer les migrations**
```bash
python manage.py migrate
```

5. **Collecter les fichiers statiques**
```bash
python manage.py collectstatic --noinput
```

6. **Créer un superutilisateur**
```bash
python manage.py createsuperuser
```

7. **Lancer le serveur de développement**
```bash
python manage.py runserver
```

8. **Accéder au dashboard**
```
http://localhost:8000/admin/
```

## 📁 Structure du Projet

```
christlumen-backend/
├── christlumen/              # Configuration principale
│   ├── settings.py          # Paramètres Django
│   ├── urls.py              # URLs principales
│   ├── asgi.py              # Configuration ASGI
│   └── wsgi.py              # Configuration WSGI
├── api/                      # Application principale
│   ├── models.py            # Modèles de données
│   ├── views/               # Vues organisées par fonctionnalité
│   ├── serializers.py       # Serializers DRF
│   ├── admin.py             # Configuration admin
│   └── services/            # Services métier
├── static/                   # Fichiers statiques personnalisés
│   └── admin/
│       ├── css/
│       │   └── christlumen-custom.css  # CSS personnalisé
│       └── img/
│           ├── christlumen-logo.jpeg
│           └── christlumen-icon.jpeg
├── staticfiles/             # Fichiers statiques collectés
├── db.sqlite3              # Base de données (dev)
├── requirements.txt        # Dépendances Python
└── manage.py              # Script de gestion Django
```

## 🔧 Technologies Utilisées

### Backend
- **Django 5.2.8** - Framework web Python
- **Django REST Framework 3.16.1** - API REST
- **Channels 4.0.0** - WebSockets pour le chat en temps réel
- **drf-spectacular 0.29.0** - Documentation API automatique
- **djangorestframework-simplejwt 5.5.1** - Authentification JWT

### Admin Panel
- **Django Jazzmin 3.0.1** - Interface admin moderne
- **Thème personnalisé Christlumen** - Dark theme avec accents dorés

### Base de données
- **PostgreSQL** (production) via psycopg2-binary
- **SQLite** (développement)

## 📊 Modèles de Données

### Utilisateurs & Églises
- **User** - Utilisateurs de la plateforme
- **Church** - Églises enregistrées
- **ChurchAdmin** - Administrateurs d'églises
- **Subscription** - Abonnements
- **SubscriptionPlan** - Plans d'abonnement

### Contenus & Programmes
- **Content** - Contenus spirituels (livres, audios, vidéos)
- **Category** - Catégories de contenus
- **Programme** - Programmes et événements

### Commerce & Dons
- **Donation** - Dons et offrandes
- **DonationCategory** - Catégories de dons
- **BookOrder** - Commandes de livres
- **Payment** - Paiements

### Tickets & Événements
- **Ticket** - Tickets générés
- **TicketType** - Types de tickets
- **TicketReservation** - Réservations de tickets

### Communication
- **Testimony** - Témoignages des membres
- **TestimonyLike** - Likes sur témoignages
- **Notification** - Notifications système
- **ChatRoom** - Salles de chat
- **ChatMessage** - Messages de chat

### Collaboration
- **ChurchCollaboration** - Collaborations entre églises

## 🔐 API Endpoints

L'API REST est disponible avec documentation interactive :

- **Swagger UI** : http://localhost:8000/api/docs/
- **ReDoc** : http://localhost:8000/api/redoc/
- **Schema JSON** : http://localhost:8000/api/schema/

### Endpoints principaux

```
/api/auth/         - Authentification (login, register, OTP)
/api/churches/     - Gestion des églises
/api/contents/     - Contenus spirituels
/api/programmes/   - Programmes et événements
/api/donations/    - Dons et offrandes
/api/testimonies/  - Témoignages
/api/chat/         - Messages et chat
```

## 🎨 Personnalisation du Thème

Le thème Christlumen peut être personnalisé dans `/static/admin/css/christlumen-custom.css`

### Variables CSS principales :
```css
:root {
    --christlumen-gold: #f59e0b;           /* Or principal */
    --christlumen-gold-light: #fbbf24;     /* Or clair */
    --christlumen-gold-dark: #d97706;      /* Or foncé */
    --christlumen-bg-dark: #1a1a1a;        /* Fond sombre */
    --christlumen-bg-darker: #0f0f0f;      /* Fond très sombre */
    --christlumen-bg-card: #2a2a2a;        /* Fond des cards */
    --christlumen-text: #f5f5f5;           /* Texte clair */
    --christlumen-border: #3a3a3a;         /* Bordures */
}
```

## 📝 Variables d'Environnement

Créez un fichier `.env` à la racine du projet :

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=sqlite:///db.sqlite3

# Frontend
FRONTEND_URL=http://localhost:3000
API_URL=http://localhost:8000
WS_URL=ws://localhost:8000

# WhatsApp (Meta)
META_PHONE_ID=your-phone-id
META_WHATSAPP_API_KEY=your-api-key
META_WA_TOKEN=your-token

# OTP
OTP_EXPIRATION_SECONDS=300
OTP_SEND_COOLDOWN_SECONDS=60
```

## 🔄 Commandes Utiles

### Développement
```bash
# Lancer le serveur de développement
python manage.py runserver

# Créer des migrations
python manage.py makemigrations

# Appliquer les migrations
python manage.py migrate

# Créer un superutilisateur
python manage.py createsuperuser

# Collecter les fichiers statiques
python manage.py collectstatic

# Ouvrir le shell Django
python manage.py shell

# Vérifier la configuration
python manage.py check
```

### Production
```bash
# Avec Gunicorn
gunicorn christlumen.wsgi:application --bind 0.0.0.0:8000

# Collecter les statiques (production)
python manage.py collectstatic --noinput --clear
```

## 🧪 Tests

```bash
# Lancer tous les tests
python manage.py test

# Lancer les tests d'une app spécifique
python manage.py test api

# Avec coverage
coverage run --source='.' manage.py test
coverage report
```

## 📦 Déploiement

### Avec Docker (à venir)
```bash
docker-compose up -d
```

### Configuration Nginx (exemple)
```nginx
server {
    listen 80;
    server_name christlumen.com;

    location /static/ {
        alias /path/to/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🤝 Contribution

Ce projet est développé et maintenu par l'équipe Christlumen.

## 📄 Licence

© 2024 Christlumen - Tous droits réservés

## 🌐 Support

Pour toute question ou assistance :
- Email: support@christlumen.com
- Documentation API: http://localhost:8000/api/docs/

---

**Christlumen** - *Apportant la lumière du Christ au monde numérique* ✨
