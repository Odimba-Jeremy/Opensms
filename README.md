# Mini SMS Gateway

Une passerelle SMS minimaliste (5 fichiers Python) : tu envoies une requête HTTP, et un téléphone Android (via Termux) ou un modem GSM envoie le SMS avec sa carte SIM.

---

## 1. Comment ça marche

```
Ton appli / curl
      │  POST /sms  (avec clé d'API)
      ▼
   main.py (API Flask) ──► storage.py (SQLite : enregistre le SMS "pending")
                                  ▲
   worker.py (arrière-plan) ──────┘ prend le SMS suivant
      │
      ▼
   sender.py ──► Termux / modem ──► SIM ──► destinataire
      │
      ▼
   statut mis à jour : sent ou failed
```

Le SMS n'est pas envoyé instantanément : l'API répond tout de suite (`202`), puis le worker l'envoie en arrière-plan, un par un, avec une pause entre chaque envoi pour protéger ta SIM.

## 2. Les fichiers

| Fichier | Rôle |
|---|---|
| `main.py` | API Flask : routes, vérification de la clé d'API |
| `config.py` | Tous les réglages (variables d'environnement) |
| `sender.py` | Envoi réel du SMS (Termux, modem ou mock) |
| `storage.py` | Historique des SMS dans une base SQLite (`sms.db`) |
| `worker.py` | File d'attente, pauses, nouvelles tentatives |
| `requirements.txt` | Dépendances (Flask) |

## 3. Installation sur Android (Termux)

### Important : bonne source d'installation

Termux de **Google Play** ne fonctionne pas avec Termux:API (qui n'existe pas sur Google Play). Installe les deux depuis **F-Droid** (ou GitHub), jamais un mélange de sources.

1. Installe **Termux** et **Termux:API** depuis F-Droid.
2. Ouvre Android > Réglages > Applications > Termux:API > Autorisations, et accorde la permission **SMS**.
3. Dans Termux :

```bash
pkg update
pkg install python termux-api
```

4. Mets les 6 fichiers dans un dossier, par exemple `~/sms-gateway`, puis :

```bash
cd ~/sms-gateway
pip install -r requirements.txt
```

5. Teste l'envoi Termux seul (avec ton vrai numéro) :

```bash
termux-sms-send -n +243XXXXXXXXX "Test"
```

Si le SMS arrive, la passerelle fonctionnera.

## 4. Lancer la passerelle

Mode test (aucun vrai SMS, les messages s'affichent dans la console) :

```bash
SMS_API_KEY=macle python main.py
```

Mode réel avec Termux :

```bash
SMS_SENDER=termux SMS_API_KEY=macle python main.py
```

Vérifie le mode actif :

```bash
curl http://127.0.0.1:8000/health
```

Tu dois voir `"sender":"termux"`.

Garde le serveur allumé : ouvre une **2e session Termux** (glisse depuis le bord gauche > New session) pour envoyer tes requêtes.

## 5. Envoyer un SMS

Le numéro s'écrit avec `+` et l'indicatif pays, sans espace (exemple RDC : `+243974336700`).

```bash
curl -X POST http://127.0.0.1:8000/sms \
  -H "X-API-Key: macle" \
  -H "Content-Type: application/json" \
  -d '{"number":"+243974336700","message":"Salut"}'
```

Réponse : `{"id":1,"status":"pending"}`

Vérifier le statut :

```bash
curl -H "X-API-Key: macle" http://127.0.0.1:8000/sms/1
```

## 6. Les routes de l'API

| Méthode | Route | Clé requise | Description |
|---|---|---|---|
| GET | `/health` | Non | Vérifie que le serveur tourne et affiche le mode |
| POST | `/sms` | Oui | Met un SMS en file d'attente |
| GET | `/sms/<id>` | Oui | Statut d'un SMS |
| GET | `/sms?limit=50&status=sent` | Oui | Liste (`status` : pending, sent, failed) |

La clé se passe dans l'en-tête `X-API-Key`. Un navigateur ne l'envoie pas : c'est normal d'obtenir "Clé d'API invalide" en ouvrant une route protégée dans Chrome (seul `/health` s'ouvre sans clé).

### Règles de validation
- Numéro : 6 à 15 chiffres, `+` optionnel au début.
- Message : de 1 à 640 caractères.

## 7. Les statuts d'un SMS

| Statut | Signification |
|---|---|
| `pending` | En attente d'envoi (ou d'un nouvel essai) |
| `sent` | Envoyé |
| `failed` | Échec après toutes les tentatives, voir le champ `error` |

Chaque SMS contient aussi : `attempts` (nombre d'essais), `error`, `created_at`, `updated_at`.

## 8. Réglages (variables d'environnement)

| Variable | Défaut | Description |
|---|---|---|
| `SMS_API_KEY` | `change-me` | Clé d'API. **À changer absolument** |
| `SMS_SENDER` | `mock` | `termux`, `modem` ou `mock` |
| `SMS_HOST` | `0.0.0.0` | Adresse d'écoute |
| `SMS_PORT` | `8000` | Port |
| `SMS_RATE_LIMIT` | `10` | SMS maximum par minute |
| `SMS_MAX_RETRIES` | `3` | Nombre d'essais avant `failed` |
| `SMS_RETRY_DELAY` | `30` | Secondes entre deux essais |
| `SMS_DB_PATH` | `sms.db` | Fichier de la base de données |
| `SMS_SERIAL_PORT` | `/dev/ttyUSB0` | Port du modem (`COM3` sous Windows) |
| `SMS_BAUDRATE` | `115200` | Vitesse du modem |

Exemple :

```bash
SMS_SENDER=termux SMS_API_KEY=ma_cle_secrete SMS_RATE_LIMIT=5 python main.py
```

## 9. Utiliser un modem USB GSM (alternative)

1. Mets la SIM dans le modem (désactive le code PIN avant).
2. `pip install pyserial`
3. Trouve le port du modem (`/dev/ttyUSB0` sous Linux, `COM3` etc. sous Windows).
4. Lance :

```bash
SMS_SENDER=modem SMS_SERIAL_PORT=/dev/ttyUSB0 python main.py
```

Limite : le modem envoie en ASCII, donc les accents sont remplacés.

## 10. Accéder depuis un autre appareil

Sur le même Wi-Fi, utilise l'adresse affichée au lancement, par exemple `http://10.156.157.191:8000`. Exemple en Python :

```python
import requests
requests.post(
    "http://10.156.157.191:8000/sms",
    headers={"X-API-Key": "macle"},
    json={"number": "+243974336700", "message": "Salut"},
)
```

Pour y accéder depuis internet, il faut un tunnel ou un serveur. Dans ce cas, utilise une clé d'API longue et secrète.

## 11. Garder la passerelle active

Android peut couper Termux en arrière-plan :
- Tape `termux-wake-lock` dans Termux.
- Désactive l'optimisation de batterie pour Termux (Réglages > Batterie).
- Laisse le téléphone branché.

## 12. Problèmes courants

| Problème | Solution |
|---|---|
| `Clé d'API invalide` | Ajoute l'en-tête `X-API-Key` avec la bonne clé (inutile pour `/health`) |
| `termux-sms-send introuvable` | `pkg install termux-api` |
| `Termux:API is not yet available on Google Play` | Réinstalle Termux et Termux:API depuis F-Droid |
| Statut `failed` sans SMS reçu | Lis le champ `error`. Vérifie la permission SMS de Termux:API |
| `pip` bloque sur `pydantic-core` | Cette version utilise Flask, qui ne compile rien. Vérifie que `requirements.txt` contient seulement `flask` |
| `"sender":"mock"` dans `/health` | Relance avec `SMS_SENDER=termux` |
| SMS internationaux qui ne partent pas | Vérifie le crédit et l'option SMS international de ta SIM |
| Statut `pending` qui reste | Le worker respecte la pause entre envois (60 / `SMS_RATE_LIMIT` secondes) : attends un peu |

## 13. Sécurité

- Change `SMS_API_KEY` avant d'exposer la passerelle hors de ton Wi-Fi.
- Ne publie jamais ta clé (GitHub, captures d'écran).
- Respecte les quotas de ton opérateur : un envoi massif peut faire bloquer la SIM.
- N'envoie des SMS qu'à des personnes qui ont accepté d'en recevoir.

## 14. Limites actuelles

- Pas de réception de SMS.
- Pas de gestion de plusieurs SIM ou plusieurs numéros (Termux utilise la SIM par défaut d'Android).
- Serveur de développement Flask : suffisant en usage perso, pas prévu pour un fort trafic.
- Les SMS très longs ne sont pas découpés par la passerelle (c'est l'envoyeur qui s'en charge).
