from functools import partial

from fastapi import Depends

from app.controllers import (
    BlacklistSentLogsController,
    CloudDBController,
    CustomerDataController,
    Customers_Blacklist_Controller,
    CustomersAuditController,
    ErrorLogsController,
    EvidenceDataController,
    Incidents_Blacklist_Controller,
    IncidentsAnalystAuditController,
    IncidentsAuditController,
    IncidentsController,
)
from app.models import (
    BlacklistSentLogs,
    Customers,
    Customers_Audit,
    Customers_Blacklist,
    ErrorLogs,
    Evidence,
    Incidents,
    Incidents_Analyst_Audit,
    Incidents_Audit,
    Incidents_Blacklist,
)
from app.repositories import (
    BlacklistSentLogsRepository,
    CustomerDataRepository,
    Customers_Blacklist_Repository,
    CustomersAuditRepository,
    ErrorLogsRepository,
    EvidenceDataRepository,
    Incidents_Blacklist_Repository,
    IncidentsAnalystAuditRepository,
    IncidentsAuditRepository,
    IncidentsRepository,
)
from core.database import get_session
from core.utils.firebase import CloudDBHandler, get_cloudDB_client


class Factory:
    """
    This is the factory container that will instantiate all the controllers and
    repositories which can be accessed by the rest of the application.
    """

    cloudDB_handler = partial(CloudDBHandler)
    blacklist_sent_logs_repository = partial(
        BlacklistSentLogsRepository, BlacklistSentLogs
    )
    incidents_repository = partial(IncidentsRepository, Incidents)
    audit_repository = partial(IncidentsAuditRepository, Incidents_Audit)
    analyst_audit_repository = partial(
        IncidentsAnalystAuditRepository, Incidents_Analyst_Audit
    )
    blacklist_repository = partial(Incidents_Blacklist_Repository, Incidents_Blacklist)
    customer_data_repository = partial(CustomerDataRepository, Customers)
    customer_audit_repository = partial(CustomersAuditRepository, Customers_Audit)
    customer_blacklist_repository = partial(
        Customers_Blacklist_Repository, Customers_Blacklist
    )
    error_logs_repository = partial(ErrorLogsRepository, ErrorLogs)
    evidence_data_repository = partial(EvidenceDataRepository, Evidence)

    def get_cloudDB_controller(self, client=Depends(get_cloudDB_client)):
        return CloudDBController(cloudDB_handler=self.cloudDB_handler(client))

    def get_blacklist_sent_logs_controller(self, db_session=Depends(get_session)):
        return BlacklistSentLogsController(
            blacklist_sent_logs_repository=self.blacklist_sent_logs_repository(
                db_session=db_session
            ),
        )

    def get_incidents_controller(self, db_session=Depends(get_session)):
        return IncidentsController(
            incidents_repository=self.incidents_repository(db_session=db_session),
        )

    def get_audit_controller(self, db_session=Depends(get_session)):
        return IncidentsAuditController(
            audit_repository=self.audit_repository(db_session=db_session),
        )

    def get_analyst_audit_controller(self, db_session=Depends(get_session)):
        return IncidentsAnalystAuditController(
            audit_repository=self.analyst_audit_repository(db_session=db_session),
        )

    def get_blacklist_controller(self, db_session=Depends(get_session)):
        return Incidents_Blacklist_Controller(
            blacklist_repository=self.blacklist_repository(db_session=db_session),
        )

    def get_customer_data_controller(self, db_session=Depends(get_session)):
        return CustomerDataController(
            customer_data_repository=self.customer_data_repository(
                db_session=db_session
            ),
        )

    def get_customer_audit_controller(self, db_session=Depends(get_session)):
        return CustomersAuditController(
            audit_repository=self.customer_audit_repository(db_session=db_session),
        )

    def get_customer_blacklist_controller(self, db_session=Depends(get_session)):
        return Customers_Blacklist_Controller(
            blacklist_repository=self.customer_blacklist_repository(
                db_session=db_session
            ),
        )

    def get_error_logs_controller(self, db_session=Depends(get_session)):
        return ErrorLogsController(
            error_logs_repository=self.error_logs_repository(db_session=db_session),
        )

    def get_evidence_data_controller(self, db_session=Depends(get_session)):
        return EvidenceDataController(
            evidence_data_repository=self.evidence_data_repository(
                db_session=db_session
            )
        )
