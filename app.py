
import os
from datetime import datetime
from uuid import uuid4

from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    redirect,
    url_for
)

from database import db

from models import (
    Learner,
    Assessment,
    Submission,
    SimilarityReport,
    IntegrityRule,
    Case,
    EvidenceItem,
    Reviewer,
    Decision,
    Appeal,
    AuditEvent,
    ConflictOfInterest,
    IndependentReview
)


app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "academic-integrity-development-key"
)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///integrity.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# --------------------------------------------------
# AUDIT EVENT HELPER
# --------------------------------------------------

def record_event(
    entity_type,
    entity_id,
    action,
    old_value=None,
    new_value=None,
    performed_by="Administrator"
):
    event = AuditEvent(
        event_id=f"EVT-{uuid4().hex[:12]}",
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=action,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
        performed_by=performed_by,
        timestamp=datetime.utcnow()
    )

    db.session.add(event)


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

def initialize_database():

    with app.app_context():

        db.create_all()

        if IntegrityRule.query.count() == 0:

            rule = IntegrityRule(
                rule_id="INT-2026-000001",
                rule_name="Standard Similarity Review",
                review_threshold=30,
                description=(
                    "Similarity scores above 30% trigger human review. "
                    "They do not establish guilt."
                )
            )

            db.session.add(rule)

        if Reviewer.query.count() == 0:

            reviewers = [
                Reviewer(
                    reviewer_id="REV-001",
                    name="Academic Reviewer 1",
                    email="reviewer1@example.com",
                    role="Instructor"
                ),
                Reviewer(
                    reviewer_id="REV-002",
                    name="Academic Reviewer 2",
                    email="reviewer2@example.com",
                    role="Administrator"
                )
            ]

            db.session.add_all(reviewers)

        db.session.commit()


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@app.route("/")
def dashboard():

    stats = {
        "learners": Learner.query.count(),

        "submissions": Submission.query.count(),

        "flags": SimilarityReport.query.filter_by(
            review_required=True
        ).count(),

        "cases": Case.query.count(),

        "open_cases": Case.query.filter_by(
            status="Open"
        ).count(),

        "appeals": Appeal.query.filter_by(
            status="Pending"
        ).count()
    }

    recent_cases = Case.query.order_by(
        Case.created_at.desc()
    ).limit(5).all()

    return render_template(
        "dashboard.html",
        stats=stats,
        recent_cases=recent_cases
    )


@app.route("/api/stats")
def api_stats():

    return jsonify({
        "learners": Learner.query.count(),
        "submissions": Submission.query.count(),
        "flags": SimilarityReport.query.filter_by(
            review_required=True
        ).count(),
        "cases": Case.query.count(),
        "appeals": Appeal.query.count()
    })


@app.route("/health")
def health():

    return jsonify({
        "status": "running"
    })


# --------------------------------------------------
# CASE LIST
# --------------------------------------------------

@app.route("/cases")
def cases():

    all_cases = Case.query.order_by(
        Case.created_at.desc()
    ).all()

    return render_template(
        "cases.html",
        cases=all_cases
    )


# --------------------------------------------------
# CASE DETAILS
# --------------------------------------------------

@app.route("/case/<int:case_id>")
def case_details(case_id):

    selected_case = Case.query.get_or_404(case_id)

    reviewers = Reviewer.query.filter_by(
        active=True
    ).order_by(Reviewer.name).all()

    return render_template(
        "case_details.html",
        case=selected_case,
        reviewers=reviewers
    )


# --------------------------------------------------
# REVIEWER MANAGEMENT
# --------------------------------------------------

@app.route("/reviewers")
def reviewers():

    all_reviewers = Reviewer.query.order_by(
        Reviewer.name
    ).all()

    return render_template(
        "reviewers.html",
        reviewers=all_reviewers
    )


# --------------------------------------------------
# ASSIGN REVIEWER
# --------------------------------------------------

@app.route(
    "/case/<int:case_id>/assign-reviewer",
    methods=["POST"]
)
def assign_reviewer(case_id):

    selected_case = Case.query.get_or_404(case_id)

    if selected_case.decisions:
        return "Reviewer cannot be changed after a decision.", 400

    reviewer_id = request.form.get(
        "reviewer_id",
        type=int
    )

    reviewer = Reviewer.query.filter_by(
        id=reviewer_id,
        active=True
    ).first()

    if not reviewer:
        return "Invalid or inactive reviewer.", 400

    conflict = ConflictOfInterest.query.filter_by(
        case_id=selected_case.id,
        reviewer_id=reviewer.id
    ).first()

    if conflict:
        return (
            "This reviewer has declared a conflict of interest "
            "for this case and cannot be assigned.",
            400
        )

    old_reviewer = (
        selected_case.reviewer.reviewer_id
        if selected_case.reviewer
        else "Unassigned"
    )

    if selected_case.reviewer_id == reviewer.id:
        return redirect(
            url_for(
                "case_details",
                case_id=selected_case.id
            )
        )

    selected_case.reviewer_id = reviewer.id

    if selected_case.status == "Open":
        selected_case.status = "Under Review"

    record_event(
        "Case",
        selected_case.case_id,
        "Reviewer Assigned",
        old_reviewer,
        reviewer.reviewer_id
    )

    db.session.commit()

    return redirect(
        url_for(
            "case_details",
            case_id=selected_case.id
        )
    )


# --------------------------------------------------
# DECLARE CONFLICT OF INTEREST
# --------------------------------------------------

@app.route(
    "/case/<int:case_id>/declare-conflict",
    methods=["POST"]
)
def declare_conflict(case_id):

    selected_case = Case.query.get_or_404(case_id)

    reviewer_id = request.form.get(
        "reviewer_id",
        type=int
    )

    reason = request.form.get(
        "reason",
        ""
    ).strip()

    declared_by = request.form.get(
        "declared_by",
        "Administrator"
    ).strip() or "Administrator"

    reviewer = Reviewer.query.filter_by(
        id=reviewer_id
    ).first()

    if not reviewer:
        return "Invalid reviewer.", 400

    if not reason:
        return "Conflict declaration reason is required.", 400

    existing_conflict = ConflictOfInterest.query.filter_by(
        case_id=selected_case.id,
        reviewer_id=reviewer.id
    ).first()

    if existing_conflict:
        return (
            "A conflict is already declared for this reviewer and case.",
            400
        )

    conflict = ConflictOfInterest(
        case_id=selected_case.id,
        reviewer_id=reviewer.id,
        reason=reason,
        declared_by=declared_by,
        declared_at=datetime.utcnow()
    )

    db.session.add(conflict)

    old_reviewer = (
        selected_case.reviewer.reviewer_id
        if selected_case.reviewer
        else "Unassigned"
    )

    # Conflict declared before a decision.

    if (
        selected_case.reviewer_id == reviewer.id
        and not selected_case.decisions
    ):

        selected_case.reviewer_id = None
        selected_case.status = "Open"

        record_event(
            "Case",
            selected_case.case_id,
            "Reviewer Unassigned Due To Conflict",
            old_reviewer,
            "Unassigned",
            declared_by
        )

    # Conflict declared after a decision.
    # Preserve the original decision.

    if selected_case.decisions:

        old_status = selected_case.status

        selected_case.status = "Independent Review Required"

        record_event(
            "Case",
            selected_case.case_id,
            "Independent Review Required",
            old_status,
            (
                f"Conflict declared for {reviewer.reviewer_id}. "
                f"Reason: {reason}"
            ),
            declared_by
        )

    record_event(
        "ConflictOfInterest",
        f"{selected_case.case_id}-{reviewer.reviewer_id}",
        "Conflict Declared",
        None,
        f"{reviewer.reviewer_id}: {reason}",
        declared_by
    )

    db.session.commit()

    return redirect(
        url_for(
            "case_details",
            case_id=selected_case.id
        )
    )


# --------------------------------------------------
# ADD EVIDENCE
# --------------------------------------------------

@app.route(
    "/case/<int:case_id>/add-evidence",
    methods=["POST"]
)
def add_evidence(case_id):

    selected_case = Case.query.get_or_404(case_id)

    evidence_type = request.form.get(
        "evidence_type",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    reference = request.form.get(
        "reference",
        ""
    ).strip()

    added_by = request.form.get(
        "added_by",
        "Administrator"
    ).strip() or "Administrator"

    if not evidence_type or not description:
        return "Evidence type and description are required.", 400

    evidence_number = EvidenceItem.query.filter_by(
        case_id=selected_case.id
    ).count() + 1

    evidence = EvidenceItem(
        evidence_id=(
            f"EVD-{selected_case.case_id}-{evidence_number:03d}"
        ),
        case_id=selected_case.id,
        evidence_type=evidence_type,
        description=description,
        reference=reference,
        added_by=added_by
    )

    db.session.add(evidence)

    if selected_case.decisions:
        action = "Evidence Added After Decision"
    else:
        action = "Evidence Added"

    record_event(
        "Evidence",
        evidence.evidence_id,
        action,
        None,
        description,
        added_by
    )

    db.session.commit()

    return redirect(
        url_for(
            "case_details",
            case_id=selected_case.id
        )
    )


# --------------------------------------------------
# RECORD DECISION
# --------------------------------------------------

@app.route(
    "/case/<int:case_id>/add-decision",
    methods=["POST"]
)
def add_decision(case_id):

    selected_case = Case.query.get_or_404(case_id)

    if not selected_case.reviewer_id:
        return "Assign a reviewer before recording a decision.", 400

    if selected_case.decisions:
        return "A decision has already been recorded for this case.", 400

    reviewer = db.session.get(
        Reviewer,
        selected_case.reviewer_id
    )

    if not reviewer or not reviewer.active:
        return "The assigned reviewer is inactive.", 400

    conflict = ConflictOfInterest.query.filter_by(
        case_id=selected_case.id,
        reviewer_id=reviewer.id
    ).first()

    if conflict:
        return "A conflicted reviewer cannot record a decision.", 400

    outcome = request.form.get(
        "outcome",
        ""
    ).strip()

    rationale = request.form.get(
        "rationale",
        ""
    ).strip()

    if not outcome or not rationale:
        return "Outcome and rationale are required.", 400

    decision = Decision(
        decision_id=f"DEC-{uuid4().hex[:12]}",
        case_id=selected_case.id,
        reviewer_id=reviewer.id,
        outcome=outcome,
        rationale=rationale
    )

    db.session.add(decision)

    old_status = selected_case.status

    selected_case.status = "Decision Recorded"

    record_event(
        "Case",
        selected_case.case_id,
        "Decision Recorded",
        old_status,
        outcome,
        reviewer.name
    )

    db.session.commit()

    return redirect(
        url_for(
            "case_details",
            case_id=selected_case.id
        )
    )


# --------------------------------------------------
# SUBMIT APPEAL
# --------------------------------------------------

@app.route(
    "/case/<int:case_id>/submit-appeal",
    methods=["POST"]
)
def submit_appeal(case_id):

    selected_case = Case.query.get_or_404(case_id)

    reason = request.form.get(
        "reason",
        ""
    ).strip()

    if not reason:
        return "Appeal reason is required.", 400

    if not selected_case.decisions:
        return "An appeal requires a recorded decision.", 400

    if selected_case.appeals:
        return "An appeal has already been submitted for this case.", 400

    appeal_number = Appeal.query.filter_by(
        case_id=selected_case.id
    ).count() + 1

    appeal = Appeal(
        appeal_id=(
            f"APL-{selected_case.case_id}-{appeal_number:02d}"
        ),
        case_id=selected_case.id,
        reason=reason,
        status="Pending"
    )

    db.session.add(appeal)

    record_event(
        "Appeal",
        appeal.appeal_id,
        "Appeal Submitted",
        None,
        reason
    )

    db.session.commit()

    return redirect(
        url_for(
            "case_details",
            case_id=selected_case.id
        )
    )


# --------------------------------------------------
# INDEPENDENT CASE REVIEW
# --------------------------------------------------

@app.route(
    "/case/<int:case_id>/independent-review",
    methods=["POST"]
)
def complete_independent_review(case_id):

    selected_case = Case.query.get_or_404(case_id)

    if selected_case.status != "Independent Review Required":
        return "This case does not currently require independent review.", 400

    if not selected_case.decisions:
        return "An original decision is required before independent review.", 400

    if selected_case.independent_reviews:
        return "An independent review has already been completed.", 400

    reviewer_id = request.form.get(
        "reviewer_id",
        type=int
    )

    outcome = request.form.get(
        "outcome",
        ""
    ).strip()

    rationale = request.form.get(
        "rationale",
        ""
    ).strip()

    allowed_outcomes = [
        "Decision Upheld",
        "Decision Overturned",
        "Further Review Required"
    ]

    if outcome not in allowed_outcomes:
        return "Select a valid independent review outcome.", 400

    if not rationale:
        return "Independent review rationale is required.", 400

    reviewer = Reviewer.query.filter_by(
        id=reviewer_id,
        active=True
    ).first()

    if not reviewer:
        return "Invalid or inactive independent reviewer.", 400

    # Exclude the currently assigned reviewer.

    if selected_case.reviewer_id == reviewer.id:
        return "The assigned case reviewer cannot conduct independent review.", 400

    # Exclude every reviewer who recorded an original decision.

    original_decision_reviewer_ids = {
        decision.reviewer_id
        for decision in selected_case.decisions
    }

    if reviewer.id in original_decision_reviewer_ids:
        return "An original decision reviewer cannot conduct independent review.", 400

    # Exclude reviewers with declared conflicts.

    conflict = ConflictOfInterest.query.filter_by(
        case_id=selected_case.id,
        reviewer_id=reviewer.id
    ).first()

    if conflict:
        return "A conflicted reviewer cannot conduct independent review.", 400

    independent_review = IndependentReview(
        review_id=f"IRV-{uuid4().hex[:12]}",
        case_id=selected_case.id,
        reviewer_id=reviewer.id,
        outcome=outcome,
        rationale=rationale,
        reviewed_at=datetime.utcnow()
    )

    db.session.add(independent_review)

    old_status = selected_case.status

    if outcome == "Further Review Required":
        selected_case.status = "Further Review Required"
    else:
        selected_case.status = "Independent Review Completed"

    record_event(
        "IndependentReview",
        independent_review.review_id,
        "Independent Review Completed",
        old_status,
        (
            f"Outcome: {outcome}. "
            f"Rationale: {rationale}"
        ),
        reviewer.name
    )

    record_event(
        "Case",
        selected_case.case_id,
        "Case Status Updated",
        old_status,
        selected_case.status,
        reviewer.name
    )

    db.session.commit()

    return redirect(
        url_for(
            "case_details",
            case_id=selected_case.id
        )
    )


# --------------------------------------------------
# INDEPENDENT APPEAL REVIEW
# --------------------------------------------------

@app.route(
    "/appeal/<int:appeal_id>/review",
    methods=["POST"]
)
def review_appeal(appeal_id):

    appeal = Appeal.query.get_or_404(appeal_id)

    reviewer_id = request.form.get(
        "reviewer_id",
        type=int
    )

    outcome = request.form.get(
        "outcome",
        ""
    ).strip()

    reviewer = Reviewer.query.filter_by(
        id=reviewer_id,
        active=True
    ).first()

    if not reviewer:
        return "Invalid or inactive reviewer.", 400

    if appeal.status != "Pending":
        return "This appeal has already been reviewed.", 400

    allowed_outcomes = [
        "Decision Upheld",
        "Decision Overturned",
        "Further Review Required"
    ]

    if outcome not in allowed_outcomes:
        return "Select a valid appeal outcome.", 400

    if appeal.case.reviewer_id == reviewer.id:
        return "The original case reviewer cannot review the appeal.", 400

    if any(
        decision.reviewer_id == reviewer.id
        for decision in appeal.case.decisions
    ):
        return "The original decision reviewer cannot review the appeal.", 400

    conflict = ConflictOfInterest.query.filter_by(
        case_id=appeal.case_id,
        reviewer_id=reviewer.id
    ).first()

    if conflict:
        return "A conflicted reviewer cannot review this appeal.", 400

    appeal.independent_reviewer_id = reviewer.id
    appeal.outcome = outcome
    appeal.status = "Reviewed"
    appeal.reviewed_at = datetime.utcnow()

    record_event(
        "Appeal",
        appeal.appeal_id,
        "Independent Appeal Review",
        "Pending",
        outcome,
        reviewer.name
    )

    db.session.commit()

    return redirect(
        url_for(
            "case_details",
            case_id=appeal.case_id
        )
    )


# --------------------------------------------------
# AUDIT HISTORY
# --------------------------------------------------

@app.route("/audit")
def audit():

    events = AuditEvent.query.order_by(
        AuditEvent.timestamp.desc()
    ).all()

    return render_template(
        "audit.html",
        events=events
    )


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":

    initialize_database()

    app.run(debug=True)