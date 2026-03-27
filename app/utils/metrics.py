"""
Prometheus 監控指標
"""
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry


class Metrics:
    """Prometheus 指標集合"""
    
    def __init__(self):
        # HTTP 請求指標
        self.request_count = Counter(
            'avp_http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status']
        )
        
        self.request_duration = Histogram(
            'avp_http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint', 'status'],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
        )
        
        # 視頻生成指標
        self.generation_tasks_total = Counter(
            'avp_generation_tasks_total',
            'Total video generation tasks',
            ['status']  # queued, processing, completed, failed
        )
        
        self.generation_duration = Histogram(
            'avp_generation_duration_seconds',
            'Video generation duration',
            ['model', 'resolution'],
            buckets=(10, 30, 60, 120, 300, 600, 1200, 1800)
        )
        
        self.gpu_utilization = Gauge(
            'avp_gpu_utilization_percent',
            'GPU utilization percentage',
            ['gpu_id']
        )
        
        # 提示詞指標
        self.prompt_success_rate = Gauge(
            'avp_prompt_success_rate',
            'Prompt success rate',
            ['category']
        )
        
        # 數據庫指標
        self.db_query_duration = Histogram(
            'avp_database_query_duration_seconds',
            'Database query duration',
            ['operation'],
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0)
        )
        
        # WebSocket 指標
        self.websocket_connections = Gauge(
            'avp_websocket_connections',
            'Active WebSocket connections'
        )


# 全局指標實例
metrics = Metrics()
