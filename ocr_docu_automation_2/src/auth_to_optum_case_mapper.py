from pydantic import BaseModel, Field
from typing import Any, Optional
import logging
from datetime import datetime, date
from dateutil.parser import parse
from os import path

logger = logging.getLogger(__name__)


class PatientDemographics(BaseModel):
    id: str = ""
    # plan_name: str = ""
    # planLob: str = ""
    firstName: str = ""
    # middleName: str = ""
    lastName: str = ""
    dob: date = date.today()  # YYYY-MM-DD
    # zipCode: str = ""
    # gender: str = (
    #     ""  # "Male", "Female", "Transgender", "Non-binary", "Prefer not to respond"
    # )
    # raceEthnicity: str = ""
    # # ethnicity: str = ""
    # primaryLanguage: str = ""
    # disabilityStatus: str = ""
    # additionalIDs: list[str] = []


class GuideLine(BaseModel):
    revision: str = ""
    version: str = ""
    product: str = ""
    subsetCid: str = ""


class Diagnosis(BaseModel):
    code: str = ""
    codingSystem: str = ""


class Service(BaseModel):
    type: str = ""
    code: str = ""
    codingSystem: str = ""  # enum": ["CPT", "HCPCS"],
    diagnosis: Diagnosis = Diagnosis()


class LineItem(BaseModel):
    id: str = ""
    services: list[Service] = []
    guideline: GuideLine = GuideLine()


class Document(BaseModel):
    filePath: str = ""
    # name: str = ""
    # versionNumber: str = "1"
    id: str = ""
    # processAI: bool = True
    # notes: list[str] = []


class OptumCase(BaseModel):
    caseId: str = ""
    caseCreatedTimeStamp: str = datetime.now().strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )  # YYYY-MM-DDTHH:MM:SSZ
    isExpedited: bool = False
    linesOfBusiness: list[str] = []
    member: PatientDemographics = PatientDemographics()
    documents: list[Document] = []
    lineItems: list[LineItem] = []


class OptumFinalCase(BaseModel):
    case: OptumCase = OptumCase()


class AuthToOptumCaseMapper:

    def getDocumentsForAIDecisioning(self, documents: list) -> list:

        return [
            doc
            for doc in documents
            if doc["documentType"]
            in [
                "Additional Clinical Documentation",
                "Additional FBO Clinical Documentation",
                "Additional Rx Clinical Documentation",
                "Incoming Fax",
                "Expedited Request",
                "Possible Duplicate Notification",
            ]
        ]

    def map(self, auth, auth_guideLine: dict[str, str]) -> OptumCase:
        optumCase = OptumCase()

        # map case details
        optumCase.caseId = auth.get("caseNumber")
        optumCase.caseCreatedTimeStamp = parse(auth.get("creationDate")).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )  # is it createdate or recieved date
        optumCase.isExpedited = auth.get("priority", "Standard") != "Standard"
        optumCase.linesOfBusiness.append(
            auth.get("memberEligibility").get("companyLob")
        )

        # self.map_case_details(auth, optumCase)
        # map member info
        member = auth.get("member", None)
        if member:
            self.map_member(auth, optumCase)

            self.map_procedures(auth, optumCase, auth_guideLine)

            self.map_documents(auth, optumCase)
        else:
            Exception("Member Not found")

        return optumCase

    def map_procedures(
        self, auth, optumCase: OptumCase, auth_guideLine: dict[str, str]
    ):

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
            # earliestServiceDate = date.today()
            # if not isAuthSR:
            #     ipServiceDates = [
            #         parse(ipDay.get("effectiveDate")).date()
            #         for ipDay in lastReview.get("ipDays", [])
            #     ]
            #     earliestServiceDate = min(ipServiceDates)
            # else:
            #     serviceDate = [
            #         parse(procedure.get("fromDate")).date() for procedure in procedures
            #     ]
            #     earliestServiceDate = min(serviceDate)

            if procedures:
                lineItem = LineItem()
                lineItem.id = lastReview.get("reviewNumber", "")
                for procedure in procedures:
                    service = Service()
                    service.code = procedure.get("code")
                    service.type = "PROCEDURE"
                    service.codingSystem = (
                        "HCPCS" if "HCPCS" in procedure.get("codeType", "") else "CPT"
                    )

                    diagnosis = lastReview.get("primaryDiagnosis", None)
                    if diagnosis:
                        service.diagnosis.code = diagnosis.get("code", "")
                        service.diagnosis.codingSystem = (
                            "ICD-10"
                            if "ICD10" in diagnosis.get("codeType", "")
                            else "ICD"
                        )

                    # service.serviceSite = lastReview.get("placeOfService")
                    # service.serviceState = serviceState

                    # service.serviceFacility = serviceFacility

                    # service.serviceDate = earliestServiceDate

                    # optumCase.l.append(services)
                    lineItem.services.append(service)

                    lineItem.guideline.product = auth_guideLine.get("product", "")
                    lineItem.guideline.revision = auth_guideLine.get("revision", "")
                    lineItem.guideline.version = auth_guideLine.get("version", "")
                    lineItem.guideline.subsetCid = auth_guideLine.get("subsetCid", "")

                optumCase.lineItems.append(lineItem)

    def map_documents(self, auth, optumCase: OptumCase):
        documents = self.getDocumentsForAIDecisioning(auth.get("documents", []))
        for doc in documents:
            file_name = doc["fileName"]
            _, file_extension = path.splitext(file_name)
            if not file_extension:
                file_name = doc["fileName"] + ".pdf"
            elif file_extension == ".PDF":
                file_name = doc["fileName"].replace("PDF", "pdf")
            elif file_extension == ".docx":
                file_name = doc["fileName"].replace("docx", "doc")

            new_doc = Document(
                filePath=file_name,
                id=doc["documentId"],
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

    def map_member(self, auth, optumCase: OptumCase):
        optumCase.member.id = auth.get("member").get("memberId")

        optumCase.member.firstName = auth.get("member").get("firstName")
        optumCase.member.lastName = auth.get("member").get("lastName")
        optumCase.member.dob = parse(auth.get("member").get("dateOfBirth")).date()

        # optumCase.member.zipCode = (
        #     auth.get("member").get("memberAddresses")[0].get("zip")
        # )
        # optumCase.member.gender = auth.get("member").get("gender")

        # optumCase.member.plan_name = auth.get("memberEligibility").get(
        #     "eligPlan"
        # )
        # optumCase.member.planLob = auth.get("memberEligibility").get(
        #     "companyLob"
        # )

        # optumCase.patientDemographic.race = auth.get(
        #     'member').get('memberId')
        # optumCase.patientDemographic.ethnicity = auth.get(
        #     'member').get('memberId')
        # optumCase.patientDemographic.primaryLanguage = auth.get(
        #     'member').get('memberId')
        # optumCase.patientDemographic.disabilityStatus = auth.get(
        #     'member').get('memberId')
