"""For posting announcements to a live Twitch channel."""

import datetime
import logging
import time
import json
import sys

import requests


class Looper():
    """Looping class to continuously check for updates."""

    SECONDS_IN_A_MINUTE = 60
    URL_PREFIX = "https://api.twitch.tv/helix/"

    def __init__(
        self,
        announcements: list[str],
        ignore_offline: bool,
        broadcaster_id: str,
        moderator_id: str,
        interval: float,
        client_id: str,
        token: str,
    ) -> None:
        logging.info('Initializing...')

        self.broadcaster_id = broadcaster_id
        self.ignore_offline = ignore_offline
        self.announcements = announcements
        self.moderator_id = moderator_id
        self.interval = interval
        self.index = 0

        self.headers = {
            "Authorization": f"Bearer {token}",
            "Client-Id": client_id,
        }

        logging.info('Initialized.')

    def run(self) -> None:
        """Main entry point."""

        while True:
            self.send_announcement()

    def send_announcement(self) -> None:
        """Main process for sending announcements."""

        now = datetime.datetime.now()

        seconds_until_announcement = self.interval - (datetime.timedelta(
            days=now.day,
            minutes=now.minute,
            seconds=now.second,
            microseconds=now.microsecond
            ) / datetime.timedelta(seconds=1)) % self.interval

        wait = datetime.timedelta(
            seconds=seconds_until_announcement
        )

        logging.info(
            "Waiting %s minute(s), %s second(s), and %s microsecond(s)...",
            seconds_until_announcement // self.SECONDS_IN_A_MINUTE,
            seconds_until_announcement % self.SECONDS_IN_A_MINUTE,
            f"{wait.microseconds:,}"
        )

        time.sleep(seconds_until_announcement)
        logging.info("Starting...")

        if self.ignore_offline and not self.try_request(self.get_online):
            logging.info('Channel is offline.')
            return

        logging.info(
            "Sending announcement to broadcaster ID '%s': '%s'.",
            self.broadcaster_id,
            self.get_announcement()
        )

        if self.try_request(self.post_announce):
            logging.info('Sent.')
            self.index = (self.index + 1) % len(self.announcements)

    def try_request(self, request) -> bool:
        """Attempt a request. Returns success."""

        try:
            return request()
        except requests.exceptions.Timeout:
            logging.error("Request timed out.")
            return False

    def get_online(self) -> bool:
        """Is the channel online? May raise a Timeout."""

        response = requests.get(
            f"{self.URL_PREFIX}streams",
            {"user_id": self.broadcaster_id},
            headers=self.headers,
            timeout=self.SECONDS_IN_A_MINUTE
        )

        return self.check_status_code(response, 200) and response.json()[
            'data'
        ]

    def post_announce(self) -> bool:
        """Send the announcement. May raise a Timeout."""

        params = {
            "broadcaster_id": self.broadcaster_id,
            "moderator_id": self.moderator_id
        }

        response = requests.post(
            f"{self.URL_PREFIX}chat/announcements",
            {"message": self.announcements[self.index]},
            params=params,
            headers=self.headers,
            timeout=60
        )

        return self.check_status_code(response, 204)

    def get_announcement(self) -> str:
        """Get the current announcement."""

        return self.announcements[self.index]

    def check_status_code(self, response, status_code):
        """Check the result code and log any errors."""

        result = response.status_code == status_code

        if not result:
            logging.error(response.content)

        return result


def main() -> None:
    """Main entry method when running the script directly."""

    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    args = sys.argv

    with open(args[1], encoding="utf-8") as file:
        config = json.load(file)

    Looper(**config).run()


if __name__ == '__main__':
    main()
