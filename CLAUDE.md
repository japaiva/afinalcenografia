# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands
- Setup: `pip install -r requirements.txt`
- Run server: `python manage.py runserver`
- Run tests: `python manage.py test`
- Run specific test: `python manage.py test app_name.tests.test_module`
- Make migrations: `python manage.py makemigrations`
- Apply migrations: `python manage.py migrate`
- Docker build: `docker-compose up --build`

## Code Style Guidelines
- Follow Django naming conventions (apps in lowercase, models in singular CamelCase)
- Use type hints in service classes (especially in core/services/rag/)
- Structure views in views/ directories with logical separation
- Import order: Python stdlib, Django modules, third-party packages, local modules
- Use explicit exception handling (try/except with specific exceptions)
- Document classes and methods with docstrings
- Organize related functionality into apps (core, cliente, projetos, gestor, etc.)
- Store environment-specific settings in settings.py
- Use Django's ORM for all database operations