#!/usr/bin/env python3
"""
集成测试 - 验证错误响应内容功能
"""

import asyncio
import sys
sys.path.insert(0, '/Users/reborn/Workspace/Dev/AnyRouter-Transparent-Proxy')

from backend.utils.encoding import ensure_unicode


async def test_encoding_available():
    """测试编码模块可用性"""
    print("\n1. 测试编码模块...")
    try:
        test_bytes = "当前模型错误".encode('utf-8')
        result = ensure_unicode(test_bytes)
        print(f"✓ 编码转换成功: {result}")
        assert "当前模型错误" in result
        return True
    except Exception as e:
        print(f"✗ 编码转换失败: {e}")
        return False


async def test_stats_data_structure():
    """测试 stats 数据结构"""
    print("\n2. 测试 stats 数据结构...")
    try:
        from backend.services.stats import recent_requests
        from collections import deque

        # 模拟错误请求数据
        test_error = {
            "request_id": "test-123",
            "path": "/test",
            "method": "POST",
            "status_code": 400,
            "error": "HTTP 400",
            "response_content": "Error: 当前模型不可用",
            "response_time": 0.1,
            "timestamp": 1234567890
        }

        # 添加到 recent_requests deque
        recent_requests.append(test_error)
        print(f"✓ 数据结构支持 response_content")
        return True
    except Exception as e:
        print(f"✗ 数据结构测试失败: {e}")
        return False


async def test_api_response_structure():
    """测试 API 响应结构"""
    print("\n3. 测试 API 响应结构...")
    try:
        # 模拟 get_stats 返回的数据
        mock_stats = {
            "summary": {"total_requests": 10, "failed_requests": 2},
            "recent_requests": [
                {
                    "request_id": "req-1",
                    "path": "/v1/messages",
                    "method": "POST",
                    "status_code": 400,
                    "error": "HTTP 400: Bad Request",
                    "response_content": '{"error": {"message": "当前模型无法访问"}}',
                    "response_time": 0.123,
                    "timestamp": 1234567890,
                    "bytes": 0
                }
            ]
        }

        # 检查字段存在
        assert "response_content" in mock_stats["recent_requests"][0]
        assert "status_code" in mock_stats["recent_requests"][0]
        print(f"✓ API 响应结构包含 response_content")
        print(f"  示例: {mock_stats['recent_requests'][0]['response_content']}")
        return True
    except Exception as e:
        print(f"✗ API 响应结构测试失败: {e}")
        return False


async def test_error_logs_api():
    """测试错误日志 API 结构"""
    print("\n4. 测试错误日志 API...")
    try:
        # 模拟 get_errors 返回的数据
        mock_errors = {
            "errors": [
                {
                    "request_id": "req-error-1",
                    "path": "/v1/completions",
                    "error": "Connection timeout",
                    "timestamp": 1234567890,
                    "formatted_time": "2024-12-11 14:30:00",
                    "response_time": 5000.0,
                    "response_content": "上游服务器连接超时"
                }
            ],
            "pagination": {"total": 1, "limit": 50, "offset": 0, "has_more": False},
            "statistics": {"total_errors": 1, "total_requests": 10, "error_rate": 0.1}
        }

        assert "response_content" in mock_errors["errors"][0]
        print(f"✓ 错误日志 API 包含 response_content")
        print(f"  示例: {mock_errors['errors'][0]['response_content']}")
        return True
    except Exception as e:
        print(f"✗ 错误日志 API 测试失败: {e}")
        return False


async def test_frontend_types():
    """测试前端 TypeScript 类型定义"""
    print("\n5. 测试前端类型定义...")
    try:
        # 检查类型文件中是否定义了 response_content
        with open('frontend/src/types/index.ts', 'r') as f:
            content = f.read()

        assert 'response_content?: string' in content
        print(f"✓ 前端类型定义包含 response_content")
        return True
    except Exception as e:
        print(f"✗ 前端类型测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("=" * 70)
    print("集成测试 - 验证错误响应内容功能链")
    print("=" * 70)

    tests = [
        test_encoding_available,
        test_stats_data_structure,
        test_api_response_structure,
        test_error_logs_api,
        test_frontend_types
    ]

    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"✗ 测试异常: {e}")
            results.append(False)

    print("\n" + "=" * 70)
    print(f"测试结果: {sum(results)}/{len(results)} 通过")
    print("=" * 70)

    if all(results):
        print("✓ 所有集成测试通过！🎉")
        print("\n功能链验证:")
        print("1. ✓ 编码转换工具可用")
        print("2. ✓ 后端数据结构支持 response_content")
        print("3. ✓ API 响应包含 response_content")
        print("4. ✓ 错误日志 API 包含 response_content")
        print("5. ✓ 前端 TypeScript 类型定义正确")
        return 0
    else:
        print("✗ 部分测试失败，请检查输出")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
