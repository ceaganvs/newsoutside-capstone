# News Outside

Django news publishing platform with role-based access control, publisher management,
reader subscriptions, and a RESTful API.

## Features

- **3 User Roles**: Reader, Journalist, Editor
- **Publishers**: Editors create publishers; journalists submit articles under a publisher for editor review
- **Article Workflow**: Independent journalists publish directly; publisher-affiliated articles require editor approval
- **Subscriptions**: Readers subscribe to publishers or individual journalists
- **Email Notifications**: Subscribers are emailed when a new article is approved or published
- **Newsletters**: Curated article collections created by journalists and editors
- **RESTful API**: Token authentication, full CRUD, role-based access
- **X (Twitter) Integration**: Posts to X when an article is approved (requires API credentials)

## Documentation

Generated Sphinx documentation is in `docs/build/html/`. Open
`docs/build/html/index.html` in a browser to browse the full API reference.

---

## Option 1 — Virtual Environment

### Requirements

- Python 3.10+
- MariaDB or MySQL 8.0+

### 1. Clone the repository

```bash
git clone https://github.com/ceaganvs/newsoutside-capstone.git
cd newsoutside-capstone
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows (PowerShell)
venv\Scripts\Activate.ps1

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `mysqlclient` requires the MySQL C client libraries.
> - **Windows**: Install [MySQL Connector/C](https://dev.mysql.com/downloads/connector/c/)
> - **Ubuntu/Debian**: `sudo apt install default-libmysqlclient-dev`
> - **macOS**: `brew install mysql-client`

### 4. Create the database

Open a MariaDB/MySQL shell and run:

```sql
CREATE DATABASE news_outside CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

### 5. Configure environment variables

Copy the example file and fill in your values:

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` in a text editor and set at minimum:

```
SECRET_KEY=your-secret-key-here
DB_NAME=news_outside
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

> **Important:** `.env` is listed in `.gitignore`. Never commit it to version control.

### 6. Run migrations and set up the project

```bash
python manage.py migrate
python manage.py setup_groups
python manage.py createsuperuser
```

### 7. Start the development server

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/

---

## Option 2 — Docker

Requires [Docker](https://docs.docker.com/get-docker/) and Docker Compose.

### 1. Clone the repository

```bash
git clone https://github.com/ceaganvs/newsoutside-capstone.git
cd newsoutside-capstone
```

### 2. Start the containers

```bash
docker compose up --build
```

This starts both the MariaDB database and the Django web server. The database
is created automatically using the credentials in `docker-compose.yml`.

### 3. Set up groups and create a superuser (first run only)

```bash
docker compose exec web python manage.py setup_groups
docker compose exec web python manage.py createsuperuser
```

Open http://127.0.0.1:8000/

### 4. Stop the containers

```bash
docker compose down        # stop, keep database volume
docker compose down -v     # stop and delete database volume
```

### Secrets and Environment Variables

The `docker-compose.yml` uses placeholder development values. For production,
replace them with strong secrets and **never commit real credentials to a public repo**.

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DB_PASSWORD` | MariaDB app-user password |
| `MARIADB_ROOT_PASSWORD` | MariaDB root password |

---

## X (Twitter) API Configuration (Optional)

To enable posting to X when articles are approved, add these to your `.env` (venv)
or to the `web` service `environment` block in `docker-compose.yml` (Docker):

```
X_API_CONSUMER_KEY=your_consumer_key
X_API_CONSUMER_SECRET=your_consumer_secret
X_API_ACCESS_TOKEN=your_access_token
X_API_ACCESS_TOKEN_SECRET=your_access_token_secret
```

Credentials come from your app at [developer.x.com](https://developer.x.com).
Requires **Read and Write** permissions. If not set, the server runs normally and
logs a message instead of posting.

---

## Running Tests

```bash
python manage.py test NOPE
```

## API Endpoints

| Method | Endpoint | Access |
|---|---|---|
| POST | `/api/token/` | Anyone |
| GET | `/api/articles/` | Public |
| POST | `/api/articles/` | Journalists |
| PUT/PATCH | `/api/articles/<id>/` | Author or Editor |
| DELETE | `/api/articles/<id>/` | Editor |
| POST | `/api/articles/<id>/approve/` | Editors |
| GET | `/api/articles/subscribed/` | Readers |
| GET/POST | `/api/newsletters/` | Authenticated |
| GET | `/api/publishers/` | Authenticated |
| GET | `/api/users/me/` | Authenticated |
| POST | `/api/users/<id>/subscribe_publisher/` | Readers |
| POST | `/api/users/<id>/subscribe_journalist/` | Readers |

## Web Routes

- `/` — Latest approved articles (landing page)
- `/register/` — Create account (reader, journalist, or editor)
- `/login/` — Login
- `/dashboard/` — Role-specific dashboard
- `/publishers/` — Browse all publishers
- `/publishers/create/` — Create publisher (editors only)
- `/subscriptions/` — Manage subscriptions (readers only)
- `/articles/create/` — Write article (journalists only)
- `/editor/pending/` — Review pending articles (editors only)

## Access

- Web: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/
- API browser: http://127.0.0.1:8000/api/
