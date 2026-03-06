# tqsdk-commodities

> 基于 **TqSdk** 的商品期货专项策略，持续更新中。

## 项目简介

本仓库专注于**商品期货量化策略**，涵盖金属、能源、农产品等品种。  
所有策略使用 [天勤量化 TqSdk](https://github.com/shinnytech/tqsdk-python) 实现。

## 策略列表

| # | 策略名称 | 类型 | 品种 | 文件 |
|---|---------|------|------|------|
| 01 | 沪铜趋势追踪策略 | 趋势跟踪 | SHFE.cu | [01_cu_trend_follow.py](strategies/01_cu_trend_follow.py) |
| 02 | 豆粕均值回归策略 | 均值回归 | DCE.m | [02_m_mean_reversion.py](strategies/02_m_mean_reversion.py) |
| 03 | 原油趋势追踪策略 | 趋势跟踪 | SC | [03_sc_trend.py](strategies/03_sc_trend.py) |
| 04 | 豆粕突破确认策略 | 突破策略 | DCE.m | [04_m_breakout.py](strategies/04_m_breakout.py) |

## 更新日志

- 2026-03-03: 新增策略03（原油趋势）、策略04（豆粕突破确认）
