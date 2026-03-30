---
name: nestjs
category: tech
description: NestJS modules, decorators, TypeORM conventions
built_in: true
---
# NestJS Conventions

## Structure
- Feature modules: controller + service + module + entity
- DTOs with class-validator decorators for all inputs
- Repositories via TypeORM `@InjectRepository`

## Patterns
- Guards for auth, Pipes for validation, Interceptors for transformation
- Exception filters for consistent error responses
- `ConfigModule` for environment variables

## Testing
- Jest for unit tests, supertest for e2e
- `Test.createTestingModule` for unit test setup
- Mock services explicitly, never mock repositories in e2e
