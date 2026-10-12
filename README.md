# SamaPass – Backend (API Django)

API REST de la plateforme de billetterie **SamaPass** (Django 6, Django REST Framework, PostgreSQL, JWT).

## Applications

| Application | Rôle |
|---|---|
| `accounts` | Utilisateurs (OTP), organisateurs, administrateurs, jetons JWT, profil |
| `events` | Événements, types de billets, programme, disponibilité, publication |
| `tickets` | Achat, billets, QR Code unique, scan, litiges |
| `transactions` | Transactions et commissions |
| `payouts` | Solde de l'organisateur et reversements |
| `access_control` | Portes d'accès et agents de scan |
| `engagement` | Favoris et notifications |
| `videos` | Fil vidéo des événements, likes, modération |
| `sponsorship` | Campagnes publicitaires sponsorisées |
| `platform_settings` | Taux de commission et réglages de la plateforme |
| `admin_activity` | Journal d'activité des administrateurs |
| `providers` | Configuration des fournisseurs de paiement et de messagerie |

## Installation

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # puis renseigner les valeurs
python manage.py migrate
python manage.py runserver
```

## Docker

```bash
docker build -t samapass-backend -f dockerfile .
```

Le projet complet (frontend, backend, chatbot) est orchestré avec Docker Compose.

## Dépôts liés

- Frontend : `SamaPass-Frontend`
- Chatbot IA : `SamaPass-Chatbot`
