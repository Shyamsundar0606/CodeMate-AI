# CodeMate PostgreSQL

Run infrastructure/start-postgres.ps1 from Windows PowerShell (see docs/WINDOWS.md).
It verifies Docker, container ownership and port 5433 before starting only the
codemate-ai Compose postgres service. It supports an already-running CodeMate
container and stops on a foreign port/name conflict. No other services are changed.

PostgreSQL 16 Alpine binds 127.0.0.1:5433 to internal 5432 and stores data in
codemate-ai-postgres-data. The read-only initialization script creates the dedicated
application and test roles/databases, revokes cross-database connection permissions,
and leaves both roles without superuser/role-creation/database-creation privileges.
The separate codemate_owner bootstrap role retains PostgreSQL-required superuser
privileges and its own ignored local password; the backend never uses that role.
The health check runs an authenticated TCP SELECT 1 as the app role, so it cannot
report readiness during the temporary socket-only initialization server.
The script runs only against an empty CodeMate volume.

Stop with docker compose -p codemate-ai stop postgres. Preserve the volume.
Compose deployment, Redis, workers and monitoring belong to later milestones.
