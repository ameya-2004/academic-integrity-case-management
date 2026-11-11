
import os
import csv
import json
import random
import hashlib

from datetime import datetime, timedelta

from app import app
from database import db

from models import (
    Learner, Assessment, Submission, SimilarityReport,
    IntegrityRule, Case, EvidenceItem, Reviewer,
    Decision, Appeal, AuditEvent
)

SEED = 20261022
rng = random.Random(SEED)

BASE_DATE = datetime(2026, 1, 1)

os.makedirs("exports", exist_ok=True)

def date_after(days):
    return BASE_DATE + timedelta(days=days)


def record_event(entity_type, entity_id, action,
                 old_value=None, new_value=None,
                 performed_by="System"):

    event_number = AuditEvent.query.count() + 1

    event = AuditEvent(
        event_id=f"EVT-2026-{event_number:06d}",
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=action,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
        performed_by=performed_by,
        timestamp=BASE_DATE + timedelta(days=event_number % 300)
    )

    db.session.add(event)


def export_table(model, filename):
    path = os.path.join("exports", filename)
    columns = [column.name for column in model.__table__.columns]

    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()

        for obj in model.query.order_by(model.id).all():
            row = {}

            for column in columns:
                value = getattr(obj, column)

                if isinstance(value, datetime):
                    value = value.isoformat()

                row[column] = value

            writer.writerow(row)


def clear_existing_data():
    # Child tables first, followed by parent tables.
    for model in [
        Appeal, Decision, EvidenceItem, AuditEvent,
        Case, SimilarityReport, Submission,
        Reviewer, IntegrityRule, Assessment, Learner
    ]:
        db.session.query(model).delete(
            synchronize_session=False
        )

    db.session.commit()


def generate():

    print("Starting synthetic data generation...")

    clear_existing_data()

    # -------------------------------------------------
    # 1. MASTER DATA
    # -------------------------------------------------

    learners = []

    for i in range(1, 2001):
        learners.append(
            Learner(
                learner_id=f"LRN-2026-{i:06d}",
                name=f"Learner {i:04d}",
                email=f"learner{i:04d}@example.test",
                department=["Computer Science", "IT", "Electronics"][
                    i % 3
                ],
                created_at=date_after(i % 250)
            )
        )

    db.session.add_all(learners)
    db.session.flush()

    assessments = []

    for i in range(1, 21):
        assessments.append(
            Assessment(
                assessment_id=f"ASM-2026-{i:04d}",
                title=f"Academic Assignment {i}",
                subject=[
                    "Python", "Database Systems",
                    "Machine Learning", "Web Development"
                ][i % 4],
                due_date=date_after(30 + i),
                created_at=BASE_DATE
            )
        )

    db.session.add_all(assessments)

    # Ensure ten reviewers exist.
    reviewers = []

    for i in range(1, 11):
        reviewers.append(
            Reviewer(
                reviewer_id=f"REV-{i:03d}",
                name=f"Academic Reviewer {i}",
                email=f"reviewer{i}@example.test",
                role="Instructor" if i <= 7 else "Administrator",
                active=True
            )
        )

    rule = IntegrityRule(
        rule_id="INT-2026-000001",
        rule_name="Standard Similarity Review",
        review_threshold=30.0,
        description=(
            "Scores at or above 30% trigger human review. "
            "Similarity alone does not prove misconduct."
        ),
        effective_from=BASE_DATE,
        active=True
    )

    db.session.add_all(reviewers)
    db.session.add(rule)
    db.session.flush()

    print("Master records created.")

    # -------------------------------------------------
    # 2. SUBMISSIONS
    # -------------------------------------------------

    submissions = []

    for i in range(1, 10001):

        learner = rng.choice(learners)
        assessment = rng.choice(assessments)

        submissions.append(
            Submission(
                submission_id=f"SUB-2026-{i:06d}",
                learner_id=learner.id,
                assessment_id=assessment.id,
                submitted_at=date_after(rng.randint(1, 280)),
                content_reference=f"synthetic/submission_{i}.txt",
                status="Submitted"
            )
        )

    db.session.add_all(submissions)
    db.session.flush()

    print("10,000 submissions created.")

    # -------------------------------------------------
    # 3. SIMILARITY REPORTS
    # -------------------------------------------------

    flagged_ids = set(
        rng.sample([s.id for s in submissions], 1000)
    )

    reports = []

    for submission in submissions:

        if submission.id in flagged_ids:
            score = round(rng.uniform(30.1, 95.0), 2)
        else:
            score = round(rng.uniform(0.0, 29.9), 2)

        reports.append(
            SimilarityReport(
                similarity_id=(
                    f"SIM-{submission.submission_id}-01"
                ),
                submission_id=submission.id,
                similarity_score=score,
                matched_sources=rng.randint(1, 12)
                    if score >= 30 else rng.randint(0, 3),
                generated_at=submission.submitted_at
                    + timedelta(days=1),
                review_required=score >= 30
            )
        )

    db.session.add_all(reports)
    db.session.flush()

    flagged_reports = [
        report for report in reports
        if report.review_required
    ]

    print("10,000 similarity reports created.")
    print("1,000 similarity flags generated.")

    # -------------------------------------------------
    # 4. CASES
    # -------------------------------------------------

    cases = []
    case_info = []

    for i, report in enumerate(flagged_reports[:300]):

        case_id = f"INT-2026-{i + 1:06d}"

        if i < 40:
            status = "Open"
        elif i < 80:
            status = "Under Review"
        elif i < 180:
            status = "Decision Recorded"
        else:
            status = "Closed"

        reviewer = reviewers[i % len(reviewers)]

        # Case 2 deliberately has a conflicted reviewer.
        if i == 1:
            reviewer_id = reviewer.id
        else:
            reviewer_id = (
                None if i < 40 else reviewer.id
            )

        case = Case(
            case_id=case_id,
            submission_id=report.submission_id,
            similarity_report_id=report.id,
            reviewer_id=reviewer_id,
            status=status,
            issue_type="similarity_review",
            created_at=report.generated_at + timedelta(days=1),
            closed_at=(
                report.generated_at + timedelta(days=10)
                if status == "Closed" else None
            )
        )

        cases.append(case)

    db.session.add_all(cases)
    db.session.flush()

    # -------------------------------------------------
    # 5. EVIDENCE
    # -------------------------------------------------

    evidence_counter = {}

    for i, case in enumerate(cases):

        count = rng.randint(1, 3)
        evidence_counter[case.id] = count

        for j in range(1, count + 1):

            evidence = EvidenceItem(
                evidence_id=f"EVD-{case.case_id}-{j:03d}",
                case_id=case.id,
                evidence_type=[
                    "Similarity Match",
                    "Quoted Material",
                    "Shared Template",
                    "Submission Reference"
                ][j % 4],
                description=(
                    "Synthetic evidence reference for academic review."
                ),
                reference=f"synthetic/evidence/{case.case_id}/{j}",
                added_at=case.created_at + timedelta(days=1),
                added_by="Academic Administrator"
            )

            db.session.add(evidence)

            record_event(
                "EvidenceItem",
                evidence.evidence_id,
                "EVIDENCE_ADDED",
                new_value=evidence.description
            )

    db.session.flush()

    # -------------------------------------------------
    # 6. DECISIONS
    # -------------------------------------------------

    decisions = {}
    expected_outcomes = {}
    decision_counter = 0

    for i, case in enumerate(cases):

        report = flagged_reports[i]
        score = report.similarity_score

        if i % 5 == 0:
            category = "legitimate_quoted_material"
            expected = "No Misconduct"

        elif i % 7 == 0:
            category = "shared_template"
            expected = "No Misconduct"

        else:
            category = "substantive_overlap"

            expected = (
                "Misconduct Confirmed"
                if score >= 65
                else "Insufficient Evidence"
            )

        expected_outcomes[case.id] = expected

        # First 80 cases are awaiting review.
        if i < 80:
            continue

        decision_counter += 1

        actual = expected

        # Edge case 1: automatic guilt despite legitimate quotation.
        if i == 0:
            actual = "Misconduct Confirmed"

        reviewer_id = case.reviewer_id or reviewers[i % 10].id

        decision = Decision(
            decision_id=f"DEC-2026-{decision_counter:06d}",
            case_id=case.id,
            reviewer_id=reviewer_id,
            outcome=actual,
            rationale=(
                "Automatically marked guilty using similarity score only."
                if i == 0
                else (
                    "Human review based on similarity score, evidence "
                    "and documented integrity rules."
                )
            ),
            decided_at=case.created_at + timedelta(days=5)
        )

        decisions[case.id] = decision
        db.session.add(decision)

        record_event(
            "Case",
            case.case_id,
            "DECISION_RECORDED",
            new_value=actual,
            performed_by="System" if i == 0 else f"Reviewer {reviewer_id}"
        )

    db.session.flush()

    # -------------------------------------------------
    # 7. EDGE CASE 3: EVIDENCE AFTER DECISION
    # -------------------------------------------------

    late_case = cases[82]

    late_evidence = EvidenceItem(
        evidence_id=f"EVD-{late_case.case_id}-999",
        case_id=late_case.id,
        evidence_type="Late Evidence",
        description=(
            "Evidence inserted after decision without audit history."
        ),
        reference="synthetic/late_evidence.txt",
        added_at=late_case.created_at + timedelta(days=7),
        added_by="System"
    )

    db.session.add(late_evidence)

    # Deliberately do not create an AuditEvent for this evidence.

    # -------------------------------------------------
    # 8. APPEALS
    # -------------------------------------------------

    successful_candidates = []

    for i in range(180, 300):
        case = cases[i]

        if expected_outcomes[case.id] == "Misconduct Confirmed":
            successful_candidates.append(case)

    if len(successful_candidates) < 15:
        raise ValueError("Not enough successful appeal candidates.")

    successful_cases = successful_candidates[:15]

    excluded = {case.id for case in successful_cases}
    excluded.add(cases[82].id)
    excluded.add(cases[83].id)

    remaining = [
        case for case in cases
        if case.id not in excluded and case.id in decisions
    ]

    rejected_cases = remaining[:20]

    used = excluded | {case.id for case in rejected_cases}

    pending_cases = [
        case for case in cases
        if case.id in decisions and case.id not in used
    ][:24]

    appeal_groups = [
        (successful_cases, "Closed", "Decision Overturned"),
        (rejected_cases, "Closed", "Decision Upheld"),
        (pending_cases, "Pending", None)
    ]

    appeal_counter = 0

    for group, status, outcome in appeal_groups:

        for case in group:

            appeal_counter += 1

            assigned_reviewer = case.reviewer_id or reviewers[0].id

            independent = next(
                r for r in reviewers
                if r.id != assigned_reviewer
            )

            appeal = Appeal(
                appeal_id=f"APL-{case.case_id}-01",
                case_id=case.id,
                reason="Learner requests an independent review.",
                status=status,
                independent_reviewer_id=(
                    independent.id if status == "Closed" else None
                ),
                outcome=outcome,
                submitted_at=case.created_at + timedelta(days=6),
                reviewed_at=(
                    case.created_at + timedelta(days=9)
                    if status == "Closed" else None
                )
            )

            db.session.add(appeal)

            record_event(
                "Appeal",
                appeal.appeal_id,
                "APPEAL_SUBMITTED"
            )

    # Edge case 4: appeal closed without independent review.
    invalid_case = cases[83]

    invalid_appeal = Appeal(
        appeal_id=f"APL-{invalid_case.case_id}-01",
        case_id=invalid_case.id,
        reason="Synthetic invalid appeal scenario.",
        status="Closed",
        independent_reviewer_id=None,
        outcome="Closed without independent review",
        submitted_at=invalid_case.created_at + timedelta(days=6),
        reviewed_at=None
    )

    db.session.add(invalid_appeal)

    # -------------------------------------------------
    # 9. EDGE CASE 2: REVIEWER CONFLICT
    # -------------------------------------------------

    conflict_case = cases[1]

    record_event(
        "Case",
        conflict_case.case_id,
        "REVIEWER_CONFLICT_FLAGGED",
        new_value=(
            f"Assigned reviewer {conflict_case.reviewer_id} "
            "has a conflict of interest."
        )
    )

    # -------------------------------------------------
    # 10. COMMIT DATABASE
    # -------------------------------------------------

    db.session.commit()

    # -------------------------------------------------
    # 11. GROUND TRUTH - SEPARATE FROM INPUT DATA
    # -------------------------------------------------

    anomalies = {
        0: (
            "automatic_guilt",
            "System must never decide guilt from similarity alone."
        ),
        1: (
            "reviewer_conflict",
            "Conflict must be checked and reviewer reassigned."
        ),
        82: (
            "evidence_without_history",
            "Evidence changes must have an audit event."
        ),
        83: (
            "appeal_without_independent_review",
            "Appeal closure requires independent review."
        )
    }

    ground_truth_path = "exports/ground_truth.csv"

    with open(
        ground_truth_path, "w", newline="", encoding="utf-8"
    ) as file:

        fields = [
            "case_id",
            "issue_type",
            "expected_outcome",
            "actual_outcome",
            "is_anomaly",
            "expected_behavior"
        ]

        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()

        for i, case in enumerate(cases):

            anomaly = anomalies.get(i)

            decision = decisions.get(case.id)

            actual = (
                decision.outcome if decision
                else "Pending Review"
            )

            writer.writerow({
                "case_id": case.case_id,
                "issue_type": (
                    anomaly[0] if anomaly else "normal_case"
                ),
                "expected_outcome": expected_outcomes[case.id],
                "actual_outcome": actual,
                "is_anomaly": bool(anomaly),
                "expected_behavior": (
                    anomaly[1] if anomaly
                    else "Follow documented review rules."
                )
            })

    # -------------------------------------------------
    # 12. EXPORT ALL BUSINESS TABLES
    # -------------------------------------------------

    tables = [
        (Learner, "learners.csv"),
        (Assessment, "assessments.csv"),
        (Submission, "submissions.csv"),
        (SimilarityReport, "similarity_reports.csv"),
        (IntegrityRule, "integrity_rules.csv"),
        (Case, "cases.csv"),
        (EvidenceItem, "evidence_items.csv"),
        (Reviewer, "reviewers.csv"),
        (Decision, "decisions.csv"),
        (Appeal, "appeals.csv"),
        (AuditEvent, "audit_events.csv")
    ]

    for model, filename in tables:
        export_table(model, filename)

    # -------------------------------------------------
    # 13. VALIDATION
    # -------------------------------------------------

    checks = {
        "learners": Learner.query.count() == 2000,
        "assessments": Assessment.query.count() == 20,
        "submissions": Submission.query.count() == 10000,
        "similarity_reports": SimilarityReport.query.count() == 10000,
        "flags": SimilarityReport.query.filter_by(
            review_required=True
        ).count() == 1000,
        "cases": Case.query.count() == 300,
        "reviewers": Reviewer.query.count() == 10,
        "evidence": EvidenceItem.query.count() >= 300,
        "foreign_keys": all(
            db.session.get(Learner, s.learner_id) is not None
            and db.session.get(Assessment, s.assessment_id) is not None
            for s in Submission.query.all()
        ),
        "report_links": all(
            db.session.get(Submission, r.submission_id) is not None
            for r in SimilarityReport.query.all()
        )
    }

    # -------------------------------------------------
    # 14. REPRODUCIBILITY CHECKSUMS
    # -------------------------------------------------

    checksums = {}

    for _, filename in tables:
        path = os.path.join("exports", filename)

        with open(path, "rb") as file:
            checksums[filename] = hashlib.sha256(
                file.read()
            ).hexdigest()

    with open("exports/checksums.json", "w") as file:
        json.dump(checksums, file, indent=4)

    manifest = {
        "dataset": "Academic Integrity Synthetic Dataset",
        "seed": SEED,
        "generated_at": "2026-11-11",
        "external_data_used": False,
        "source": "Fully synthetic data",
        "submissions": 10000,
        "similarity_reports": 10000,
        "flags": 1000,
        "cases": 300,
        "ground_truth_separate": True
    }

    with open("exports/source_manifest.json", "w") as file:
        json.dump(manifest, file, indent=4)

    with open("exports/validation_report.txt", "w") as file:
        file.write("ACADEMIC INTEGRITY DATA VALIDATION\n")
        file.write("=" * 40 + "\n")

        for name, passed in checks.items():
            file.write(
                f"{name}: {'PASS' if passed else 'FAIL'}\n"
            )

        file.write("\n")
        file.write(
            "Intentional anomalies: 4\n"
        )
        file.write(
            "Anomaly labels stored separately in ground_truth.csv\n"
        )

    print("\nDATA GENERATION COMPLETED")
    print("=" * 40)

    for name, passed in checks.items():
        print(name, "PASS" if passed else "FAIL")

    print("\nExports saved in the exports folder.")

    if not all(checks.values()):
        raise ValueError("One or more validation checks failed.")


if __name__ == "__main__":
    with app.app_context():
        generate()

