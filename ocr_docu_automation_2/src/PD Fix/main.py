import argparse
import asyncio
import csv
from typing import Any

from anyio import Path

from dotenv import load_dotenv
from os import mkdir, path, makedirs
import logging
import datetime
import zipfile
from os import path

from csv import DictReader
import csv

from venv import logger
from httpx import AsyncClient, codes
import os
import typing
import base64
import random
import io

logger = logging.getLogger(__name__)  # type: ignore
CURRENT_DIR = path.dirname(path.abspath(__file__))
ROOT_DIR = Path(CURRENT_DIR).parent.parent


async def main(environment: str):
    logger.info(f"Current Environment is {environment}")

    load_config(environment)

    mhkRequests: list[str] = [
        "D26097803205",
        "D26096641189",
        "D26083362884",
        "D26079669618",
    ]
    __client = AsyncClient(
        headers={
            "MEDHOKUSER": os.environ.get("MEDHOKUSER", ""),
            "PWD": os.environ.get("MHK_PASS", ""),
        },
        base_url=os.environ.get("MHK_ROOT_URL", ""),
    )

    for request in mhkRequests:
        url: str = f"ProviderDisputesRestServices/getProviderDisputes?case={request}"
        try:
            response = await __client.post(url, json={})
            if response.status_code == codes.OK:
                pd_case = response.json()[0]
                medhokId = pd_case["medhokID"]
                for docs in pd_case["documents"]:
                    if docs["documentType"] != "Provider Disputes Document":
                        continue
                    if docs["userId"] != "MCED":
                        continue
                    document = await getAuthAttachment(docs["documentId"], __client)
                    if document:
                        decoded_data = base64.b64decode(document)

                        await postAuthAttachment(
                            docs["documentId"],
                            __client,
                            decoded_data,
                            Path(docs["fileName"]).stem
                            + "_"
                            + str(random.randint(1, 10))
                            + ".pdf",
                            medhokId,
                        )

                        # with open(
                        #     Path(docs["fileName"]).stem
                        #     + str(random.randint(1, 10))
                        #     + ".pdf",
                        #     "wb",
                        # ) as f:
                        #     f.write(decoded_data)

            else:
                response.raise_for_status()
        except Exception as e:
            logger.exception(
                f"Failed to get case details for case {request}", exc_info=e
            )
            return None


def load_config(environment: str):
    env_file = ROOT_DIR.joinpath("config", f".env.{environment.lower()}")

    load_dotenv(dotenv_path=env_file)


async def getAuthAttachment(documentId, client) -> typing.Optional[bytes]:

    url: str = "DocumentRestServices/getDocument"
    try:
        response = await client.get(
            url,
            headers={
                "MEDHOKUSER": os.environ.get("MEDHOKUSER", ""),
                "PWD": os.environ.get("MHK_PASS", ""),
            },
            params={"documentId": documentId},
        )
        if response.status_code != codes.OK:
            response.raise_for_status()
        return response.content
    except Exception as e:
        logger.exception(f"Failed to download file {documentId}", exc_info=e)
        return None


async def postAuthAttachment(
    documentId, client, decoded_data: bytes, fileName: str, medhokId: str
) -> typing.Optional[bytes]:

    url: str = "DocumentRestServices/addDocument"
    try:
        response = await client.post(
            url,
            headers={
                "MEDHOKUSER": os.environ.get("MEDHOKUSER", ""),
                "PWD": os.environ.get("MHK_PASS", ""),
            },
            params={
                "medhokID": medhokId,
                "documentType": "Provider Disputes Document",
                "userId": "MCED",
                "context": "ProviderDispute",
                "fileName": fileName,
            },
            files={"file": (fileName, io.BytesIO(decoded_data), "application/pdf")},
        )
        if response.status_code != codes.OK:
            response.raise_for_status()
        return response.content
    except Exception as e:
        logger.exception(f"Failed to download file {documentId}", exc_info=e)
        return None


if __name__ == "__main__":
    logging.basicConfig(
        filename=f"logs/PD_{datetime.datetime.now()}.log", level=logging.INFO
    )
    logger.info("Starting Process to extract case details")

    parser = argparse.ArgumentParser(description="Optum Case Extractor")
    parser.add_argument(
        "-env", type=str, default="prod", help="Application Environment."
    )
    args = vars(parser.parse_args())
    try:
        print("Update me")
        asyncio.run(main(args["env"]))
    except Exception as ex:
        logger.exception("Process failed", exc_info=ex)

    finally:
        logger.info("Ending Process to extract case details")
