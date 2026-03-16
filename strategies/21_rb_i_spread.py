#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 21
策略名称: 螺纹钢-铁矿石跨品种对冲策略
生成日期: 2026-03-16
仓库地址: tqsdk-commodities
================================================================================

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【TqSdk 简介】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TqSdk（天勤量化 SDK）是由信易科技（北京）有限公司开发的专业期货量化交易框架，
完全免费开源（Apache 2.0 协议），基于 Python 语言设计，支持 Python 3.6+ 环境。
TqSdk 已服务于数万名国内期货量化投资者，是国内使用最广泛的期货量化框架之一。

TqSdk 核心能力包括：

1. **统一行情接口**：对接国内全部7大期货交易所（SHFE/DCE/CZCE/CFFEX/INE/GFEX）
   及主要期权品种，统一的 get_quote / get_kline_serial 接口，告别繁琐的协议适配；

2. **高性能数据推送**：天勤服务器行情推送延迟通常在5ms以内，Tick 级数据实时到达，
   K线自动合并，支持自定义周期（秒/分钟/小时/日/周/月）；

3. **同步式编程范式**：独特的 wait_update() + is_changing() 设计，策略代码像
   写普通Python一样自然流畅，无需掌握异步编程，大幅降低开发门槛；

4. **完整回测引擎**：内置 TqBacktest 回测模式，历史数据精确到Tick级别，
   支持滑点、手续费等真实市场参数，回测结果可信度高；

5. **实盘/模拟一键切换**：代码结构不变，仅替换 TqApi 初始化参数即可从
   模拟盘切换至实盘，极大降低策略上线风险；

6. **多账户并发**：支持同时连接多个期货账户，适合机构投资者和量化团队；

7. **活跃生态**：官方提供策略示例库、在线文档、量化社区论坛，更新维护活跃。

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
GitHub: https://github.com/shinnytech/tqsdk-python
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】

本策略是基于螺纹钢与铁矿石的跨品种对冲策略。铁矿石是螺纹钢的主要上游原材料，
两者价格具有高度相关性。当价差偏离历史均值时，预期价差会回归，从而实现套利。

策略逻辑：
1. 选取螺纹钢（RB）和铁矿石（I）作为交易标的
2. 计算两者价格的价差（spread = RB - k * I，k为对冲比率）
3. 统计过去N日的价差均值和标准差
4. 当价差突破均值+1.5倍标准差时，做空价差（空RB，多I）
5. 当价差跌破均值-1.5倍标准差时，做多价差（多RB，空I）
6. 价差回归均值时平仓

【策略参数】

| 参数 | 默认值 | 说明 |
|------|--------|------|
| SYMBOL_RB | SHFE.rb2510 | 螺纹钢合约 |
| SYMBOL_I | DCE.i2510 | 铁矿石合约 |
| LOOKBACK_PERIOD | 20 | 统计周期（交易日） |
| ENTRY_THRESHOLD | 1.5 | 入场阈值（标准差倍数） |
| EXIT_THRESHOLD | 0.5 | 出场阈值（标准差倍数） |
| HEDGE_RATIO | 0.15 | 对冲比率（铁矿石/螺纹钢） |
| LOT_SIZE | 1 | 单次开仓手数 |

【风险提示】

- 跨品种套利需要关注两个品种的流动性差异
- 价差可能长时间不回归，需做好资金管理
- 期货交易存在较高风险，请充分测试后再用于实盘
================================================================================
"""

from tqsdk import TqApi, TqAuth, TqSim
import pandas as pd
import numpy as np
from collections import deque

# ============ 参数配置 ============
SYMBOL_RB = "SHFE.rb2510"       # 螺纹钢主力合约
SYMBOL_I = "DCE.i2510"         # 铁矿石主力合约
LOOKBACK_PERIOD = 20            # 统计周期
ENTRY_THRESHOLD = 1.5           # 入场阈值（标准差倍数）
EXIT_THRESHOLD = 0.5           # 出场阈值
HEDGE_RATIO = 0.15              # 对冲比率
LOT_SIZE = 1                    # 开仓手数
KLINE_DURATION = 60 * 60       # 1小时K线


class SpreadStrategy:
    def __init__(self, api):
        self.api = api
        self.spread_history = deque(maxlen=LOOKBACK_PERIOD)
        self.position = 0  # 1: 多价差, -1: 空价差, 0: 空仓
        self.rb_pos = 0
        self.i_pos = 0
        
    def get_spread(self):
        """获取当前价差"""
        rb_quote = self.api.get_quote(SYMBOL_RB)
        i_quote = self.api.get_quote(SYMBOL_I)
        rb_price = rb_quote.last_price
        i_price = i_quote.last_price
        # 价差 = RB - k * I
        spread = rb_price - HEDGE_RATIO * i_price
        return spread, rb_price, i_price
    
    def calculate_stats(self):
        """计算价差统计特征"""
        if len(self.spread_history) < LOOKBACK_PERIOD:
            return None, None
        
        spreads = list(self.spread_history)
        mean = np.mean(spreads)
        std = np.std(spreads)
        return mean, std
    
    def update_position(self, spread):
        """更新仓位"""
        if len(self.spread_history) < LOOKBACK_PERIOD:
            return
        
        mean, std = self.calculate_stats()
        if std == 0:
            return
        
        z_score = (spread - mean) / std
        
        # 入场逻辑
        if self.position == 0:
            if z_score > ENTRY_THRESHOLD:
                # 价差偏高，做空价差：空RB，多I
                self.rb_pos = -LOT_SIZE
                self.i_pos = LOT_SIZE
                self.position = -1
                print(f"做空价差: z={z_score:.2f}, spread={spread:.2f}")
            elif z_score < -ENTRY_THRESHOLD:
                # 价差偏低，做多价差：多RB，空I
                self.rb_pos = LOT_SIZE
                self.i_pos = -LOT_SIZE
                self.position = 1
                print(f"做多价差: z={z_score:.2f}, spread={spread:.2f}")
        
        # 出场逻辑
        elif self.position == 1 and z_score > -EXIT_THRESHOLD:
            # 多价差仓位平仓
            self.rb_pos = 0
            self.i_pos = 0
            self.position = 0
            print(f"平多仓: z={z_score:.2f}")
        elif self.position == -1 and z_score < EXIT_THRESHOLD:
            # 空价差仓位平仓
            self.rb_pos = 0
            self.i_pos = 0
            self.position = 0
            print(f"平空仓: z={z_score:.2f}")
    
    def execute_orders(self):
        """执行下单"""
        try:
            # 螺纹钢下单
            if self.rb_pos != 0:
                order_rb = self.api.insert_order(
                    symbol=SYMBOL_RB,
                    direction="BUY" if self.rb_pos > 0 else "SELL",
                    offset="OPEN",
                    volume=abs(self.rb_pos)
                )
            else:
                # 平仓
                positions = self.api.get_position(SYMBOL_RB)
                if positions.pos_long > 0:
                    self.api.insert_order(
                        symbol=SYMBOL_RB,
                        direction="SELL",
                        offset="CLOSE",
                        volume=positions.pos_long
                    )
                elif positions.pos_short > 0:
                    self.api.insert_order(
                        symbol=SYMBOL_RB,
                        direction="BUY",
                        offset="CLOSE",
                        volume=positions.pos_short
                    )
            
            # 铁矿石下单
            if self.i_pos != 0:
                order_i = self.api.insert_order(
                    symbol=SYMBOL_I,
                    direction="BUY" if self.i_pos > 0 else "SELL",
                    offset="OPEN",
                    volume=abs(self.i_pos)
                )
            else:
                positions = self.api.get_position(SYMBOL_I)
                if positions.pos_long > 0:
                    self.api.insert_order(
                        symbol=SYMBOL_I,
                        direction="SELL",
                        offset="CLOSE",
                        volume=positions.pos_long
                    )
                elif positions.pos_short > 0:
                    self.api.insert_order(
                        symbol=SYMBOL_I,
                        direction="BUY",
                        offset="CLOSE",
                        volume=positions.pos_short
                    )
        except Exception as e:
            print(f"下单错误: {e}")
    
    def run(self):
        """运行策略"""
        print("跨品种对冲策略启动")
        
        # 订阅行情
        self.api.subscribe([SYMBOL_RB, SYMBOL_I])
        
        # 预热数据
        for _ in range(LOOKBACK_PERIOD):
            self.api.wait_update()
            spread, _, _ = self.get_spread()
            self.spread_history.append(spread)
        
        print(f"预热完成，当前价差: {list(self.spread_history)[-1]:.2f}")
        
        while True:
            self.api.wait_update()
            spread, rb_price, i_price = self.get_spread()
            self.spread_history.append(spread)
            
            print(f"RB: {rb_price:.2f}, I: {i_price:.2f}, Spread: {spread:.2f}")
            
            self.update_position(spread)
            self.execute_orders()


def main():
    # 使用模拟账户
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    try:
        strategy = SpreadStrategy(api)
        strategy.run()
    except KeyboardInterrupt:
        print("策略停止")
    finally:
        api.close()


if __name__ == "__main__":
    main()
