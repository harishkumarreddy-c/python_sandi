from venv import logger
from httpx import AsyncClient, codes
import os
import typing


class MhkAuthRepo:

    def __init__(self):
        pass

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

    async def __aexit__(self, *_):
        try:
            if not self.__client.is_closed:
                await self.__client.aclose()
        except:
            pass

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
        
    async def getAuthInquiry(self, **kwArgs) -> typing.Optional[bytes]:
        """
        Send medhokID and/or inquiryNumber to get enquiry details
        """
        
        url: str = "AuthRestServices/getAuthInquiry"
        try:
            apiParams = {}
            if kwArgs["medhokID"]:
                apiParams["medhokID"] = kwArgs["medhokID"]

            if kwArgs["inquiryNumber"]:
                apiParams["inquiryNumber"] = kwArgs["inquiryNumber"]

            if apiParams.__len__ == 0:
                raise Exception("Invalid inputs!. at least one value required with the key names 'medhokID' and/or 'inquiryNumber'")
            
            response = await self.__client.get(
                url,
                headers={
                    "MEDHOKUSER": os.environ.get("MEDHOKUSER", ""),
                    "PWD": os.environ.get("MHK_PASS", ""),
                },
                params=apiParams,
            )
            return response.content
        except Exception as e:
            logger.exception(f"Failed to connect:", exc_info=e)
            return None
