# Academic Integrity and Similarity Case Management System

## 1. Project Overview

The Academic Integrity and Similarity Case Management System is a Flask-based web application designed to manage academic integrity cases, similarity reports, evidence, reviewer assignments, decisions, appeals, and audit history.

The system supports a fair and transparent review process. Similarity flags trigger human review and do not automatically establish academic misconduct.

## 2. Key Features

- Dashboard displaying case statistics and system activity.
- Submission and similarity report management.
- Case creation and status tracking.
- Reviewer assignment and conflict-of-interest management.
- Evidence submission and tracking.
- Decision recording with rationale.
- Appeal submission and review.
- Independent review management.
- Audit history for tracking system activities.
- SQLite database integration.

## 3. Technologies Used

- Python 3.11
- Flask
- Flask-SQLAlchemy
- SQLite
- HTML5
- CSS3
- Bootstrap
- JavaScript
- Pandas
- NumPy

## 4. Database Structure

The application uses SQLite for persistent storage.

| Table | Description |
|---|---|
| learner | Learner information |
| assessment | Assessment information |
| integrity_rule | Academic integrity rules |
| reviewer | Reviewer information |
| submission | Learner submissions |
| similarity_report | Similarity analysis results |
| case | Academic integrity cases |
| evidence_item | Evidence associated with cases |
| decision | Recorded case decisions |
| appeal | Learner appeals |
| conflict_of_interest | Reviewer conflict declarations |
| independent_review | Independent review records |
| audit_event | System activity history |

## 5. Dataset Information

The project database contains:

| Entity | Records |
|---|---:|
| Learners | 2,000 |
| Assessments | 20 |
| Reviewers | 10 |
| Submissions | 10,000 |
| Similarity Reports | 10,000 |
| Flagged Reports | 1,000 |
| Non-Flagged Reports | 9,000 |
| Cases | 300 |
| Evidence Items | 591 |
| Decisions | 221 |
| Appeals | 61 |
| Conflict Records | 3 |
| Independent Reviews | 1 |
| Audit Events | 887 |

Database verification was performed using SQLite queries.

## 6. Project Installation

### Prerequisites

- Python 3.11 or later
- Visual Studio Code
- pip

### Step 1: Clone or open the project

Open the project directory in Visual Studio Code.

### Step 2: Create a virtual environment

```bash
python -m venv venv
```

### Step 3: Activate the virtual environment

Windows PowerShell:

```powershell
venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```cmd
venv\Scripts\activate
```

### Step 4: Install dependencies

```bash
pip install -r requirements.txt
```

## 7. Running the Application

Start the Flask application:

```bash
python app.py
```

Open the local application URL displayed in the terminal, usually:

```text
http://127.0.0.1:5000/
```

## 8. Main Application Workflow

1. View the dashboard.
2. Review similarity reports and cases.
3. Open a case to inspect its information.
4. Assign an appropriate reviewer.
5. Declare and manage conflicts of interest.
6. Add supporting evidence.
7. Record a decision with its rationale.
8. Allow learners to submit appeals