# Deploy Releaf to PythonAnywhere

This project can run on a PythonAnywhere Beginner (free) account using Django's
development-safe defaults locally and production settings in the hosted WSGI
configuration.

## 1. Upload the project

Upload or clone the project into your home directory, for example:

```text
/home/<username>/Releaf
```

The directory should contain `manage.py` and `requirements.txt`.

The repository ignore rules exclude `db.sqlite3` and `media/`. If you want to
preserve local listings and uploaded photos, back up and transfer the database
and media directory separately; do not add secrets or local database files to
the repository.

## 2. Create the virtualenv

In a PythonAnywhere Bash console, create a Python 3.10 virtualenv and install
the pinned project dependencies:

```bash
mkvirtualenv --python=/usr/bin/python3.10 releaf-venv
cd ~/Releaf
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

`requirements.txt` already lists the project's direct dependencies; freezing
the entire local virtualenv would add unrelated development packages.

## 3. Create the web app

In the **Web** tab, create a web app using **Manual configuration** and Python
3.10. Set its virtualenv to:

```text
/home/<username>/.virtualenvs/releaf-venv
```

Edit the WSGI file linked from that tab. Replace its contents with the
following, substituting your PythonAnywhere username and a newly generated
secret key:

```python
import os
import sys

project_home = "/home/<username>/Releaf"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ["DJANGO_SETTINGS_MODULE"] = "releaf_project.settings"
os.environ["DJANGO_DEBUG"] = "False"
os.environ["DJANGO_SECRET_KEY"] = "replace-with-a-random-secret"
os.environ["DJANGO_ALLOWED_HOSTS"] = "<username>.pythonanywhere.com"
os.environ["CSRF_TRUSTED_ORIGINS"] = "https://<username>.pythonanywhere.com"

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
```

Generate a secret in the Bash console with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Keep the real secret only in the PythonAnywhere WSGI configuration; do not
commit it.

Enable the free SSL certificate for your `pythonanywhere.com` domain in the
Web tab before testing the site. Production settings redirect HTTP to HTTPS
and enable HSTS.

## 4. Configure static files and uploads

In the **Static files** section of the Web tab, add these mappings:

| URL | Directory |
| --- | --- |
| `/static/` | `/home/<username>/Releaf/staticfiles` |
| `/media/` | `/home/<username>/Releaf/media` |

The SQLite database and uploaded files live in your home directory and persist
across web-app reloads. The free account has limited storage, so keep uploaded
images small and back up the database and `media/` directory.

## 5. Reload and verify

Click **Reload** in the Web tab, then verify the public site, login, static
styles, and an uploaded plant image. For code updates, upload the changes,
rerun migrations if needed, run `collectstatic` after static changes, and
reload the web app.
