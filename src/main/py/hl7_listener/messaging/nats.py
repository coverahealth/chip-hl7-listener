from typing import (
    Union,
)

from covera.loglib import configure_get_logger
from covera_ddtrace import inject_ddtrace
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrNoServers

import hl7_listener.messaging.settings as msgr_config
from hl7_listener import (
    NATS_CONNECT_ERROR,
    NATS_CONNECTED,
    NATS_REQUEST_SEND_MSG_RESPONSE,
    SENDING_MSG_TO_NATS,
)
from hl7_listener.messaging.base import MessagingInterface

logger = configure_get_logger()
PILOT_HEADER = {"record_id": "pilot:pilot", "payload_type": "hl7", "trigger": "pilot"}


class NATSMessager(MessagingInterface):

    @inject_ddtrace
    async def connect(self) -> bool:
        """Connect to the NATS jetstream server."""
        self.conn = NATS()
        try:
            await self.conn.connect(msgr_config.settings.NATS_SERVER_URL)
            logger.info(
                NATS_CONNECTED,
                logging_code="HL7LLOG006",
                nats_server_url=msgr_config.settings.NATS_SERVER_URL
            )
            return True

        except ErrNoServers as exp:
            logger.error(
                NATS_CONNECT_ERROR,
                logging_code="HL7LERR002",
                exc_info=exp
            )
            raise exp

    @inject_ddtrace
    async def send_msg(self, msg: Union[str, bytes]) -> None:
        """Synchronously (no callback or async ACK) send the input message to the NATS
        configured Subject.

        Note: An Exception will result if the send times out or fails for other reasons.
        """
        assert isinstance(msg, (str, bytes))

        to_send = msg
        if isinstance(msg, str):
            to_send = msg.encode()

        logger.info(SENDING_MSG_TO_NATS, logging_code="HL7LLOG007")

        kwargs = {
            "subject": msgr_config.settings.NATS_OUTGOING_SUBJECT,
            "payload": to_send,
            "timeout": 10,
        }

        if msgr_config.settings.PILOT_MODE:
            kwargs["headers"] = PILOT_HEADER

        send_response = await self.conn.request(**kwargs)
        logger.info(
            NATS_REQUEST_SEND_MSG_RESPONSE,
            logging_code="HL7LLOG008",
            send_response=send_response
        )
