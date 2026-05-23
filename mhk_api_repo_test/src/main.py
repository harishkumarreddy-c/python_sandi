import argparse
import asyncio
import csv
from typing import Any

from anyio import Path

from mhk_api_repo import MhkAuthRepo
from dotenv import load_dotenv
from os import mkdir, path, makedirs
import logging
import datetime
import zipfile
from os import path

from csv import DictReader
import csv

logger = logging.getLogger(__name__)  # type: ignore
CURRENT_DIR = path.dirname(path.abspath(__file__))
ROOT_DIR = Path(CURRENT_DIR).parent


async def main(environment: str):
    logger.info(f"Current Environment is {environment}")

    load_config(environment)

    mhkCases: list[dict[str, str]] = load_requests(environment)

    logger.info(f"Total # of cases : {len(mhkCases)}")

    if not mhkCases:
        logger.info("No request found to extract")
        exit()

    # Loop through all the cases from the file
    for case in mhkCases:
        # Fetch case details
        async with MhkAuthRepo() as apiClient:
            mhkResponse = await apiClient.getAuthInquiry(case)
            
            # Log all the case details
            # print(mhkResponse)
            logger.info(f"Case details with the medhokID:{case.get("medhokID")} and inquiryNumber:{case.get("inquiryNumber")}", mhkResponse)
            
            output_dir = ROOT_DIR.joinpath(
                "output",
                "mhk_cases-" + datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
            )



def load_config(environment: str):
    env_file = ROOT_DIR.joinpath("config", f".env.{environment.lower()}")

    load_dotenv(dotenv_path=env_file)


def load_requests(environment: str) -> list[dict[str, str]]:

    caseFile = ROOT_DIR.joinpath("input", f"{environment.lower()}", "case.csv")
    with open(caseFile, encoding="utf-8-sig", newline="") as requestText:
        # fieldnames = ['first_name', 'last_name']
        reader = DictReader(requestText)
        return [line for line in reader]


if __name__ == "__main__":

    makedirs(
        ROOT_DIR.joinpath(
            "logs",
        ),
        exist_ok=True,
    )

    logging.basicConfig(
        filename=f"logs/MHK_case_{datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.log",
        level=logging.INFO,
    )
    logger.info("Starting Process to extract case details")

    parser = argparse.ArgumentParser(description=" Case Extractor")
    parser.add_argument(
        "-env", type=str, default="uat", help="Application Environment."
    )
    args = vars(parser.parse_args())
    try:
        asyncio.run(main(args["env"]))
    except Exception as ex:
        logger.exception("Process failed", exc_info=ex)

    finally:
        logger.info("Ending Process to extract case details")
