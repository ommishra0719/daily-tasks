import asyncio
import aiohttp
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

URLS = [
    "https://jsonplaceholder.typicode.com/posts/1",
    "https://jsonplaceholder.typicode.com/posts/2",
    "https://jsonplaceholder.typicode.com/posts/3",
    "https://jsonplaceholder.typicode.com/posts/4",
    "https://jsonplaceholder.typicode.com/posts/5"
]


async def fetch(session, url):

    try:
        async with asyncio.timeout(5):

            async with session.get(url) as response:

                response.raise_for_status()

                data = await response.json()

                logging.info(f"Fetched {url}")

                return data

    except TimeoutError:

        logging.error(f"Timeout while fetching {url}")

    except Exception as e:

        logging.error(f"Error fetching {url}: {e}")


async def sequential_fetch():

    async with aiohttp.ClientSession() as session:

        results = []

        for url in URLS:

            result = await fetch(session, url)

            results.append(result)

        return results


async def concurrent_fetch():

    async with aiohttp.ClientSession() as session:

        tasks = [
            fetch(session, url)
            for url in URLS
        ]

        results = await asyncio.gather(*tasks)

        return results


async def main():

    start = time.perf_counter()

    sequential_results = await sequential_fetch()

    sequential_time = time.perf_counter() - start

    logging.info(
        f"Sequential completed in {sequential_time:.4f} seconds"
    )


    start = time.perf_counter()

    concurrent_results = await concurrent_fetch()

    concurrent_time = time.perf_counter() - start

    logging.info(
        f"Concurrent completed in {concurrent_time:.4f} seconds"
    )

    logging.info(
        f"Speedup = {sequential_time/concurrent_time:.2f}x"
    )


if __name__ == "__main__":

    asyncio.run(main())