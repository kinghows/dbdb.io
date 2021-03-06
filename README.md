Carnegie Mellon Encyclopedia of Database Systems
============

## Requirements

### Ubuntu Packages

```
python-pip
libmysqlclient-dev
```
### Python Packages

Execute this command:
```
pip install -r requirements.txt
```

## Installation Instructions

Clone repository
```bash
git clone https://github.com/cmu-db/dbdb.io.git
```

Create a symlink for the static admin files
```bash
ln -s /usr/local/lib/python2.7/dist-packages/django/contrib/admin/static/admin website/static/admin
```

Removed ROW_FORMAT step because no longer necessary.

To start from scratch, drop the database and recreate it:
```bash
mysqladmin drop -u <user> -p dbdb_io
mysqladmin create -u <user> -p dbdb_io
```

To avoid issues with migrations, if you already have migrations for this app, you should first delete all files from `systems/migrations` EXCEPT for the `__init__.py` and `__init__.pyc` files

* Apply migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

Load in the initial data from the `current_data` directory.
There will be some text output saved to files which indicate  which fields don't match or any other issues in formatting:
```bash
cd current_data
python ./parse_system_data.py
cd ..
```

Load all fixtures - including new ones added by the `parse_system_data` script.
```bash
python manage.py loaddata systems/fixtures/*
```

Create the super user
```
python ./manage.py createsuperuser
```