from tornado.web import RequestHandler
from tornado.testing import AsyncHTTPTestCase

from tornado_prometheus import PrometheusMixInApplication


class SampleApp(PrometheusMixInApplication):
    pass


class MainHandler(RequestHandler):
    def get(self):
        self.write("Hello, world")


class TestIntegration(AsyncHTTPTestCase):
    def get_app(self):
        return SampleApp([(r"/", MainHandler)])

    def test_integration(self):
        self.fetch("/")
        response = self.fetch("/metrics")
        self.assertIn(
            b'tornado_http_requests_total{handler="MainHandler",method="GET",status="2xx"} 1.0',
            response.body,
        )
        self.assertIn(
            b'tornado_http_request_duration_seconds_bucket{handler="MainHandler",le="15.0",method="GET"} 1.0',
            response.body,
        )
