
from datetime import datetime
from database import db


# --------------------------------------------------
# LEARNER
# --------------------------------------------------

class Learner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    learner_id = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    department = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    submissions = db.relationship("Submission", back_populates="learner")


# --------------------------------------------------
# ASSESSMENT
# --------------------------------------------------

class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.String(30), unique=True, nullable=False)
    title = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(100))
    due_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    submissions = db.relationship("Submission", back_populates="assessment")


# --------------------------------------------------
# SUBMISSION
# --------------------------------------------------

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.String(40), unique=True, nullable=False)

    learner_id = db.Column(db.Integer, db.ForeignKey("learner.id"), nullable=False)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessment.id"), nullable=False)

    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    content_reference = db.Column(db.String(255))
    status = db.Column(db.String(30), default="Submitted")

    learner = db.relationship("Learner", back_populates="submissions")
    assessment = db.relationship("Assessment", back_populates="submissions")

    similarity_reports = db.relationship(
        "SimilarityReport", back_populates="submission"
    )


# --------------------------------------------------
# INTEGRITY RULE
# --------------------------------------------------

class IntegrityRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.String(30), unique=True, nullable=False)
    rule_name = db.Column(db.String(100), nullable=False)
    review_threshold = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    effective_from = db.Column(db.DateTime, default=datetime.utcnow)
    effective_to = db.Column(db.DateTime)
    active = db.Column(db.Boolean, default=True)


# --------------------------------------------------
# SIMILARITY REPORT
# --------------------------------------------------

class SimilarityReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    similarity_id = db.Column(db.String(100), unique=True, nullable=False)

    submission_id = db.Column(
        db.Integer, db.ForeignKey("submission.id"), nullable=False
    )

    similarity_score = db.Column(db.Float, nullable=False)
    matched_sources = db.Column(db.Integer, default=0)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    review_required = db.Column(db.Boolean, default=False)

    submission = db.relationship(
        "Submission", back_populates="similarity_reports"
    )

    cases = db.relationship("Case", back_populates="similarity_report")


# --------------------------------------------------
# REVIEWER
# --------------------------------------------------

class Reviewer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reviewer_id = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    role = db.Column(db.String(50), default="Instructor")
    active = db.Column(db.Boolean, default=True)

    cases = db.relationship("Case", back_populates="reviewer")
    decisions = db.relationship("Decision", back_populates="reviewer")

    appeals = db.relationship(
        "Appeal",
        foreign_keys="Appeal.independent_reviewer_id",
        back_populates="independent_reviewer"
    )

    conflict_declarations = db.relationship(
        "ConflictOfInterest",
        back_populates="reviewer",
        foreign_keys="ConflictOfInterest.reviewer_id"
    )

    independent_reviews = db.relationship(
        "IndependentReview",
        back_populates="reviewer",
        foreign_keys="IndependentReview.reviewer_id"
    )


# --------------------------------------------------
# CASE
# --------------------------------------------------

class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.String(30), unique=True, nullable=False)

    submission_id = db.Column(
        db.Integer, db.ForeignKey("submission.id"), nullable=False
    )

    similarity_report_id = db.Column(
        db.Integer, db.ForeignKey("similarity_report.id"), nullable=False
    )

    reviewer_id = db.Column(
        db.Integer, db.ForeignKey("reviewer.id"), nullable=True
    )

    status = db.Column(db.String(50), default="Open")
    issue_type = db.Column(db.String(60))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime)

    submission = db.relationship("Submission")

    similarity_report = db.relationship(
        "SimilarityReport", back_populates="cases"
    )

    reviewer = db.relationship("Reviewer", back_populates="cases")

    evidence_items = db.relationship(
        "EvidenceItem", back_populates="case"
    )

    decisions = db.relationship("Decision", back_populates="case")
    appeals = db.relationship("Appeal", back_populates="case")

    conflict_declarations = db.relationship(
        "ConflictOfInterest", back_populates="case"
    )

    independent_reviews = db.relationship(
        "IndependentReview",
        back_populates="case",
        order_by="IndependentReview.reviewed_at"
    )


# --------------------------------------------------
# EVIDENCE
# --------------------------------------------------

class EvidenceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    evidence_id = db.Column(db.String(40), unique=True, nullable=False)

    case_id = db.Column(
        db.Integer, db.ForeignKey("case.id"), nullable=False
    )

    evidence_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    reference = db.Column(db.String(255))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    added_by = db.Column(db.String(100))

    case = db.relationship("Case", back_populates="evidence_items")


# --------------------------------------------------
# DECISION
# --------------------------------------------------

class Decision(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    decision_id = db.Column(db.String(40), unique=True, nullable=False)

    case_id = db.Column(
        db.Integer, db.ForeignKey("case.id"), nullable=False
    )

    reviewer_id = db.Column(
        db.Integer, db.ForeignKey("reviewer.id"), nullable=False
    )

    outcome = db.Column(db.String(50), nullable=False)
    rationale = db.Column(db.Text, nullable=False)
    decided_at = db.Column(db.DateTime, default=datetime.utcnow)

    case = db.relationship("Case", back_populates="decisions")
    reviewer = db.relationship("Reviewer", back_populates="decisions")


# --------------------------------------------------
# APPEAL
# --------------------------------------------------

class Appeal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appeal_id = db.Column(db.String(40), unique=True, nullable=False)

    case_id = db.Column(
        db.Integer, db.ForeignKey("case.id"), nullable=False
    )

    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(40), default="Pending")

    independent_reviewer_id = db.Column(
        db.Integer, db.ForeignKey("reviewer.id"), nullable=True
    )

    outcome = db.Column(db.String(50))
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)

    case = db.relationship("Case", back_populates="appeals")

    independent_reviewer = db.relationship(
        "Reviewer",
        foreign_keys=[independent_reviewer_id],
        back_populates="appeals"
    )


# --------------------------------------------------
# CONFLICT OF INTEREST
# --------------------------------------------------

class ConflictOfInterest(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    case_id = db.Column(
        db.Integer, db.ForeignKey("case.id"), nullable=False
    )

    reviewer_id = db.Column(
        db.Integer, db.ForeignKey("reviewer.id"), nullable=False
    )

    reason = db.Column(db.Text, nullable=False)
    declared_by = db.Column(db.String(100), nullable=False)
    declared_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            "case_id",
            "reviewer_id",
            name="unique_case_reviewer_conflict"
        ),
    )

    case = db.relationship(
        "Case", back_populates="conflict_declarations"
    )

    reviewer = db.relationship(
        "Reviewer",
        back_populates="conflict_declarations",
        foreign_keys=[reviewer_id]
    )


# --------------------------------------------------
# INDEPENDENT REVIEW
# --------------------------------------------------

class IndependentReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    review_id = db.Column(
        db.String(50), unique=True, nullable=False
    )

    case_id = db.Column(
        db.Integer,
        db.ForeignKey("case.id"),
        nullable=False,
        unique=True
    )

    reviewer_id = db.Column(
        db.Integer,
        db.ForeignKey("reviewer.id"),
        nullable=False
    )

    outcome = db.Column(
        db.String(60), nullable=False
    )

    rationale = db.Column(
        db.Text, nullable=False
    )

    reviewed_at = db.Column(
        db.DateTime, default=datetime.utcnow
    )

    case = db.relationship(
        "Case", back_populates="independent_reviews"
    )

    reviewer = db.relationship(
        "Reviewer",
        back_populates="independent_reviews",
        foreign_keys=[reviewer_id]
    )


# --------------------------------------------------
# AUDIT EVENT
# --------------------------------------------------

class AuditEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(40), unique=True, nullable=False)

    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(100), nullable=False)

    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    performed_by = db.Column(db.String(100))

    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


    


    


    