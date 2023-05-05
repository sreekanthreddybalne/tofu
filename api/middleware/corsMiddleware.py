from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

class corsMiddleware(MiddlewareMixin):
    # def __init__(self, get_response):
    #     self.get_response = get_response
    #
    # def __call__(self, request):
    #     return self.get_response(request)

    def process_response(self, req, resp):
        print("sreeeeeeeeeeeeeee")
        print(req.headers)
        print(resp)
        print(resp.content)
        resp["Access-Control-Allow-Origin"] = "*"
        return resp
