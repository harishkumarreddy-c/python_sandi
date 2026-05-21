# OCR Docu Automation Code Walkthrough

This document explains every line of code found in the `ocr_docu_automation_2` project folder, with a focus on the actual OCR/document automation source files under `src/`.

## 1. `main.py` (root)

```python
def main():
    print("Hello from ocr-docu-automation!")


if __name__ == "__main__":
    main()
```

- `def main():`: Defines the main function for the root-level script.
- `print("Hello from ocr-docu-automation!")`: Prints a simple greeting to stdout when the script is run.
- `if __name__ == "__main__":`: Ensures the script runs only when executed directly, not when imported.
- `main()`: Calls the root `main` function.

## 2. `src/main.py`

This file is the orchestration script for reading request and guideline data, loading configuration, fetching authenticated case details, mapping them to Optum case format, and writing output ZIP archives.

```python
import argparse
import asyncio
import csv
from typing import Any

from anyio import Path

from auth_request import AuthRequester
from dotenv import load_dotenv
from os import mkdir, path, makedirs
import logging
import datetime
import zipfile
from os import path

from csv import DictReader
import csv

from auth_to_optum_case_mapper import AuthToOptumCaseMapper, OptumCase, OptumFinalCase
```

- `import argparse`: Imports the command-line argument parser.
- `import asyncio`: Imports async runtime support.
- `import csv`: Imports CSV utilities.
- `from typing import Any`: Imports the `Any` type annotation.
- `from anyio import Path`: Uses `Path` for cross-platform path handling.
- `from auth_request import AuthRequester`: Imports the HTTP auth requester helper.
- `from dotenv import load_dotenv`: Imports dotenv loader for environment files.
- `from os import mkdir, path, makedirs`: Imports OS path functions and directory creation helpers.
- `import logging`: Imports logging support.
- `import datetime`: Imports date/time utilities.
- `import zipfile`: Imports ZIP writing utilities.
- `from os import path`: Re-imports `path` to ensure path utilities are available.
- `from csv import DictReader`: Imports CSV dictionary reader.
- `import csv`: Duplicate import of CSV; this is redundant and can be removed.
- `from auth_to_optum_case_mapper import AuthToOptumCaseMapper, OptumCase, OptumFinalCase`: Imports mapper and data models for Optum output.

```python
logger = logging.getLogger(__name__)  # type: ignore
CURRENT_DIR = path.dirname(path.abspath(__file__))
ROOT_DIR = Path(CURRENT_DIR).parent
```

- `logger = logging.getLogger(__name__)`: Creates a module-level logger.
- `CURRENT_DIR = path.dirname(path.abspath(__file__))`: Resolves the absolute directory path of this file.
- `ROOT_DIR = Path(CURRENT_DIR).parent`: Sets the project root directory one level above `src/`.

```python
async def main(environment: str):
    logger.info(f"Current Environment is {environment}")

    load_config(environment)
    mhkRequests: list[dict[str, str]] = load_requests(environment)

    guideLines = load_guidelines(environment)

    logger.info(f"Total # of cases : {len(mhkRequests)}")

    if not mhkRequests:
        logger.info("No request found to extract")
        exit()

    output_dir = ROOT_DIR.joinpath(
        "output",
        "optum_cases-" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
```

- `async def main(environment: str):`: Defines the async main workflow accepting an environment name.
- `logger.info(...)`: Logs the selected environment.
- `load_config(environment)`: Loads environment variables from the appropriate `.env` file.
- `mhkRequests = load_requests(environment)`: Reads the case request CSV.
- `guideLines = load_guidelines(environment)`: Reads the guideline CSV.
- `logger.info(f"Total # of cases : {len(mhkRequests)}")`: Logs how many requests were loaded.
- `if not mhkRequests:`: If no requests were found, log and exit.
- `output_dir = ROOT_DIR.joinpath(...)`: Builds the output directory path using a timestamp.

```python
    for request in mhkRequests:

        async with AuthRequester() as requestor:

            makedirs(output_dir, exist_ok=True)

            requestId = request.get("auth")
            subset = request.get("subset")

            if not requestId or not subset:
                logger.error("Failed to fetch subset or request ")
                continue

            logger.info(f"Processing requestid : {requestId}")

            guideLine = fetch_request_guideline(guideLines, subset)

            if not guideLine:
                logger.error("Failed to fetch guideline for request {requestId}")
                continue

            guideLineName = guideLine.get("Guideline Name", "")

            logger.info(f"Selected Guideline : {guideLineName}")
            mhkRequest = await requestor.getAuthDetails(requestId)
            if mhkRequest:
                try:
                    optumCase = AuthToOptumCaseMapper().map(mhkRequest, guideLine)

                    await create_case_zip(requestId, requestor, output_dir, optumCase)

                except Exception as e:
                    logger.exception(
                        f"Failed to process request {requestId}", exc_info=e
                    )
            logger.info(f"Finished processing requestid : {requestId}")
```

- `for request in mhkRequests:`: Iterates each row in the request CSV.
- `async with AuthRequester() as requestor:`: Opens the authenticated HTTP client context.
- `makedirs(output_dir, exist_ok=True)`: Ensures the output directory exists.
- `requestId = request.get("auth")`: Reads the auth request identifier.
- `subset = request.get("subset")`: Reads the guideline subset identifier.
- `if not requestId or not subset:`: Validates required CSV fields.
- `logger.error(...)`: Logs missing request or subset data.
- `guideLine = fetch_request_guideline(guideLines, subset)`: Finds the matching guideline row.
- `if not guideLine:`: Logs failure if no guideline row matches.
- `mhkRequest = await requestor.getAuthDetails(requestId)`: Fetches authenticated case details from the API.
- `optumCase = AuthToOptumCaseMapper().map(mhkRequest, guideLine)`: Converts the API response into Optum case format.
- `await create_case_zip(...)`: Writes output ZIP with JSON and attachments.
- `logger.exception(...)`: Logs exceptions during processing.
- `logger.info(...)`: Marks request completion.

```python
def fetch_request_guideline(guideLines, subset):
    guideLine: dict[str, str] | Any = None
    for guide in guideLines:
        if guide.get("Guideline Name", "").lower().strip() == subset.lower().strip():
            guideLine = guide
    return guideLine
```

- `fetch_request_guideline(...)`: Finds the guideline row whose `Guideline Name` matches the subset value.
- `guide.get("Guideline Name", "")`: Reads the guideline name field safely.
- `.lower().strip()`: Normalizes text before comparison.
- `return guideLine`: Returns the matched row or `None`.

```python
def load_guidelines(environment: str):
    guidelineFile = ROOT_DIR.joinpath(
        "input", f"{environment.lower()}", "Optum_Guidelines.csv"
    )
    with open(guidelineFile, encoding="utf-8-sig", newline="") as guidelineText:
        reader = DictReader(guidelineText)
        return [line for line in reader]
```

- `load_guidelines(...)`: Loads guideline data from `input/{env}/Optum_Guidelines.csv`.
- `Path.joinpath(...)`: Builds the path to the CSV file.
- `encoding="utf-8-sig"`: Handles BOM if present.
- `DictReader(guidelineText)`: Parses rows into dictionaries keyed by column name.
- `return [line for line in reader]`: Returns a list of guideline dictionaries.

```python
async def create_case_zip(
    requestId: str, requestor: AuthRequester, output_dir: Path, optumCase: OptumCase
) -> bool:
    logger.info(f"Creating Extracts for requestid : {requestId}")
    final_optum_case = OptumFinalCase(case=optumCase)
    with zipfile.ZipFile(
        output_dir.joinpath(requestId + ".zip"),
        "w",
        zipfile.ZIP_DEFLATED,
    ) as zipped_request:
        zipped_request.writestr("case.json", final_optum_case.model_dump_json(indent=4))

        for doc in optumCase.documents:
            document = await requestor.getAuthAttachment(doc.id)
            if document:
                zipped_request.writestr(doc.filePath, document)
    logger.info(f"Finished Creating Extracts for requestid : {requestId}")
    return True
```

- `create_case_zip(...)`: Writes the Optum case output and binary attachments into a ZIP file.
- `OptumFinalCase(case=optumCase)`: Wraps the case data in the final model.
- `zipfile.ZipFile(...) as zipped_request`: Creates the ZIP output file.
- `zipped_request.writestr("case.json", ...)`: Writes the case JSON inside the archive.
- `for doc in optumCase.documents:`: Iterates document attachments to download.
- `document = await requestor.getAuthAttachment(doc.id)`: Downloads attachment bytes.
- `zipped_request.writestr(doc.filePath, document)`: Stores each attachment under its file path inside the ZIP.
- `return True`: Returns success indicator.

```python
def load_config(environment: str):
    env_file = ROOT_DIR.joinpath("config", f".env.{environment.lower()}")

    load_dotenv(dotenv_path=env_file)
```

- `load_config(...)`: Loads environment variables from the environment-specific `.env` file.
- `ROOT_DIR.joinpath("config", f".env.{environment.lower()}")`: Builds the config file path.
- `load_dotenv(...)`: Loads values into `os.environ`.

```python
def load_requests(environment: str) -> list[dict[str, str]]:

    requestFile = ROOT_DIR.joinpath(
        "input", f"{environment.lower()}", "case_guidelines.csv"
    )
    with open(requestFile, encoding="utf-8-sig", newline="") as requestText:
        # fieldnames = ['first_name', 'last_name']
        reader = DictReader(requestText)
        return [line for line in reader]
```

- `load_requests(...)`: Reads the request CSV from `input/{env}/case_guidelines.csv`.
- `DictReader(requestText)`: Reads rows as dictionaries.
- `return [line for line in reader]`: Returns the list of request dictionaries.

```python
if __name__ == "__main__":

    logging.basicConfig(
        filename=f"logs/Ocr_doc_{datetime.datetime.now()}.log", level=logging.INFO
    )
    logger.info("Starting Process to extract case details")

    parser = argparse.ArgumentParser(description="Optum Case Extractor")
    parser.add_argument(
        "-env", type=str, default="dev", help="Application Environment."
    )
    args = vars(parser.parse_args())
    try:
        asyncio.run(main(args["env"]))
    except Exception as ex:
        logger.exception("Process failed", exc_info=ex)

    finally:
        logger.info("Ending Process to extract case details")
```

- `logging.basicConfig(...)`: Configures logging to write to a timestamped log file.
- `argparse.ArgumentParser(...)`: Creates the CLI parser.
- `parser.add_argument("-env" ...)`: Adds the environment argument.
- `args = vars(parser.parse_args())`: Parses CLI args into a dict.
- `asyncio.run(main(args["env"]))`: Runs the async main workflow.
- `logger.exception(...)`: Logs any top-level exceptions.
- `finally: logger.info(...)`: Logs completion.

## 3. `src/auth_request.py`

This module contains the authenticated HTTP client used to request case details and attachments from the backend API.

```python
from venv import logger
from httpx import AsyncClient, codes
import os
import typing
```

- `from venv import logger`: Imports the logger from the virtual environment package, which is likely incorrect and should be replaced with `import logging`.
- `from httpx import AsyncClient, codes`: Imports the async HTTP client and status code constants.
- `import os`: Imports environment variable access.
- `import typing`: Imports typing utilities.

```python
class AuthRequester:

    def __init__(self):
        pass
```

- `class AuthRequester:`: Defines the class that manages authenticated API calls.
- `def __init__(self): pass`: No initialization logic.

```python
    async def __aenter__(self):
        self.__client = AsyncClient(
            headers={
                "MEDHOKUSER": os.environ.get("MEDHOKUSER", ""),
                "PWD": os.environ.get("MHK_PASS", ""),
            },
            base_url=os.environ.get("MHK_ROOT_URL", ""),
        )
        await self.__client.__aenter__()
        return self
```

- `async def __aenter__(self):`: Defines the async context manager entry.
- `self.__client = AsyncClient(...)`: Creates the HTTP client with default auth headers from environment variables.
- `await self.__client.__aenter__()`: Enters the client's async context.
- `return self`: Returns the requester instance.

```python
    async def __aexit__(self, *_):
        try:
            if not self.__client.is_closed:
                await self.__client.aclose()
        except:
            pass
```

- `async def __aexit__(self, *_):`: Defines cleanup logic when exiting the context.
- `if not self.__client.is_closed:`: Checks client state.
- `await self.__client.aclose()`: Closes the HTTP client.
- `except: pass`: Silently ignores close errors.

```python
    async def getAuthDetails(self, authId: str) -> typing.Any:
        url: str = "AuthRestServices/getPreAuth"
        try:
            response = await self.__client.get(url, params={"caseNumber": authId})
            if response.status_code == codes.OK:
                return response.json()
            else:
                response.raise_for_status()
        except Exception as e:
            logger.exception(
                f"Failed to get case details for case {authId}", exc_info=e
            )
            return None
```

- `getAuthDetails(...)`: Fetches case details by case number.
- `response = await self.__client.get(...)`: Calls the API endpoint.
- `if response.status_code == codes.OK:`: Returns JSON only for HTTP 200.
- `response.raise_for_status()`: Raises an exception for non-200 responses.
- `logger.exception(...)`: Logs failures and returns `None`.

```python
    async def getAuthAttachment(self, documentId) -> typing.Optional[bytes]:

        url: str = "DocumentRestServices/getDocument"
        try:
            response = await self.__client.get(
                url,
                headers={
                    "MEDHOKUSER": os.environ.get("MEDHOKUSER", ""),
                    "PWD": os.environ.get("MHK_PASS", ""),
                },
                params={"documentId": documentId},
            )
            return response.content
        except Exception as e:
            logger.exception(f"Failed to download file {documentId}", exc_info=e)
            return None
```

- `getAuthAttachment(...)`: Retrieves binary document content from the API.
- `headers={...}`: Re-supplies the same auth headers for the attachment request.
- `return response.content`: Returns raw bytes even if the HTTP status is not checked.
- `logger.exception(...)`: Logs failures and returns `None`.

## 4. `src/auth_to_optum_case_mapper.py`

This module defines the Optum case data models and maps the authenticated API response into the Optum case format used for output.

```python
from pydantic import BaseModel, Field
from typing import Any, Optional
import logging
from datetime import datetime, date
from dateutil.parser import parse
from os import path

logger = logging.getLogger(__name__)
```

- `BaseModel, Field`: Pydantic classes for model validation and serialization.
- `Any, Optional`: Type hints.
- `parse`: Date parser for input strings.
- `logger = logging.getLogger(__name__)`: Creates a module logger.

### Data models

- `PatientDemographics`: Stores patient/member fields, including `dob` with a default of today.
- `GuideLine`: Stores guideline metadata used for procedures.
- `Diagnosis`: Stores diagnosis code and coding system.
- `Service`: Describes a medical service line item.
- `LineItem`: Contains services and the associated guideline.
- `Document`: Represents a document attachment by path and ID.
- `OptumCase`: Root case model including case metadata, member, documents, and line items.
- `OptumFinalCase`: Wrapper that nests `OptumCase` under a `case` field.

```python
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
```

- `getDocumentsForAIDecisioning(...)`: Filters documents to only those relevant for AI decisioning.
- `if doc["documentType"] in [...]`: Matches a specific set of document types.

```python
    def map(self, auth, auth_guideLine: dict[str, str]) -> OptumCase:
        optumCase = OptumCase()

        # map case details
        optumCase.caseId = auth.get("caseNumber")
        optumCase.caseCreatedTimeStamp = parse(auth.get("creationDate")).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        optumCase.isExpedited = auth.get("priority", "Standard") != "Standard"
        optumCase.linesOfBusiness.append(
            auth.get("memberEligibility").get("companyLob")
        )

        member = auth.get("member", None)
        if member:
            self.map_member(auth, optumCase)

            self.map_procedures(auth, optumCase, auth_guideLine)

            self.map_documents(auth, optumCase)
        else:
            Exception("Member Not found")

        return optumCase
```

- `map(...)`: Converts the raw API response into an `OptumCase`.
- `optumCase.caseId = auth.get("caseNumber")`: Copies the case number.
- `optumCase.caseCreatedTimeStamp = ...`: Formats creation date to ISO UTC string.
- `optumCase.isExpedited`: Sets expedited status based on priority.
- `optumCase.linesOfBusiness.append(...)`: Adds the business line.
- `member = auth.get("member", None)`: Checks for member information.
- `self.map_member(...)`: Maps patient demographics.
- `self.map_procedures(...)`: Converts procedures into line items.
- `self.map_documents(...)`: Converts documents into attachment records.

```python
    def map_procedures(
        self, auth, optumCase: OptumCase, auth_guideLine: dict[str, str]
    ):

        serviceFacilityProvider = (
            auth.get("facilityProvider", None)
            if "facilityProvider" in auth
            else auth.get("servicingProvider", None)
        )

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

                    lineItem.services.append(service)

                    lineItem.guideline.product = auth_guideLine.get("product", "")
                    lineItem.guideline.revision = auth_guideLine.get("revision", "")
                    lineItem.guideline.version = auth_guideLine.get("version", "")
                    lineItem.guideline.subsetCid = auth_guideLine.get("subsetCid", "")

                optumCase.lineItems.append(lineItem)
```

- `serviceFacilityProvider`: Chooses facility provider if available, otherwise servicing provider.
- `serviceState` and `serviceFacility`: Extracts state and facility details.
- `lastReview = auth.get("lastReview", None)`: Gets the review object.
- `procedures = lastReview.get("procedures", [])`: Reads procedure list.
- `isAuthSR`: Detects whether the request type is a service request.
- `lineItem = LineItem()`: Creates a new line item.
- `service.code`: Copies procedure code.
- `service.type = "PROCEDURE"`: Hard-codes service type.
- `service.codingSystem`: Sets HCPCS or CPT based on the code type.
- `diagnosis`: Adds primary diagnosis code if present.
- `lineItem.guideline.*`: Applies guideline metadata to the line item.
- `optumCase.lineItems.append(lineItem)`: Adds the mapped line item.

```python
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
```

- `file_name = doc["fileName"]`: Reads the attachment name.
- `path.splitext(...)`: Splits the extension.
- `if not file_extension:`: Appends `.pdf` when none exists.
- `elif file_extension == ".PDF":`: Normalizes uppercase PDF extension.
- `elif file_extension == ".docx":`: Normalizes DOCX to `.doc`.
- `Document(filePath=file_name, id=...)`: Creates the document record.
- `optumCase.documents.append(new_doc)`: Adds it to the case.

```python
    def map_case_details(self, auth, optumCase: OptumCase):
        optumCase.caseDetails.caseId = auth.get("caseNumber")
        optumCase.caseDetails.startTimestamp = parse(
            auth.get("creationDate")
        )
        optumCase.caseDetails.urgentCase = (
            auth.get("priority", "Standard") != "Standard"
        )
```

- `map_case_details(...)`: Maps legacy case metadata, but this method is not used in the current `map` flow.

```python
    def map_member(self, auth, optumCase: OptumCase):
        optumCase.member.id = auth.get("member").get("memberId")

        optumCase.member.firstName = auth.get("member").get("firstName")
        optumCase.member.lastName = auth.get("member").get("lastName")
        optumCase.member.dob = parse(auth.get("member").get("dateOfBirth")).date()
```

- `map_member(...)`: Copies member ID, first name, last name, and date of birth.
- Many member fields are commented out, indicating that additional demographic mapping was planned but disabled.

## 5. `src/auth_to_optum_case_mapper_old.py`

This module contains an older version of the Optum case mapper and data model definitions.

```python
from pydantic import BaseModel, Field
from typing import Any, Optional
import logging
from datetime import datetime, date
from dateutil.parser import parse

logger = logging.getLogger(__name__)
```

- Similar imports and logger setup as the current mapper.

### Old data models

- `CaseDetails`: Contains case metadata, including urgent case and timestamps.
- `PatientDemographics`: Older member shape with zip, gender, race, plan info.
- `Procedure`: Older procedure model with service details and facility fields.
- `Document`: Older document model that includes `documentId` as excluded from serialization.
- `OptumCase`: Root case model for the old mapper.

```python
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
```

- Filters documents by a similar set of document types as the current mapper.

```python
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
```

- The old `map` method builds an older output shape and relies on `map_case_details`.

```python
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
```

- The old implementation calculates `earliestServiceDate` differently and maps procedures into the older `Procedure` model.

```python
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
```

- Maps older document records directly using the same document filter.

```python
    def map_case_details(self, auth, optumCase):
        optumCase.caseDetails.caseId = auth.get("caseNumber")
        optumCase.caseDetails.startTimestamp = parse(
            auth.get("creationDate")
        )  # is it createdate or recieved date
        optumCase.caseDetails.urgentCase = (
            auth.get("priority", "Standard") != "Standard"
        )
```

- Maps legacy case metadata into the old `CaseDetails` model.

```python
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
```

- Maps the older member demographic fields, including zip code, gender, and plan details.

## 6. `src/auditor.py`

This module currently contains placeholder audit definitions.

```python
class RequestAudit:
    requestId: str
    expectedAttachments: int
    exportedAttachments: int


def addRequestAudit(audit: RequestAudit):
    pass


def generateRequestAuditReport():
    pass
```

- `RequestAudit`: Declares the audit record shape with `requestId`, `expectedAttachments`, and `exportedAttachments`.
- `addRequestAudit(...)`: Stub method intended to add an audit entry.
- `generateRequestAuditReport()`: Stub method intended to create an audit report.

---

## Notes and Suggestions

- `src/main.py` has a duplicate `import csv` and a redundant `import path` re-import.
- In `src/auth_request.py`, the `from venv import logger` import should be corrected to use `logging`.
- `src/auth_to_optum_case_mapper.py` contains commented-out fields and unused helper methods that indicate a future extension path.
- `src/auth_to_optum_case_mapper_old.py` is an older mapper implementation and can be archived or removed once the new mapper is fully validated.

## Document Location

This walkthrough is saved at:

- `ocr_docu_automation_2/docs/code_walkthrough.md`
