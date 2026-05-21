from pydantic import BaseModel, Field
from typing import Any, Optional
import logging
from datetime import datetime, date
from dateutil.parser import parse

logger = logging.getLogger(__name__)


class CaseDetails(BaseModel):
    caseId: str = ""
    caseVersion: int = 0
    urgentCase: bool = False
    aiAssist: bool = True
    caseOffshoreRestricted: bool = False  # get details
    startTimestamp: datetime = datetime.now()


class PatientDemographics(BaseModel):
    memberID: str = ""
    plan_name: str = ""
    planLob: str = ""
    firstName: str = ""
    lastName: str = ""
    dob: date = date.today()
    zipCode: str = ""
    gender: str = ""
    race: str = ""
    ethnicity: str = ""
    primaryLanguage: str = ""
    disabilityStatus: str = ""


class Procedure(BaseModel):
    code: str = ""
    valueSet: str = ""
    subsetIds: list[str] = []
    serviceSite: str = ""
    serviceState: str = ""
    serviceDate: date = date.today()
    serviceFacility: str = ""


class Document(BaseModel):
    fileName: str = ""
    name: str = ""
    version: str = "1"
    documentId: str = Field(exclude=True, default="")


class OptumCase(BaseModel):
    caseDetails: CaseDetails = CaseDetails()
    patientDemographic: PatientDemographics = PatientDemographics()
    procedures: list[Procedure] = []
    documents: list[Document] = []


class AuthToOptumCaseMapper:

    def getDocumentsForAIDecisioning(self, documents: list) -> list:

        return [
            doc
            for doc in documents
            if doc["documentType"]
            in [
                "Additional Clinical Documentation",
                "Additional FBO CLinical Documentation",
                "Additional Rx Clinical Documentation",
                "Incoming Fax",
                "Expedited Request",
            ]
        ]

    def map(self, auth) -> OptumCase:
        optumCase = OptumCase()
        # map case details
        self.map_case_details(auth, optumCase)
        # map member info
        member = auth.get("member", None)
        if member:
            self.map_member(auth, optumCase)

            self.map_procedures(auth, optumCase)

            self.map_documents(auth, optumCase)
        else:
            Exception("Member Not found")

        return optumCase

    def map_procedures(self, auth, optumCase):

        serviceFacilityProvider = (
            auth.get("facilityProvider", None)
            if "facilityProvider" in auth
            else auth.get("servicingProvider", None)
        )
        # facility for both, if no then use servicing

        serviceState = (
            serviceFacilityProvider.get("state") if serviceFacilityProvider else ""
        )
        serviceFacility = (
            serviceFacilityProvider.get("fullName") if serviceFacilityProvider else ""
        )
        lastReview = auth.get("lastReview", None)

        if lastReview:
            procedures = lastReview.get("procedures", [])

            isAuthSR: bool = (
                auth.get("requestType", "service request").lower() == "service request"
            )
            earliestServiceDate = date.today()
            if not isAuthSR:
                ipServiceDates = [
                    parse(ipDay.get("effectiveDate")).date()
                    for ipDay in lastReview.get("ipDays", [])
                ]
                earliestServiceDate = min(ipServiceDates)
            else:
                serviceDate = [
                    parse(procedure.get("fromDate")).date() for procedure in procedures
                ]
                earliestServiceDate = min(serviceDate)

            if procedures:
                for procedure in procedures:
                    optumProcedure = Procedure()
                    optumProcedure.code = procedure.get("code")
                    optumProcedure.valueSet = procedure.get("codeType")
                    optumProcedure.subsetIds = []  # no need
                    optumProcedure.serviceSite = lastReview.get("placeOfService")
                    optumProcedure.serviceState = serviceState

                    optumProcedure.serviceFacility = serviceFacility

                    optumProcedure.serviceDate = earliestServiceDate

                    optumCase.procedures.append(optumProcedure)

    def map_documents(self, auth, optumCase):
        documents = self.getDocumentsForAIDecisioning(auth.get("documents", []))
        for doc in documents:
            new_doc = Document(
                fileName=doc["fileName"],
                name=doc["fileName"],
                version="1",
                documentId=doc["documentId"],
            )
            optumCase.documents.append(new_doc)

    def map_case_details(self, auth, optumCase):
        optumCase.caseDetails.caseId = auth.get("caseNumber")
        optumCase.caseDetails.startTimestamp = parse(
            auth.get("creationDate")
        )  # is it createdate or recieved date
        optumCase.caseDetails.urgentCase = (
            auth.get("priority", "Standard") != "Standard"
        )

    def map_member(self, auth, optumCase):
        optumCase.patientDemographic.memberID = auth.get("member").get("memberId")

        optumCase.patientDemographic.firstName = auth.get("member").get("firstName")
        optumCase.patientDemographic.lastName = auth.get("member").get("lastName")
        optumCase.patientDemographic.dob = parse(
            auth.get("member").get("dateOfBirth")
        ).date()
        optumCase.patientDemographic.zipCode = (
            auth.get("member").get("memberAddresses")[0].get("zip")
        )
        optumCase.patientDemographic.gender = auth.get("member").get("gender")

        optumCase.patientDemographic.plan_name = auth.get("memberEligibility").get(
            "eligPlan"
        )
        optumCase.patientDemographic.planLob = auth.get("memberEligibility").get(
            "companyLob"
        )

        # optumCase.patientDemographic.race = auth.get(
        #     'member').get('memberId')
        # optumCase.patientDemographic.ethnicity = auth.get(
        #     'member').get('memberId')
        # optumCase.patientDemographic.primaryLanguage = auth.get(
        #     'member').get('memberId')
        # optumCase.patientDemographic.disabilityStatus = auth.get(
        #     'member').get('memberId')
