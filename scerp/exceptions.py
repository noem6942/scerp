'''
scerp/exceptions.py

To raise a custom error when a REST API call fails, and control the behavior
so that you don't flood the user with too many errors, you can create a
custom exception class. Then, you can catch this exception and display a
user-friendly message in the admin.py without showing the raw exception
details.

'''
class APIRequestError(Exception):
    """Custom exception for failed API requests."""
    def __init__(self, message):
        super().__init__(message)
