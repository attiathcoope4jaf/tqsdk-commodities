# tqsdk-commodities

> 基于 **TqSdk** 的商品期货策略集合，持续更新中。

## 项目简介

本仓库专注于**商品期货量化策略**，涵盖趋势跟踪、均值回归、突破策略、跨品种套利等方向。  
所有策略使用 [天勤量化 TqSdk](https://github.com/shinnytech/tqsdk-python) 实现，可直接对接实盘账户。

## 策略列表

| # | 策略名称 | 类型 | 品种 | 文件 |
|---|---------|------|------|------|
| 01 | 铜价趋势追踪策略 | 趋势跟踪 | SHFE.cu | [01_cu_trend_follow.py](strategies/01_cu_trend_follow.py) |
| 02 | 豆粕均值回归策略 | 均值回归 | DCE.m | [02_m_mean_reversion.py](strategies/02_m_mean_reversion.py) |
| 03 | 原油趋势追踪策略 | 趋势跟踪 | SC | [03_sc_trend.py](strategies/03_sc_trend.py) |
| 04 | 豆粕突破确认策略 | 突破策略 | DCE.m | [04_m_breakout.py](strategies/04_m_breakout.py) |
| 05 | 趋势跟踪：铜价三均线策略 | 趋势跟踪 | SHFE.cu | [05_cu_triple_ma.py](strategies/05_cu_triple_ma.py) |
| 06 | 区间震荡：白糖区间突破策略 | 区间震荡 | CZCE.sr | [06_sr_boll_breakout.py](strategies/06_sr_boll_breakout.py) |
| 07 | 趋势策略：棉花趋势跟踪策略 | 趋势跟踪 | CZCE.cf | [07_cf_trend_follow.py](strategies/07_cf_trend_follow.py) |
| 08 | 区间策略：玉米区间震荡策略 | 区间震荡 | DCE.c | [08_c_range.py](strategies/08_c_range.py) |
| 09 | 沪铜跨期趋势策略 | 跨期套利 | SHFE.cu | [09_cu_inter_temporal.py](strategies/09_cu_inter_temporal.py) |
| 10 | 农产品跨品种套利：豆油棕榈油价差 | 跨品种套利 | DCE.y + DCE.p | [10_y_p_spread.py](strategies/10_y_p_spread.py) |
| 11 | 白银均值回归策略 | 均值回归 | SHFE.ag | [11_ag_mean_reversion.py](strategies/11_ag_mean_reversion.py) |
| 12 | 原油多周期共振策略 | 多周期共振 | SC | [12_sc_multi_timeframe.py](strategies/12_sc_multi_timeframe.py) |
| 13 | 铝价布林带突破策略 | 布林带突破 | SHFE.al | [13_al_boll_breakout.py](strategies/13_al_boll_breakout.py) |
| 14 | 锌价高低点突破策略 | 突破策略 | SHFE.zn | [14_zn_breakout.py](strategies/14_zn_breakout.py) |
| 15 | 白糖期货布林带突破策略 | 布林带突破 | CZCE.sr | [15_sr_boll_band.py](strategies/15_sr_boll_band.py) |
| 16 | 棉花期货双均线交叉策略 | 均线交叉 | CZCE.cf | [16_cf_ma_crossover.py](strategies/16_cf_ma_crossover.py) |
| 17 | 铁矿石趋势布林策略 | 趋势跟踪 | DCE.i | [17_i_boll_trend.py](strategies/17_i_boll_trend.py) |
| 18 | 橡胶RSI超买超卖策略 | RSI策略 | SHFE.ru | [18_ru_rsi_strategy.py](strategies/18_ru_rsi_strategy.py) |
| 19 | 螺纹钢-热卷跨品种对冲策略 | 跨品种套利 | SHFE.rb + SHFE.hc | [19_rb_hc_spread.py](strategies/19_rb_hc_spread.py) |
| 20 | 橡胶期货多因子量化策略 | 多因子策略 | SHFE.ru | [20_ru_multi_factor.py](strategies/20_ru_multi_factor.py) |
| 21 | 螺纹钢-铁矿石跨品种对冲策略 | 跨品种套利 | SHFE.rb + DCE.i | [21_rb_i_spread.py](strategies/21_rb_i_spread.py) |
| 22 | 螺纹钢三因子趋势量化策略 | 多因子策略 | SHFE.rb | [22_rb_three_factor.py](strategies/22_rb_three_factor.py) |
| 23 | 螺纹钢多品种截面动量策略 | 截面动量 | 多品种 | [23_rb_cross_sectional_momentum.py](strategies/23_rb_cross_sectional_momentum.py) |
| 24 | 金属板块跨品种对冲策略 | 跨品种套利 | SHFE.cu + SHFE.al + SHFE.zn + SHFE.ni | [24_metal_hedge.py](strategies/24_metal_hedge.py) |
| 25 | 螺纹钢-热卷价差均值回归策略 | 均值回归 | SHFE.rb + SHFE.hc | [25_rb_hc_mean_reversion.py](strategies/25_rb_hc_mean_reversion.py) |
| 26 | 农产品板块多因子轮动策略 | 多因子策略 | DCE.m + DCE.c + CZCE.cf + CZCE.sr | [26_ag_sector_multi_factor.py](strategies/26_ag_sector_multi_factor.py) |
| 27 | 贵金属板块多因子策略 | 多因子策略 | SHFE.au + SHFE.ag | [26_commodity_multi_factor.py](strategies/26_commodity_multi_factor.py) |
| 28 | 原油系跨品种对冲日历价差策略 | 跨品种套利 | SHFE.sc + SHFE.bu + DCE.p | [27_cu_al_zn_calendar_spread.py](strategies/27_cu_al_zn_calendar_spread.py) |
| 29 | 农产品-软商品跨品种多因子轮动策略 | 多因子策略 | DCE.m + DCE.c + CZCE.SR + CZCE.CF | [29_agri_soft_multi_factor.py](strategies/29_agri_soft_multi_factor.py) |
| 30 | 黑色系产业链统计套利与趋势增强策略 | 统计套利 | SHFE.rb + SHFE.hc + DCE.i | [30_black_metals_stat_arb.py](strategies/30_black_metals_stat_arb.py) |

## 策略分类

### 📈 趋势跟踪（Trend Following）
基于均线、趋势线等技术指标捕捉价格趋势。

### 🔄 均值回归（Mean Reversion）
基于价格偏离均值后回归的特性进行交易。

### 💥 突破策略（Breakout）
基于价格突破关键位置进行交易。

### 🔀 跨品种套利（Cross-Commodity Arbitrage）
利用相关品种之间的价差关系进行套利。

### 🌊 多周期共振（Multi-Timeframe）
结合多个时间周期的信号提高策略稳定性。

### 🎯 多因子策略（Multi-Factor）
综合多个技术指标因子进行量化决策。

## 环境要求

```bash
pip install tqsdk numpy pandas ta-lib
```

## 使用说明

1. 替换代码中 `YOUR_ACCOUNT` / `YOUR_PASSWORD` 为你的天勤账号
2. 根据实际行情调整合约代码和参数
3. 建议先用模拟账户（`TqSim()`）回测后再上实盘

## 风险提示

- 商品期货杠杆较高，风险较大
- 请充分测试后再使用于实盘
- 本仓库策略仅供学习研究，不构成投资建议

---

**持续更新中，欢迎 Star ⭐ 关注**

*更新时间：2026-03-26*
