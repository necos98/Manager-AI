---
name: django
category: tech
description: Django patterns, ORM, DRF conventions
built_in: true
---
# Django Conventions

## Structure
- Fat models, thin views
- Managers for complex querysets
- `select_related` / `prefetch_related` to avoid N+1

## API (DRF)
- ViewSets with routers for CRUD
- Serializer validation, never validate in views
- `IsAuthenticated` as default permission class

## Testing
- pytest-django, `@pytest.mark.django_db`
- `baker` (model_bakery) for test data
- Test serializers and views separately

## Naming
- Models: singular PascalCase
- URLs: kebab-case
- Apps: plural snake_case
