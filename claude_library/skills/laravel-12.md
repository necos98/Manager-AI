---
name: laravel-12
category: tech
description: Patterns, conventions, Eloquent, Pest for Laravel 12
built_in: true
---
# Laravel 12 Conventions

## Architecture
- Use Repository pattern for data access layer
- Service classes for business logic (inject via constructor)
- Form Requests for validation
- API Resources for response transformation

## Models & Eloquent
- Define `$fillable` explicitly, never use `$guarded = []`
- Use typed properties in models
- Relationships: `hasMany`, `belongsTo`, `belongsToMany` with explicit foreign keys
- Scopes for reusable query logic

## Testing
- Use Pest PHP for all tests
- `RefreshDatabase` trait for database tests
- Factory-based test data, never raw inserts
- Feature tests in `tests/Feature/`, unit tests in `tests/Unit/`

## API
- RESTful routes in `api.php`, versioned under `/api/v1/`
- Return `JsonResource` or `ResourceCollection`, never raw arrays
- HTTP status codes: 201 for creation, 204 for deletion, 422 for validation errors

## Naming
- Controllers: `PascalCase`, suffix `Controller`
- Migrations: snake_case descriptive names (`create_users_table`)
- Events: past tense (`UserRegistered`, `OrderShipped`)
