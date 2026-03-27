# Fix "relation already exists" when running alembic upgrade head

Your database already has tables (e.g. `hospitals`) but Alembic's version table is empty or out of sync, so it tries to re-apply the initial migration and fails.

## Step 1: Stamp with the revision that matches your DB

If your database has **only** the initial schema (hospitals, users, roles, etc. from the first migration):

```powershell
alembic stamp d38c70f097c0
```

This tells Alembic: "Consider revision `d38c70f097c0` (Initial migration) as already applied."

If your database had **more** migrations applied before (e.g. you got to lab_reports_005 and then something cleared the version table), you can stamp with a later revision so only the missing ones run. Examples:

- After initial only: `alembic stamp d38c70f097c0`
- After pharmacy + fix_pm_fk + lab through lab_reports_005: `alembic stamp lab_reports_005`  
  (Then run `alembic upgrade head` to apply the rest.)

## Step 2: Run the rest of the migrations

```powershell
alembic upgrade head
```

If you stamped with `d38c70f097c0`, this will apply all later migrations. If you see "relation X already exists" again, stamp with the revision that creates that table (e.g. `alembic stamp pharmacy_001`) and run `alembic upgrade head` again until you reach head.

## Check current DB revision (optional)

To see what Alembic thinks is applied:

```powershell
alembic current
```

To list all revision IDs:

```powershell
alembic history
```
