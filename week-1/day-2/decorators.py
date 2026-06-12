import time
import functools
import pytest

# ==========================================
# 1. DECORATORS
# ==========================================

def timeit(func):
    #Decorator that measures and prints the execution time of a function.
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        print(f"[{func.__name__}] executed in {execution_time:.4f} seconds")
        return result
    return wrapper

def retry(max_attempts=3, delay=1.0, exceptions=(IOError,)):
    #Decorator factory that retries a function if specific exceptions are raised.
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempts += 1
                    print(f"[{func.__name__}] Attempt {attempts}/{max_attempts} failed with {e.__class__.__name__}: {e}")
                    if attempts >= max_attempts:
                        print(f"[{func.__name__}] Max attempts reached. Raising exception.")
                        raise
                    print(f"[{func.__name__}] Retrying in {delay} seconds...")
                    time.sleep(delay)
        return wrapper
    return decorator


# ==========================================
# 2. SIMULATED API CALL
# ==========================================

class UnstableAPI:
    def __init__(self):
        self.call_count = 0

    @timeit
    @retry(max_attempts=3, delay=1.0, exceptions=(IOError,))
    def fetch_data(self):
        #Simulates an API call that fails twice, then succeeds on the third try.
        self.call_count += 1
        if self.call_count < 3:
            raise IOError("Network timeout")
        return {"status": "success", "data": "Sample payload"}


# ==========================================
# 3. PYTESTS
# ==========================================

def test_retry_success_after_failures():
    #Test that the function eventually succeeds after failing twice.
    api = UnstableAPI()
    
    # The first two calls will raise IOError, caught by @retry.
    # The third call will succeed.
    result = api.fetch_data()
    
    assert result["status"] == "success"
    assert api.call_count == 3  # Verifies it actually retried exactly 3 times

def test_retry_max_attempts_exceeded():
    #Test that the function raises the error if it exceeds max_attempts.
    # Create a dummy function that ALWAYS fails
    @retry(max_attempts=2, delay=1.0, exceptions=(ValueError,))
    def always_fails():
        raise ValueError("Permanent failure")

    with pytest.raises(ValueError, match="Permanent failure"):
        always_fails()

def test_timeit_metadata_preservation():
    #Test that @functools.wraps successfully preserved metadata.
    
    @timeit
    def dummy_func():
        """This is a dummy docstring."""
        pass
        
    assert dummy_func.__name__ == "dummy_func"
    assert dummy_func.__doc__ == "This is a dummy docstring."

if __name__ == "__main__":
    # Quick manual demonstration
    print("--- Running Manual Demonstration ---")
    api = UnstableAPI()
    try:
        data = api.fetch_data()
        print("Final Result:", data)
    except Exception as e:
        print("Final Failure:", e)