# Orbit learning platform

Orbit is a structured learning workspace for learners and teachers. The repository is split into a Next.js web client and a FastAPI API backed by PostgreSQL. Firebase Authentication handles account credentials and email verification; FastAPI verifies Firebase ID tokens and owns application profiles, classrooms, assignments, submissions, and grades.

## Project map

```text
frontend/
  app/                 App Router pages and route layouts
  components/          Shared layout and auth UI
  features/            Auth, classroom, assignment, grades, coding, study, tools, profile
  lib/api/              Authenticated API client and API types
  lib/firebase/         Firebase browser initialization
backend/
  app/api/v1/           Versioned HTTP routes and dependencies
  app/core/              Settings and Firebase Admin setup
  app/db/                SQLAlchemy engine and metadata
  app/models/            PostgreSQL entities
  app/schemas/           Request and response validation
  app/services/          Access rules, bounded Python runner, study provider
  alembic/               Database migrations
  tests/                 Service and API tests
  var/uploads/           Local assignment attachment storage (ignored)
docs/                    Product and security notes
sources/                 Synced project references (read-only)
```

## Local setup

Requirements: Node.js 20.9+, Python 3.12+, Docker Desktop (or PostgreSQL 16+ installed), and a Firebase project.

1. Copy `.env.example` to `.env` and fill PostgreSQL and Firebase Admin values. Keep the Firebase service-account JSON outside this repository.
2. Copy `frontend/.env.local.example` to `frontend/.env.local` and fill the Firebase web app values.
3. In Firebase Console, enable Email/Password and Google sign-in and authorize your local/deployed domains.
4. Start PostgreSQL with `docker compose up -d db`.
5. In `backend/`, create a virtual environment, install `requirements.txt`, run `alembic upgrade head`, then start `uvicorn app.main:app --reload`.
6. From the repository root, run `npm install` and `npm run dev`.
7. Open `http://localhost:3000`. FastAPI docs are at `http://localhost:8000/docs`.

For a full Docker run, configure `.env` and use `docker compose up --build`, then apply the migration with `alembic upgrade head` in the API container.

## Account and class permissions

Everyone uses the same sign-in. A user can create a class, and its creator becomes that class's admin. The class admin can assign an existing Orbit user as a teacher for one or more subjects, remove subject access, or transfer class ownership to a class member. Any user can also join other classes as a learner. Permissions are scoped to each class; the account itself does not have a separate teacher login or a global teacher role.

## Feature flows

- Firebase email/password and Google sign-in, email verification, password reset, and profile onboarding.
- Class creation/join, class admin controls, subject teacher assignment, ownership transfer, announcements, and resources.
- Assignment creation by class admins and subject-assigned teachers, learner turn-in with text/objective answers/files, and teacher grading.
- Private returned grades for learners. Objective quiz scoring is only a suggestion until a teacher returns a grade.
- Restricted educational Python practice and a provider-configured study assistant endpoint.
- Browser-based PDF reading, image-to-PDF print flow, and notes export.

Firebase, PostgreSQL, and (for study responses) an AI provider must be configured for their respective flows to work. The app reports setup or connection errors instead of pretending to save data.
