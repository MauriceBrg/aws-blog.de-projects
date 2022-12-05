import asyncio
import random
import time
import typing


async def sleepy_boi(name: str) -> int:
    """Sleeps for a bit and returns the number of seconds it slept for."""
    # In practice, this would be I/O operations
    sleep_for_s = random.randint(1, 5)
    await asyncio.sleep(sleep_for_s)
    print(f"Sleepy Boi {name} woke up after {sleep_for_s}s")
    return sleep_for_s


async def sleepy_bois(number_of_bois: int) -> typing.List[int]:
    """Calls many sleepy bois"""

    return await asyncio.gather(
        *[sleepy_boi(f"boi_{i}") for i in range(number_of_bois)]
    )


def main():
    """Main function that triggers the async magic."""

    start = time.perf_counter()

    result = asyncio.run(sleepy_bois(5))

    runtime = time.perf_counter() - start
    print(f"It took {runtime:.3f}s to execute, the total wait time was {sum(result)}s.")


if __name__ == "__main__":
    main()

