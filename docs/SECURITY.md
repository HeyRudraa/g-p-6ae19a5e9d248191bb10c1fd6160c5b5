# Security and data boundaries

Orbit uses Firebase Authentication for credentials and email verification. The API verifies Firebase ID tokens before granting access. Passwords are never stored by Orbit. Profiles, class memberships, subject assignments, assignments, submissions, and grades are stored in PostgreSQL.

## Current protections

- The account uses one sign-in; class membership determines learner, class admin, or subject-teacher access.
- Class admins can manage only their own class. Subject teachers can manage submissions and grades only for subjects assigned to them in that class.
- Learners can read only their own returned grades and submissions. Class admins and assigned teachers are authorized on the server for their class scope.
- Quiz answer keys are not returned to clients. Suggested objective scores are not returned as grades until a teacher reviews and returns them.
- Uploads are size-limited, type allow-listed, assigned random storage keys, and downloaded only through an authorized API route.
- The Python practice service interprets a small AST subset without `eval`, `exec`, imports, file access, or network access. It limits steps, output, collection size, and numeric/text values.

## Before production deployment

Configure Firebase authorized domains, protect service-account credentials, use strong database credentials and managed PostgreSQL backups, and deploy behind HTTPS with restrictive CORS. Add privacy, retention, deletion/export, consent, audit, malware scanning, AI-provider privacy/rate limits, and operational monitoring before real student data is used. Local Docker credentials are development defaults and must be changed.

The study assistant sends prompts to the configured provider; review its retention and student-privacy terms before use. Local PDF and document tools operate in the user's browser.
