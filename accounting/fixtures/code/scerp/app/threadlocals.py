from threading import local

_user = local()

class ThreadLocals(object):
    """
    Middleware that gets various objects from the
    request object and saves them in thread local storage
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _user.value = request.user
        response = self.get_response(request)
        return response
