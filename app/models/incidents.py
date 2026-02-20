from sqlalchemy import (
    ARRAY,
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Interval,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    desc,
    func,
)
from sqlalchemy.orm import relationship

from core.config import config
from core.database.session import Base


class Incidents(Base):
    __tablename__ = "incidents"

    class IncidentType:
        """
        IncidentType indicates the type of incident occured.
        This is given by Data Science Team
        """

        CUSTOMER_THEFT = 0
        PREVIOUSLY_BLACKLISTED = 1
        ESCAPE_THEFT = 2
        THEFT_STOPPED = 3

    class IncidentStatus:
        """
        IncidentStatus indicates the status of the incident.
        This is given by the user inside the app.
        """

        NONE = config.STATUS_NONE
        NO_ACTION = config.NO_ACTION
        ESCAPE_THEFT = config.ESCAPE_THEFT
        THEFT_STOPPED = config.THEFT_STOPPED
        PREVIOUSLY_BLACKLISTED = config.BLACKLISTED

    class PriorityChoices:
        LOW = 1
        MEDIUM = 2
        HIGH = 3

    class AnalystValidationChoices:
        INVALID = 0
        VALID = 1
        DOUBTFUL = 2

    class QAPendingValidationChoices:
        INVALID = 0
        VALID = 1

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    incident_id = Column(String, unique=True, index=True)
    company_id = Column(BigInteger, nullable=False)
    branch_id = Column(BigInteger, nullable=False)
    camera_id = Column(BigInteger)
    name = Column(String, nullable=False)
    incident_type = Column(Integer)
    incident_time = Column(DateTime(timezone=False), nullable=False)
    incident_logged_time = Column(DateTime(timezone=True))
    match_score = Column(Float, nullable=True)
    comments = Column(String, nullable=True)
    photo_url = Column(String(255), nullable=False)
    video_url = Column(String(255), nullable=False)
    share_video_url = Column(String(255), nullable=True)
    thumbnail_url = Column(String(255))
    status = Column(Integer, default=IncidentStatus.NONE)
    is_blacklisted = Column(Boolean, default=False)
    analyst_blacklisted = Column(Boolean, default=None)
    previous_incident_id = Column(BigInteger)
    probable_customer_ids = Column(ARRAY(String))
    customer_id = Column(BigInteger, ForeignKey("customers.id", ondelete="CASCADE"))
    no_of_visits = Column(Integer)
    priority = Column(Integer, default=PriorityChoices.HIGH)
    is_valid = Column(Integer)
    is_test = Column(Boolean, default=False)
    validated_by = Column(Integer)
    # validated_at = Column(DateTime(timezone=True), nullable=True)
    analyst_comments = Column(String)
    analyst_incident_type = Column(Integer)
    resolution_time = Column(Interval, nullable=True)
    # is_qa_assigned = Column(Boolean, default=False)
    # qa_status = Column(Integer, nullable=True)
    # qa_comments = Column(String, nullable=True)
    response = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    created_by = Column(BigInteger)
    updated_at = Column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
    )
    updated_by = Column(BigInteger, nullable=True)

    blacklists = relationship(
        "Incidents_Blacklist", back_populates="incident", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_branch_incident_time", "branch_id", desc("incident_time")),
    )


class Incidents_Audit(Base):
    __tablename__ = "incidents_audit"

    class AuditAction:
        NO_ACTION = config.NO_ACTION
        ESCAPE_THEFT = config.ESCAPE_THEFT
        THEFT_STOPPED = config.THEFT_STOPPED
        BLACKLISTED = config.BLACKLISTED

    class AuditStatus:
        ADDED = 1
        REMOVED = 2
        APPROVED = 3
        DECLINED = 4

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    incident_id = Column(
        BigInteger,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type = Column(Integer)
    status = Column(Integer, nullable=False)
    comments = Column(String)
    created_at = Column(DateTime(timezone=True), default=func.now())
    created_by = Column(BigInteger)
    updated_at = Column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
    )
    updated_by = Column(BigInteger, nullable=True)
    edited = Column(Boolean, default=False)


class Incidents_Analyst_Audit(Base):
    __tablename__ = "incident_analyst_audit_logs"

    class AnalystAuditAction:
        BLACKLISTED = 4
        VALID = 5
        INVALID = 6
        DOUBT = 7
        CUSTOMER = 8

    class AnalystAuditStatus:
        ADDED = 1
        REMOVED = 2
        APPROVED = 3
        DECLINED = 4

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    incident_id = Column(
        BigInteger,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type = Column(Integer)
    status = Column(Integer, nullable=False)
    comments = Column(String)
    created_at = Column(DateTime(timezone=True), default=func.now())
    created_by = Column(BigInteger)
    updated_at = Column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
    )
    updated_by = Column(BigInteger, nullable=True)
    edited = Column(Boolean, default=False)


class Incidents_Blacklist(Base):
    __tablename__ = "blacklists"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    incident_id = Column(
        BigInteger,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), default=func.now())
    related_incident_id = Column(BigInteger, nullable=True)

    incident = relationship("Incidents", back_populates="blacklists", lazy="selectin")


class Customers(Base):
    __tablename__ = "customers"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    customer_id = Column(String, nullable=False, unique=True, index=True)
    company_id = Column(BigInteger, nullable=False)
    branch_id = Column(BigInteger, nullable=False)
    camera_id = Column(BigInteger, nullable=False)
    descriptor_1 = Column(String)
    descriptor_2 = Column(String)
    pic_url = Column(String)
    no_of_visits = Column(Integer)
    is_test = Column(Boolean, default=False)
    analyst_blacklisted = Column(Boolean, default=False)
    app_blacklisted = Column(Boolean, default=False)
    visited_time = Column(DateTime(timezone=False))
    created_at = Column(DateTime(timezone=True), default=func.now())


class Customers_Audit(Base):
    __tablename__ = "customer_audit"

    class AuditAction:
        BLACKLISTED = config.BLACKLISTED

    class AuditStatus:
        ADDED = 1
        REMOVED = 2

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    customer_id = Column(
        BigInteger, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    action_type = Column(Integer)
    status = Column(Integer, nullable=False)
    comments = Column(String)
    created_at = Column(DateTime(timezone=True), default=func.now())
    created_by = Column(BigInteger)
    updated_at = Column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
    )
    updated_by = Column(BigInteger, nullable=True)
    edited = Column(Boolean, default=False)


class Customers_Blacklist(Base):
    __tablename__ = "customer_blacklists"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    customer_id = Column(
        BigInteger, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), default=func.now())


class BlacklistSentLogs(Base):
    __tablename__ = "blacklist_sent_logs"

    class ActionTypes:
        REMOVE = 0
        ADD = 1

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    action_type = Column(SmallInteger, nullable=False)
    company_id = Column(BigInteger, nullable=False)
    branch_id = Column(BigInteger, nullable=False)
    incident_id = Column(
        BigInteger,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=True,
    )
    customer_id = Column(
        BigInteger, ForeignKey("customers.id", ondelete="CASCADE"), nullable=True
    )

    # can be either customer_blacklists id or blacklists id
    blacklist_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)


class ErrorLogs(Base):
    __tablename__ = "error_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    incident_id = Column(String)
    error_msg = Column(String)
    created_at = Column(DateTime(timezone=True), default=func.now())


class TestWatchlistedCustomers(Base):
    __tablename__ = "test_watchlisted_customers"
    __table_args__ = (
        UniqueConstraint("customer_id", "user_id", name="uq_user_customer"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    customer_id = Column(
        BigInteger, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())


class IncidentValidationMetrics(Base):
    __tablename__ = "incident_analyst_review_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    incident_id = Column(
        BigInteger, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(BigInteger, nullable=False)
    is_validated = Column(Boolean, nullable=False, default=False)
    opened_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    time_difference = Column(Interval, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now()
    )


class Evidence(Base):
    __tablename__ = "evidences"

    class EvidenceType:
        NON_THEFT = 0
        THEFT = 1
        SYSTEM_TEST = 2

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    incident_id = Column(
        BigInteger, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    evidence_type = Column(Integer, nullable=False)
    property_details = Column(JSON, nullable=True)
    evidence_description = Column(String, nullable=True)
    share_email_id = Column(String(255))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    created_by = Column(BigInteger)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now()
    )
    updated_by = Column(BigInteger, nullable=True)
