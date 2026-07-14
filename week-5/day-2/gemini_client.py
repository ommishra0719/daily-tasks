import logging
import mimetypes
import os
import time
from pathlib import Path

from google import genai
from google.genai import types


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


class GeminiClient:
    """
    Production-ready Gemini wrapper.

    Features
    --------
    ✓ Token counting
    ✓ Budget enforcement
    ✓ Retry on HTTP 429
    ✓ Token usage logging
    ✓ Multimodal support
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        system_instruction: str = "You are a helpful AI assistant.",
        token_budget: int = 8000,
        max_retries: int = 3,
    ):
        self.client = genai.Client(api_key=api_key)

        self.model = model
        self.token_budget = token_budget
        self.max_retries = max_retries

        self.config = types.GenerateContentConfig(
            system_instruction=system_instruction
        )

    ###############################################################
    # Token Counting
    ###############################################################

    def count_tokens(self, contents):
        response = self.client.models.count_tokens(
            model=self.model,
            contents=contents,
        )

        return response.total_tokens

    ###############################################################
    # Budget Check
    ###############################################################

    def _enforce_budget(self, contents):
        tokens = self.count_tokens(contents)

        logging.info(f"Prompt Tokens: {tokens}")

        if tokens > self.token_budget:
            raise ValueError(
                f"Token budget exceeded "
                f"({tokens}>{self.token_budget})"
            )

        return tokens

    ###############################################################
    # Retry Logic
    ###############################################################

    def _generate_with_retry(self, contents):

        delay = 1

        for attempt in range(self.max_retries):

            try:
                return self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=self.config,
                )

            except Exception as e:

                error = str(e)

                if "429" not in error:
                    raise

                logging.warning(
                    f"429 Rate Limit. "
                    f"Retry {attempt+1}/{self.max_retries}"
                )

                time.sleep(delay)

                delay *= 2

        raise RuntimeError("Maximum retries exceeded.")

    ###############################################################
    # Usage Logging
    ###############################################################

    @staticmethod
    def _log_usage(response):

        usage = response.usage_metadata

        logging.info("========== Token Usage ==========")

        logging.info(
            f"Prompt Tokens : {usage.prompt_token_count}"
        )

        logging.info(
            f"Output Tokens : {usage.candidates_token_count}"
        )

        logging.info(
            f"Total Tokens  : {usage.total_token_count}"
        )

        logging.info("===============================")

    ###############################################################
    # Public Text Generation
    ###############################################################

    def generate(self, prompt: str):

        self._enforce_budget(prompt)

        response = self._generate_with_retry(prompt)

        self._log_usage(response)

        return response.text

    ###############################################################
    # Multimodal Generation
    ###############################################################

    def generate_from_image(
        self,
        image_path: str,
        question: str,
    ):

        image_path = Path(image_path)

        mime_type = (
            mimetypes.guess_type(image_path)[0]
            or "image/jpeg"
        )

        image_bytes = image_path.read_bytes()

        image = types.Part.from_bytes(
            data=image_bytes,
            mime_type=mime_type,
        )

        contents = [
            image,
            question,
        ]

        self._enforce_budget(contents)

        response = self._generate_with_retry(contents)

        self._log_usage(response)

        return response.text