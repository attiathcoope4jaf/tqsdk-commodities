#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 22
策略名称: 螺纹钢三因子趋势量化策略
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

本策略是一个多因子量化策略，综合考虑三个技术因子来判断趋势方向：

1. 移动平均线因子（MA）：价格站上20日均线上看多，跌破则看空
2. 动量因子（Momentum）：20日动量为正看多，为负看空  
3. 布林带因子（Bollinger Bands）：价格处于布林带中轨上方看多，下方看空

策略规则：
- 三个因子中有至少2个看多时，做多
- 三个因子中有至少2个看空时，做空
- 持仓过程中如信号消失，平仓

【策略参数】

| 参数 | 默认值 | 说明 |
|------|--------|------|
| SYMBOL | SHFE.rb2510 | 螺纹钢主力合约 |
| MA_PERIOD | 20 | 均线周期 |
| MOMENTUM_PERIOD | 20 | 动量周期 |
| BB_PERIOD | 20 | 布林带周期 |
| BB_STD | 2 | 布林带标准差倍数 |
| LOT_SIZE | 1 | 单次开仓手数 |

【风险提示】

- 多因子策略需要确保各因子权重合理
- 市场剧烈波动时可能导致信号频繁变化
- 期货交易存在较高风险，请充分测试后再用于实盘
================================================================================
"""

from tqsdk import TqApi, TqAuth, TqSim
import pandas as pd
import numpy as np
from collections import deque

# ============ 参数配置 ============
SYMBOL = "SHFE.rb2510"          # 螺纹钢主力合约
KLINE_DURATION = 60 * 60        # 1小时K线
MA_PERIOD = 20                  # 均线周期
MOMENTUM_PERIOD = 20            # 动量周期
BB_PERIOD = 20                  # 布林带周期
BB_STD = 2                      # 布林带标准差倍数
LOT_SIZE = 1                    # 开仓手数


class ThreeFactorStrategy:
    def __init__(self, api):
        self.api = api
        self.klines = deque(maxlen=100)
        self.position = 0  # 1: 多头, -1: 空头, 0: 空仓
        
    def get_klines(self, count=50):
        """获取K线数据"""
        klines = self.api.get_kline_serial(SYMBOL, KLINE_DURATION, count)
        return klines
    
    def calculate_ma_factor(self, df):
        """计算均线因子：价格站上均线看多"""
        df['ma'] = df['close'].rolling(window=MA_PERIOD).mean()
        if pd.isna(df['ma'].iloc[-1]):
            return 0
        return 1 if df['close'].iloc[-1] > df['ma'].iloc[-1] else -1
    
    def calculate_momentum_factor(self, df):
        """计算动量因子：20日动量为正看多"""
        if len(df) < MOMENTUM_PERIOD + 1:
            return 0
        momentum = df['close'].iloc[-1] - df['close'].iloc[-MOMENTUM_PERIOD]
        return 1 if momentum > 0 else -1
    
    def calculate_bb_factor(self, df):
        """计算布林带因子：价格处于中轨上方看多"""
        df['bb_mid'] = df['close'].rolling(window=BB_PERIOD).mean()
        df['bb_std'] = df['close'].rolling(window=BB_PERIOD).std()
        df['bb_upper'] = df['bb_mid'] + BB_STD * df['bb_std']
        df['bb_lower'] = df['bb_mid'] - BB_STD * df['bb_std']
        
        if pd.isna(df['bb_mid'].iloc[-1]):
            return 0
        
        close = df['close'].iloc[-1]
        if close > df['bb_mid'].iloc[-1]:
            return 1
        elif close < df['bb_mid'].iloc[-1]:
            return -1
        return 0
    
    def calculate_signals(self, df):
        """计算各因子信号"""
        ma_factor = self.calculate_ma_factor(df)
        momentum_factor = self.calculate_momentum_factor(df)
        bb_factor = self.calculate_bb_factor(df)
        
        # 统计信号
        signals = [ma_factor, momentum_factor, bb_factor]
        long_signals = sum(1 for s in signals if s > 0)
        short_signals = sum(1 for s in signals if s < 0)
        
        return ma_factor, momentum_factor, bb_factor, long_signals, short_signals
    
    def update_position(self, long_signals, short_signals):
        """更新仓位"""
        if self.position == 0:
            if long_signals >= 2:
                self.position = 1
                print(f"开多仓: {long_signals}个因子看多")
            elif short_signals >= 2:
                self.position = -1
                print(f"开空仓: {short_signals}个因子看空")
        elif self.position == 1 and short_signals >= 2:
            self.position = 0
            print("平多仓: 转空信号")
        elif self.position == -1 and long_signals >= 2:
            self.position = 0
            print("平空仓: 转多信号")
    
    def execute_orders(self):
        """执行下单"""
        try:
            positions = self.api.get_position(SYMBOL)
            
            if self.position == 1 and positions.pos_long == 0:
                # 开多
                self.api.insert_order(
                    symbol=SYMBOL,
                    direction="BUY",
                    offset="OPEN",
                    volume=LOT_SIZE
                )
            elif self.position == -1 and positions.pos_short == 0:
                # 开空
                self.api.insert_order(
                    symbol=SYMBOL,
                    direction="SELL",
                    offset="OPEN",
                    volume=LOT_SIZE
                )
            elif self.position == 0:
                # 平仓
                if positions.pos_long > 0:
                    self.api.insert_order(
                        symbol=SYMBOL,
                        direction="SELL",
                        offset="CLOSE",
                        volume=positions.pos_long
                    )
                if positions.pos_short > 0:
                    self.api.insert_order(
                        symbol=SYMBOL,
                        direction="BUY",
                        offset="CLOSE",
                        volume=positions.pos_short
                    )
        except Exception as e:
            print(f"下单错误: {e}")
    
    def run(self):
        """运行策略"""
        print("三因子趋势策略启动")
        
        # 订阅行情
        self.api.subscribe([SYMBOL])
        
        # 预热数据
        klines = self.get_klines(100)
        
        while True:
            self.api.wait_update()
            klines = self.get_klines(100)
            
            if len(klines) < BB_PERIOD + 1:
                continue
            
            df = pd.DataFrame({
                'open': klines['open'],
                'high': klines['high'],
                'low': klines['low'],
                'close': klines['close'],
                'volume': klines['volume']
            })
            
            ma_f, mom_f, bb_f, long_s, short_s = self.calculate_signals(df)
            
            print(f"MA因子: {ma_f}, 动量因子: {mom_f}, BB因子: {bb_f}")
            print(f"多信号: {long_s}, 空信号: {short_s}, 当前持仓: {self.position}")
            
            self.update_position(long_s, short_s)
            self.execute_orders()


def main():
    # 使用模拟账户
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    try:
        strategy = ThreeFactorStrategy(api)
        strategy.run()
    except KeyboardInterrupt:
        print("策略停止")
    finally:
        api.close()


if __name__ == "__main__":
    main()
