# QCMS Enterprise

QCMS Enterprise is a Flask-based quality management system for structured problem solving, project tracking, approvals, and knowledge capture. The workspace contains a Flask backend, a static HTML/CSS/JavaScript frontend, and PostgreSQL-backed persistence.

## Overview

The application centers on an 8-stage workflow used to move projects from problem definition through analysis, approval, implementation, verification, and standardization. Role-based access controls cover Admin, Reviewer, Facilitator, Team Leader, and Team Member workflows.

```mermaid
graph TD
    U[Browser UI] --> F[Frontend HTML/CSS/JS]
    F --> B[Flask App]
    B --> A[JWT + RBAC + Workflow APIs]
    A --> D[(PostgreSQL)]
```

## Repository Layout

```text
.
├── backend/        # Flask API, models, migrations/helpers, scripts
├── frontend/       # Static web app served by Nginx or Flask
├── API_DOCUMENTATION.md
├── README.md
└── docker-compose.yml
```

## Features

- 8-stage project workflow with stage tracking and approval gates.
- Role-based dashboards for Admin, Reviewer, Facilitator, Team Leader, and Team Member.
- Project, department, repository, analytics, and audit-style views.
- Email support via Resend for verification and notifications.
- PDF and spreadsheet report generation in the backend utilities.

## Tech Stack

| Layer | Stack |
| :--- | :--- |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Backend | Python 3.10+, Flask, SQLAlchemy, Flask-JWT-Extended, Flask-Bcrypt, Flask-CORS |
| Database | PostgreSQL |
| Deployment | Docker, Docker Compose, Nginx |
| Reporting | pandas, openpyxl, fpdf2 |

## Requirements

- Python 3.10 or newer.
- PostgreSQL if you are running the backend outside Docker.
- Docker and Docker Compose if you want the full stack locally.

## Quick Start

### Docker Compose

This is the fastest way to run the full system.

```bash
docker-compose up --build
```

Services exposed by the compose file:

- Frontend: `http://localhost:80`
- Backend API: `http://localhost:5000`

### Manual Backend Run

```bash
cd backend
pip install -r requirements.txt
python setup_db.py
python run.py
```

The backend bootstrap will create missing tables and seed the default roles. The setup script also creates an initial admin account if one does not already exist.

### Default Credentials

The seeded admin account uses:

- Username: `admin`
- Password: `admin123`

Change these immediately after first login.

## Environment Variables

The backend reads its configuration from `backend/.env`. The main values used by the app are:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`
- `FLASK_APP`
- `FLASK_ENV`
- `PORT`

Example database format:

```text
DATABASE_URL=postgresql://user:password@host:5432/database_name
```

## Key Entry Points

- Backend app factory and route registration: [backend/app/__init__.py](backend/app/__init__.py)
- Backend development runner: [backend/run.py](backend/run.py)
- Database bootstrap and role seeding: [backend/setup_db.py](backend/setup_db.py)
- Frontend landing page: [frontend/index.html](frontend/index.html)
- API reference: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

## Frontend Pages

The static frontend includes pages for:

- Authentication: login, register, forgot/reset password
- Dashboards: admin, reviewer, facilitator, team leader, team member
- Projects: workspace, details, repository
- Admin flows: users, departments, settings, audit queue, audit logs
- Knowledge views: repository, standards, analytics, profile pages

## Backend API Surface

The Flask app registers the following major API groups:

- `/api/auth`
- `/api/projects`
- `/api/workflow`
- `/api/analytics`
- `/api/admin`
- `/api/facilitator`
- `/api/reviewer`
- `/api/team-leader`
- `/api/team-member`
- `/api/project`
- `/api/dashboard`
- `/api/repository`

## Notes

- The backend serves the frontend static files directly when run through Flask.
- `docker-compose.yml` also defines a separate Nginx frontend container.
- Uploaded files are served from the backend `uploads/` directory.

## More Documentation

- [Backend Developer Guide](backend/README.md)
- [Frontend Developer Guide](frontend/README.md)
- [API Documentation](API_DOCUMENTATION.md)



