"""calc 工具的 8 条测试用例（等价类 + 边界值 + 异常路径）。

用法：python -m pytest tests/test_calc_cases.py -v
每条用例对应 docs/calc-测试用例.md 表格里的一行。
"""

import json

import pytest

from agent.tools import ToolError, builtin_registry


@pytest.fixture()
def registry():
    return builtin_registry()


# 用例 1：正常路径——带括号的四则运算
def test_case01_normal_expression(registry):
    result = registry.call("calc", {"expression": "12*(3+4)"})
    assert "84" in result


# 用例 2：等价类——表达式前后有空格，应当仍能计算
def test_case02_spaces_around_expression(registry):
    result = registry.call("calc", {"expression": " 1 + 2 "})
    assert '"value": 3' in result


# 用例 3：边界值——负数运算
def test_case03_negative_number(registry):
    result = registry.call("calc", {"expression": "-3*2"})
    assert '"value": -6' in result


# 用例 4：异常路径——除数为 0
def test_case04_division_by_zero(registry):
    with pytest.raises(ToolError) as excinfo:
        registry.call("calc", {"expression": "1/0"})
    assert "division by zero" in str(excinfo.value)


# 用例 5：异常路径——表达式里混入字母（非法字符白名单）
def test_case05_illegal_character(registry):
    with pytest.raises(ToolError) as excinfo:
        registry.call("calc", {"expression": "1+a"})
    assert "only digits" in str(excinfo.value)


# 用例 6：异常路径——括号不匹配（语法错误）
def test_case06_unbalanced_parentheses(registry):
    with pytest.raises(ToolError) as excinfo:
        registry.call("calc", {"expression": "12*(3+4"})
    assert "cannot evaluate" in str(excinfo.value)


# 用例 7：异常路径——空表达式
def test_case07_empty_expression(registry):
    with pytest.raises(ToolError):
        registry.call("calc", {"expression": ""})


# 用例 8：异常路径——不传必填参数
def test_case08_missing_argument(registry):
    with pytest.raises(ToolError) as excinfo:
        registry.call("calc", {})
    assert "missing required argument" in str(excinfo.value)


# 缺陷用例：浮点精度（BUG-001，见 docs/calc-测试用例.md）
# 期望 0.3，实际返回 0.30000000000000004。先标 xfail 记录事实，不阻断 CI。
@pytest.mark.xfail(reason="BUG-001: 浮点精度未处理，0.1+0.2 返回 0.30000000000000004", strict=True)
def test_case09_float_precision(registry):
    result = json.loads(registry.call("calc", {"expression": "0.1+0.2"}))
    assert result["value"] == 0.3
