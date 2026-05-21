import argparse # for command-line argument parsing
import asyncio # for asynchronous programming for handling multiple requests concurrently
import csv
from typing import Any # for type hinting to indicate that a variable can be of any type

from anyio import Path # for handling file paths in a platform-independent way

from auth_request import AuthRequester # for making authenticated requests to fetch case details and attachments
from dotenv import load_dotenv # for loading environment variables from a .env file, which can contain sensitive information like API keys or configuration settings
from os import mkdir, path, makedirs # for creating directories and handling file paths
import logging # for logging information, errors, and exceptions during the execution of the script
import datetime # for handling date and time, particularly for timestamping logs and output files
import zipfile # for creating ZIP files to store the extracted case details and attachments in a compressed format
from os import path # for handling file paths, such as determining the current directory and constructing paths to input and output files

from csv import DictReader # for reading CSV files and converting each row into a dictionary, which allows for easier access to the data using column names as keys
import csv # for handling CSV files, which are used for inputting case guidelines and requests, and potentially for outputting results in a structured format

from auth_to_optum_case_mapper import AuthToOptumCaseMapper, OptumCase, OptumFinalCase # for mapping the authenticated case details to a specific format required by Optum, and for defining the data structures (OptumCase and OptumFinalCase) that represent the case details in the desired format


logger = logging.getLogger(__name__)  # type: ignore
CURRENT_DIR = path.dirname(path.abspath(__file__))
ROOT_DIR = Path(CURRENT_DIR).parent


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


def fetch_request_guideline(guideLines, subset):
    guideLine: dict[str, str] | Any = None
    for guide in guideLines:
        if guide.get("Guideline Name", "").lower().strip() == subset.lower().strip():
            guideLine = guide
    return guideLine


def load_guidelines(environment: str):
    guidelineFile = ROOT_DIR.joinpath(
        "input", f"{environment.lower()}", "Optum_Guidelines.csv"
    )
    with open(guidelineFile, encoding="utf-8-sig", newline="") as guidelineText:
        reader = DictReader(guidelineText)
        return [line for line in reader]


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


def load_config(environment: str):
    env_file = ROOT_DIR.joinpath("config", f".env.{environment.lower()}")

    load_dotenv(dotenv_path=env_file)


def load_requests(environment: str) -> list[dict[str, str]]:

    requestFile = ROOT_DIR.joinpath(
        "input", f"{environment.lower()}", "case_guidelines.csv"
    )
    with open(requestFile, encoding="utf-8-sig", newline="") as requestText:
        # fieldnames = ['first_name', 'last_name']
        reader = DictReader(requestText)
        return [line for line in reader]


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
