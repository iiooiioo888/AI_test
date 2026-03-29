"""
負載測試腳本
壓力測試、性能基準測試、瓶頸分析
"""
import asyncio
import time
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass, field
import aiohttp
import structlog

logger = structlog.get_logger()


@dataclass
class LoadTestResult:
    """負載測試結果"""
    test_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    
    # 時間指標 (毫秒)
    min_latency: float = 0.0
    max_latency: float = 0.0
    avg_latency: float = 0.0
    median_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0
    
    # 吞吐量
    requests_per_second: float = 0.0
    
    # 錯誤
    error_rate: float = 0.0
    errors: List[str] = field(default_factory=list)
    
    def calculate_metrics(self, latencies: List[float], duration: float):
        """計算指標"""
        if latencies:
            self.min_latency = min(latencies)
            self.max_latency = max(latencies)
            self.avg_latency = statistics.mean(latencies)
            self.median_latency = statistics.median(latencies)
            
            sorted_latencies = sorted(latencies)
            p95_idx = int(len(sorted_latencies) * 0.95)
            p99_idx = int(len(sorted_latencies) * 0.99)
            self.p95_latency = sorted_latencies[p95_idx] if p95_idx < len(sorted_latencies) else 0
            self.p99_latency = sorted_latencies[p99_idx] if p99_idx < len(sorted_latencies) else 0
        
        self.requests_per_second = self.total_requests / duration if duration > 0 else 0
        self.error_rate = self.failed_requests / self.total_requests if self.total_requests > 0 else 0


class LoadTester:
    """
    負載測試器
    
    測試場景：
    1. API 端點壓力測試
    2. 並發用戶模擬
    3. 長時間穩定性測試
    4. 瓶頸分析
    """
    
    def __init__(self, base_url: str = "http://localhost:8888"):
        self.base_url = base_url
        self.results: List[LoadTestResult] = []
    
    async def test_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        concurrent_users: int = 10,
        requests_per_user: int = 100,
        payload: Dict = None,
    ) -> LoadTestResult:
        """
        測試單個端點
        
        Args:
            endpoint: API 端點
            method: HTTP 方法
            concurrent_users: 並發用戶數
            requests_per_user: 每用戶請求數
            payload: 請求體
            
        Returns:
            LoadTestResult: 測試結果
        """
        url = f"{self.base_url}{endpoint}"
        total_requests = concurrent_users * requests_per_user
        
        logger.info(
            "load_test_started",
            endpoint=endpoint,
            total_requests=total_requests,
            concurrent_users=concurrent_users,
        )
        
        latencies: List[float] = []
        errors: List[str] = []
        successful = 0
        failed = 0
        
        start_time = time.time()
        
        # 創建並發任務
        async with aiohttp.ClientSession() as session:
            tasks = []
            for _ in range(concurrent_users):
                task = self._user_session(
                    session, url, method, requests_per_user, payload, latencies, errors
                )
                tasks.append(task)
            
            await asyncio.gather(*tasks, return_exceptions=True)
        
        duration = time.time() - start_time
        
        # 計算結果
        result = LoadTestResult(
            test_name=f"{method} {endpoint}",
            total_requests=total_requests,
            successful_requests=successful,
            failed_requests=failed,
        )
        
        result.successful_requests = len(latencies)
        result.failed_requests = len(errors)
        result.errors = errors[:10]  # 只保留前 10 個錯誤
        result.calculate_metrics(latencies, duration)
        
        self.results.append(result)
        
        logger.info(
            "load_test_completed",
            endpoint=endpoint,
            duration=duration,
            rps=result.requests_per_second,
            avg_latency=result.avg_latency,
            error_rate=result.error_rate,
        )
        
        return result
    
    async def _user_session(
        self,
        session: aiohttp.ClientSession,
        url: str,
        method: str,
        requests: int,
        payload: Dict,
        latencies: List[float],
        errors: List[str],
    ):
        """模擬用戶會話"""
        for _ in range(requests):
            try:
                start = time.time()
                
                if method == "GET":
                    async with session.get(url) as response:
                        await response.text()
                elif method == "POST":
                    async with session.post(url, json=payload) as response:
                        await response.text()
                
                latency = (time.time() - start) * 1000  # ms
                latencies.append(latency)
                
            except Exception as e:
                errors.append(str(e))
            
            # 模擬用戶思考時間
            await asyncio.sleep(0.01)
    
    async def run_all_tests(self) -> Dict[str, LoadTestResult]:
        """運行所有測試"""
        tests = [
            # 健康檢查
            self.test_endpoint("/health", concurrent_users=50, requests_per_user=20),
            
            # API 端點
            self.test_endpoint("/api/v1/scenes/", concurrent_users=20, requests_per_user=50),
            self.test_endpoint("/api/v1/projects/", concurrent_users=20, requests_per_user=50),
            self.test_endpoint("/api/v1/prompts/", concurrent_users=20, requests_per_user=50),
            
            # 高負載端點
            self.test_endpoint(
                "/api/v1/generation/submit",
                method="POST",
                concurrent_users=10,
                requests_per_user=20,
                payload={"scene_id": "test-001"},
            ),
        ]
        
        results = await asyncio.gather(*tests, return_exceptions=True)
        
        return {
            "health": results[0] if isinstance(results[0], LoadTestResult) else None,
            "scenes": results[1] if isinstance(results[1], LoadTestResult) else None,
            "projects": results[2] if isinstance(results[2], LoadTestResult) else None,
            "prompts": results[3] if isinstance(results[3], LoadTestResult) else None,
            "generation": results[4] if isinstance(results[4], LoadTestResult) else None,
        }
    
    def print_report(self):
        """打印測試報告"""
        print("\n" + "="*80)
        print("📊 LOAD TEST REPORT")
        print("="*80 + "\n")
        
        for result in self.results:
            print(f"📍 {result.test_name}")
            print(f"   Total Requests: {result.total_requests}")
            print(f"   Success: {result.successful_requests} | Failed: {result.failed_requests}")
            print(f"   Error Rate: {result.error_rate*100:.2f}%")
            print(f"   Throughput: {result.requests_per_second:.2f} req/s")
            print(f"   Latency (ms):")
            print(f"     Min: {result.min_latency:.2f}")
            print(f"     Avg: {result.avg_latency:.2f}")
            print(f"     Median: {result.median_latency:.2f}")
            print(f"     P95: {result.p95_latency:.2f}")
            print(f"     P99: {result.p99_latency:.2f}")
            print(f"     Max: {result.max_latency:.2f}")
            
            if result.errors:
                print(f"   Errors: {len(result.errors)}")
                for error in result.errors[:3]:
                    print(f"     - {error}")
            
            print()
        
        print("="*80)


async def main():
    """主函數"""
    tester = LoadTester()
    
    print("🚀 Starting Load Tests...")
    await tester.run_all_tests()
    tester.print_report()


if __name__ == "__main__":
    asyncio.run(main())
