from typing import List, Type, Any

from tornado.routing import _RuleList
from tornado.web import RequestHandler, Application
from prometheus_client import Histogram, Counter, REGISTRY
from prometheus_client.exposition import choose_encoder


class PrometheusMixInApplication(Application):
    default_bucket = (0.01, 0.05, 0.1, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, 15.0, 20.0, 30.0)

    def __init__(self, handlers: _RuleList = None, buckets: List[float] = default_bucket, default_host: str = None,
                 transforms: List[Type["OutputTransform"]] = None, **settings: Any) -> None:
        handlers.append((r"/metrics", PrometheusMetricsHandler))
        super().__init__(handlers, default_host, transforms, **settings)

        self.request_time_seconds = Histogram(
            namespace="tornado",
            subsystem="http",
            name="request_duration_seconds",
            documentation="HTTP request duration in seconds",
            buckets=buckets,
            labelnames=("handler", "method"),
        )

        self.requests_total = Counter(
            namespace="tornado",
            subsystem="http",
            name="requests_total",
            documentation="Total of HTTP requests processed",
            labelnames=("handler", "method", "status"),
        )

    def observe_request(self, handler):
        handler_name = type(handler).__name__
        method = handler.request.method
        request_time = handler.request.request_time()
        status = handler.get_status()

        self.request_time_seconds.labels(handler_name, method).observe(request_time)
        self.requests_total.labels(
            handler_name, method, self.classify_status_code(status)
        ).inc()

    def log_request(self, handler):
        super().log_request(handler)
        self.observe_request(handler)

    def classify_status_code(self, status_code):
        """
        Prometheus recomends to have lower number of cardinality,
        each combination creates a new metric in datastore,
        to reduce this risk we store only the class of status code
        """
        if 200 <= status_code < 300:
            return "2xx"

        if 300 <= status_code < 400:
            return "3xx"

        if 400 <= status_code < 500:
            return "4xx"

        return "5xx"


class PrometheusMetricsHandler(RequestHandler):
    def get(self):
        encoder, content_type = choose_encoder(self.request.headers.get('accept'))
        self.set_header("Content-Type", content_type)
        self.write(encoder(REGISTRY))
