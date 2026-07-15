"""
API 请求日志中间件
- 记录每次请求的方法、路径、客户端 IP、User-Agent
- 记录响应状态码、耗时（毫秒）
"""
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logger import get_logger

logger = get_logger("request")


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """API 请求日志中间件"""

    async def dispatch(self, request: Request, call_next) -> Response:
        # 请求开始时间
        start_time = time.time()

        # 获取客户端信息
        client_host = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        method = request.method
        path = request.url.path

        # 记录请求开始
        logger.info(
            f"Request started | "
            f"Method: {method} | "
            f"Path: {path} | "
            f"Client: {client_host} | "
            f"User-Agent: {user_agent}"
        )

        # 处理请求
        try:
            response = await call_next(request)
        except Exception as e:
            # 记录异常
            logger.error(
                f"Request failed | "
                f"Method: {method} | "
                f"Path: {path} | "
                f"Error: {str(e)}"
            )
            raise

        # 计算耗时
        process_time = (time.time() - start_time) * 1000  # 转换为毫秒

        # 记录请求完成
        logger.info(
            f"Request completed | "
            f"Method: {method} | "
            f"Path: {path} | "
            f"Status: {response.status_code} | "
            f"Duration: {process_time:.2f}ms"
        )

        # 添加响应头
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

        return response
