"""
================================================================================
TqSdk（天勤量化）简介
================================================================================
TqSdk 是由信易科技（Shinny Technologies）开发的专业期货量化交易 Python SDK。
它提供了完整的期货量化交易解决方案，支持实盘交易、模拟交易和历史回测三种模式，
无需切换代码即可在三种模式间自由切换，极大地降低了策略开发和验证的成本。

TqSdk 的核心特性：
1. 实时行情推送：基于 WebSocket 长连接，行情延迟低至毫秒级，覆盖国内所有主要
   期货交易所的全品种合约，包括 Tick、1分钟、5分钟、日线等多周期 K 线数据。
2. 同步式编程模型：TqSdk 采用同步阻塞式 API（wait_update）隐藏了底层的异步
   复杂性，用户无需掌握 asyncio 即可编写高效的事件驱动策略，大幅降低入门门槛。
3. 技术指标库（tafunc）：内置 MA、EMA、BOLL、MACD、RSI、ATR、KDJ 等数十种
   常用技术指标，计算结果与 tradingview / 同花顺 等主流平台保持一致。
4. 多账户支持：单个 TqApi 实例可同时管理多个交易账户（期货公司），适用于
   组合策略、风险对冲等复杂场景。
5. 回测精度高：回测引擎逐 Tick 回放历史数据，能准确模拟滑点、成交顺序等
   市场微观结构，回测结果可信度远高于基于 K 线收盘价的简单回测。
6. 持仓目标管理（TargetPosTask）：指定目标仓位后，SDK 自动完成从当前仓位
   到目标仓位的开平仓操作，并处理上期所"平今/平昨"规则差异，策略层无需
   关心具体的开平仓指令细节。
7. 完善的文档和社区：官方文档详尽，GitHub 社区活跃，提供大量示例策略，
   并有专属 QQ 群和论坛供用户交流经验。

官网：https://www.shinnytech.com/tianqin/
文档：https://doc.shinnytech.com/tqsdk/latest/

================================================================================
策略说明：02_m_mean_reversion — 豆粕期货布林带均值回归策略
================================================================================

【品种选择理由 — 为什么选豆粕（DCE.m）】
豆粕是大豆压榨的主要副产品，是国内养殖业最重要的蛋白饲料原料，市场需求
庞大且稳定。选择豆粕作为均值回归策略的标的，具有以下核心优势：

1. 成交量全球第一：大连商品交易所（DCE）豆粕期货长期占据全球农产品期货
   成交量榜首，日均成交额超过千亿元人民币，流动性极为充裕，极低的买卖价差
   使均值回归策略的成本控制成为可能。

2. 震荡属性突出：豆粕价格受季节性因素（南美大豆收割、国内消费旺季）影响
   显著，在非趋势期（约占全年 60%~70% 的时间）表现为典型的宽幅区间震荡，
   均值回归策略天然契合此类行情特征。

3. 基差规律性强：豆粕现货价格与期货价格的基差具有较强的均值回归特性，叠加
   月间价差的季节性规律，为统计套利和均值回归策略提供了丰富的信号来源。

4. 价格影响因素透明：美国大豆种植面积报告（USDA WASDE）、南美天气、人民币
   汇率、生猪存栏量等核心变量均可公开追踪，有助于策略研究者判断阶段性
   价格中枢的合理区间，从而更准确地捕捉均值回归时机。

5. 套保盘与投机盘并存：大型油厂和饲料企业的套保力量，与散户、机构投机盘
   形成博弈，使得价格在脱离基本面估值区间后往往迅速修复，天然支持均值回归
   的逻辑假设。

【策略逻辑 — 布林带均值回归（Bollinger Band Mean Reversion）】
布林带（Bollinger Bands）由约翰·布林格（John Bollinger）提出，由三条线组成：
- 中轨（Middle Band）：N 周期简单移动平均线，代表价格均值。
- 上轨（Upper Band） ：中轨 + K × N周期标准差，代表超买区域上边界。
- 下轨（Lower Band） ：中轨 - K × N周期标准差，代表超卖区域下边界。

均值回归假设：当价格偏离均值过远时（触及或突破上下轨），市场的自我修正
力量将推动价格重新向均值靠拢。

本策略具体规则：
- 做多条件：收盘价跌破布林带下轨，且 RSI 指标低于超卖阈值（默认 35），
  两重条件同时满足时开多仓，等待价格向中轨回归。
- 做空条件：收盘价突破布林带上轨，且 RSI 指标高于超买阈值（默认 65），
  两重条件同时满足时开空仓，等待价格向中轨回归。
- 止盈条件：价格回归至布林带中轨附近（±0.1×布林带宽度范围内）时平仓止盈。
- 止损条件：价格进一步向不利方向运动，超出 ATR 止损倍数时强制平仓，
  防止"均值回归"演变为"趋势单边行情"时的持续亏损。

【RSI 辅助过滤的意义】
单纯依赖价格触及布林带边界的信号，在强趋势行情中容易出现"越跌越买、
越涨越卖"的逆势亏损。引入 RSI 过滤条件，可有效区分：
- 真正的超卖/超买（RSI 配合偏极端值）→ 均值回归信号有效
- 趋势延续中的新高/新低（RSI 未达极端值）→ 过滤掉，避免逆势开仓

【参数说明】
- SYMBOL        : 合约代码（豆粕主力合约）
- BOLL_PERIOD   : 布林带计算周期，默认 20
- BOLL_K        : 布林带标准差倍数，默认 2.0
- RSI_PERIOD    : RSI 计算周期，默认 14
- RSI_OVERSOLD  : RSI 超卖阈值，默认 35（低于此值配合下轨开多）
- RSI_OVERBOUGHT: RSI 超买阈值，默认 65（高于此值配合上轨开空）
- ATR_PERIOD    : ATR 计算周期，默认 14
- ATR_STOP_MULT : 止损 ATR 倍数，默认 1.5（均值回归止损应收紧，避免大幅亏损）
- LOTS          : 单次开仓手数，默认 1

【风险提示】
期货交易具有较高风险，历史回测表现不代表未来实盘收益。
均值回归策略在强趋势行情中可能出现连续亏损，务必严格执行止损。
本策略仅供学习交流，不构成任何投资建议。请在充分了解风险后审慎使用。

作者：TqSdk 商品期货策略库
日期：2026-03-02
版本：v1.0
"""

# ==============================================================================
# 模块导入
# ==============================================================================
from tqsdk import TqApi, TqAuth, TqSim, TargetPosTask, BacktestFinished
from tqsdk.tafunc import boll, atr   # TqSdk 内置技术指标
import datetime
import logging

# ==============================================================================
# 日志配置
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("02_m_mean_reversion")

# ==============================================================================
# 策略参数配置
# ==============================================================================

# ---- 合约配置 ----------------------------------------------------------------
# 大连商品交易所豆粕主力合约（DCE.m2505 为示例，实盘请换成当月主力）
SYMBOL = "DCE.m2505"            # 目标合约代码

# ---- 布林带参数 --------------------------------------------------------------
BOLL_PERIOD = 20                 # 布林带均线周期，与经典参数一致
BOLL_K      = 2.0                # 标准差倍数，控制布林带宽度（2.0 覆盖约 95% 的价格分布）

# ---- RSI 参数 ----------------------------------------------------------------
RSI_PERIOD     = 14              # RSI 计算周期，参考 Wilder 原始设定
RSI_OVERSOLD   = 35              # RSI 超卖阈值：低于此值认为市场超卖，配合下轨开多
RSI_OVERBOUGHT = 65              # RSI 超买阈值：高于此值认为市场超买，配合上轨开空
# 注：传统阈值为 30/70，本策略适当收窄至 35/65，以减少噪音信号

# ---- ATR 止损参数 ------------------------------------------------------------
ATR_PERIOD    = 14               # ATR 计算周期
ATR_STOP_MULT = 1.5              # ATR 止损倍数（均值回归止损应比趋势策略更紧）

# ---- 仓位参数 ----------------------------------------------------------------
LOTS = 1                         # 单次开仓手数（每手豆粕 = 10 吨）

# ---- K线周期 -----------------------------------------------------------------
# 30分钟K线：豆粕日内波动频繁，30分钟周期能捕捉到足够的均值回归机会
KLINE_DURATION = 1800            # K线周期（秒），1800 = 30分钟

# ---- 止盈参数 ----------------------------------------------------------------
# 当价格回归至中轨附近时止盈，PROFIT_BAND_RATIO 控制"附近"的宽度
PROFIT_BAND_RATIO = 0.1          # 止盈触发范围 = ±0.1 × 布林带宽度（上轨-下轨）

# ---- 回测时间范围 ------------------------------------------------------------
BACKTEST_START = datetime.datetime(2024, 1, 1, 9, 0, 0)
BACKTEST_END   = datetime.datetime(2025, 12, 31, 15, 0, 0)


# ==============================================================================
# 辅助函数
# ==============================================================================

def compute_rsi(close_series, period):
    """
    手动计算 RSI 指标（Relative Strength Index，相对强弱指数）。

    RSI 的计算步骤：
    1. 计算每根 K 线的涨跌幅（close[i] - close[i-1]）
    2. 分别取正值（上涨幅度）和负值绝对值（下跌幅度）
    3. 以 SMA 方式平滑，得到平均上涨幅度（avg_gain）和平均下跌幅度（avg_loss）
    4. RSI = 100 - 100 / (1 + avg_gain / avg_loss)

    RSI 值域为 [0, 100]：
    - RSI > 70：超买区域，价格可能面临回调压力
    - RSI < 30：超卖区域，价格可能面临反弹支撑
    - RSI = 50：多空力量均衡

    参数：
        close_series : pandas Series，收盘价序列
        period       : int，RSI 计算周期（通常为 14）

    返回：
        float，最新一根 K 线的 RSI 值；数据不足时返回 None
    """
    if len(close_series) < period + 1:
        return None

    # 计算最近 period+1 根 K 线的涨跌幅
    closes = close_series.iloc[-(period + 1):]
    deltas = closes.diff().dropna()           # 去掉第一个 NaN

    gains  = deltas.clip(lower=0)             # 只保留正值（上涨幅度）
    losses = (-deltas).clip(lower=0)          # 只保留负值的绝对值（下跌幅度）

    avg_gain = gains.mean()                   # 平均上涨幅度（简单平均）
    avg_loss = losses.mean()                  # 平均下跌幅度（简单平均）

    if avg_loss == 0:
        return 100.0                          # 没有下跌，RSI = 100（完全强势）

    rs        = avg_gain / avg_loss
    rsi_value = 100.0 - (100.0 / (1.0 + rs))
    return rsi_value


def is_near_middle_band(price, upper, lower, ratio=0.1):
    """
    判断价格是否接近布林带中轨（止盈逻辑辅助函数）。

    策略中的"接近中轨"定义为：
        中轨 - ratio × 带宽  <=  price  <=  中轨 + ratio × 带宽
    其中带宽 = 上轨 - 下轨，中轨 = (上轨 + 下轨) / 2。

    参数：
        price : float，当前价格
        upper : float，布林带上轨
        lower : float，布林带下轨
        ratio : float，允许偏离中轨的比例（相对于带宽）

    返回：
        bool，True 表示价格在中轨附近
    """
    band_width = upper - lower
    middle     = (upper + lower) / 2.0
    threshold  = ratio * band_width
    return (middle - threshold) <= price <= (middle + threshold)


# ==============================================================================
# 核心策略函数
# ==============================================================================

def run_strategy():
    """
    豆粕布林带均值回归策略主函数。

    策略的核心逻辑是：
    1. 价格过度偏离均值（突破布林带边界）→ 认为市场短期过度反应
    2. RSI 确认超买/超卖状态 → 过滤掉趋势性突破，只保留均值回归信号
    3. 价格回归至中轨附近 → 获利了结
    4. 价格继续向不利方向运动超过 ATR 止损距离 → 强制止损，控制单笔亏损
    """

    # --------------------------------------------------------------------------
    # 1. 初始化 TqApi（模拟盘模式）
    # 实盘时替换为 TqAuth("天勤账号", "密码") 并传入真实账户对象
    # --------------------------------------------------------------------------
    api = TqApi(TqSim(), auth=TqAuth("your_account", "your_password"))
    logger.info(f"TqApi 初始化完成，目标合约：{SYMBOL}")

    try:
        # ----------------------------------------------------------------------
        # 2. 订阅行情数据
        # 订阅 30 分钟 K 线，数据长度 200 根，覆盖约 4 个月的 30 分钟 K 线数据，
        # 足够支撑布林带（20 周期）和 RSI（14 周期）等指标的计算。
        # ----------------------------------------------------------------------
        klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=200)
        logger.info(f"K线订阅成功，周期：{KLINE_DURATION}秒（30分钟），数据长度：200根")

        # ----------------------------------------------------------------------
        # 3. 获取账户和持仓信息
        # ----------------------------------------------------------------------
        account  = api.get_account()
        position = api.get_position(SYMBOL)

        # ----------------------------------------------------------------------
        # 4. 初始化目标仓位任务（TargetPosTask）
        # TargetPosTask 会自动处理开平仓方向，策略层只需调用 set_target_volume()
        # 指定目标净仓位即可，正数为多仓，负数为空仓，0 为空仓（清仓）。
        # ----------------------------------------------------------------------
        target_pos = TargetPosTask(api, SYMBOL)
        logger.info("TargetPosTask 初始化完成")

        # ----------------------------------------------------------------------
        # 5. 状态变量
        # current_direction : 当前持仓方向（"long" / "short" / "flat"）
        # entry_price       : 入场价格，用于计算止损价
        # stop_loss_price   : ATR 止损价格
        # entry_upper/lower : 开仓时的布林带上下轨，用于止盈判断
        # ----------------------------------------------------------------------
        current_direction = "flat"
        entry_price       = 0.0
        stop_loss_price   = 0.0
        entry_upper       = 0.0
        entry_lower       = 0.0

        logger.info("策略开始运行，等待数据更新...")

        # ----------------------------------------------------------------------
        # 6. 主事件循环
        # api.wait_update() 是事件驱动的核心：每次有行情、账户或订单更新时返回。
        # is_changing() 检查指定字段是否在本次 wait_update 中发生变化。
        # ----------------------------------------------------------------------
        while api.wait_update():

            # ------------------------------------------------------------------
            # 6.1 只在 K 线完成（新 K 线生成）时执行策略逻辑
            # 使用最新完成 K 线（iloc[-2]，index -1 为实时未完成的当前 K 线）的
            # 数据进行计算，避免使用未完成 K 线造成信号频繁变化。
            # 注：部分策略选择 iloc[-1]（实时），本策略选择 iloc[-2]（已完成）以
            # 保证信号稳定性，这是均值回归策略的常见做法。
            # ------------------------------------------------------------------
            if not api.is_changing(klines.iloc[-1], "datetime"):
                continue

            # ------------------------------------------------------------------
            # 6.2 计算布林带
            # TqSdk tafunc.boll() 返回包含 "upper"、"middle"、"lower" 三列的
            # DataFrame，与 klines 等长。
            # ------------------------------------------------------------------
            close_series = klines["close"]
            boll_df      = boll(close_series, BOLL_PERIOD, BOLL_K)

            # 取最新已完成 K 线的布林带值（iloc[-2] 为最新已完成 K 线）
            upper_cur  = boll_df["upper"].iloc[-2]
            middle_cur = boll_df["middle"].iloc[-2]
            lower_cur  = boll_df["lower"].iloc[-2]
            close_cur  = close_series.iloc[-2]   # 最新已完成 K 线收盘价

            # 计算 ATR（使用全部 klines 数据）
            atr_df  = atr(klines, ATR_PERIOD)
            atr_cur = atr_df.iloc[-2]            # 最新已完成 K 线的 ATR 值

            # 计算 RSI（使用手动实现）
            rsi_value = compute_rsi(close_series, RSI_PERIOD)

            # ------------------------------------------------------------------
            # 6.3 数据有效性检查
            # 布林带和 RSI 需要足够多的历史 K 线才能正确计算，
            # 若数据不足则跳过本轮，避免使用 NaN 数据触发错误信号。
            # ------------------------------------------------------------------
            if (
                upper_cur != upper_cur or    # NaN 检查（NaN != NaN 为 True）
                lower_cur != lower_cur or
                atr_cur   != atr_cur or
                rsi_value is None
            ):
                logger.debug("指标数据不足，跳过本轮计算")
                continue

            logger.debug(
                f"收盘：{close_cur:.0f} | "
                f"布林上：{upper_cur:.0f} | 中：{middle_cur:.0f} | 下：{lower_cur:.0f} | "
                f"RSI：{rsi_value:.1f} | ATR：{atr_cur:.0f} | 方向：{current_direction}"
            )

            # ------------------------------------------------------------------
            # 6.4 止损检查（优先于开仓信号）
            # 均值回归策略的止损逻辑：
            # - 多仓：价格继续下跌超过止损价 → 市场从超卖变为趋势下跌 → 止损
            # - 空仓：价格继续上涨超过止损价 → 市场从超买变为趋势上涨 → 止损
            # ------------------------------------------------------------------
            if current_direction == "long" and close_cur <= stop_loss_price:
                logger.warning(
                    f"多仓止损触发！入场价：{entry_price:.0f}，"
                    f"当前价：{close_cur:.0f}，止损价：{stop_loss_price:.0f}"
                )
                target_pos.set_target_volume(0)
                current_direction = "flat"
                entry_price = stop_loss_price = 0.0
                entry_upper = entry_lower = 0.0

            elif current_direction == "short" and close_cur >= stop_loss_price:
                logger.warning(
                    f"空仓止损触发！入场价：{entry_price:.0f}，"
                    f"当前价：{close_cur:.0f}，止损价：{stop_loss_price:.0f}"
                )
                target_pos.set_target_volume(0)
                current_direction = "flat"
                entry_price = stop_loss_price = 0.0
                entry_upper = entry_lower = 0.0

            # ------------------------------------------------------------------
            # 6.5 止盈检查
            # 当持仓且价格回归至中轨附近时，触发止盈平仓。
            # 使用开仓时的布林带（entry_upper / entry_lower）而非实时布林带，
            # 保证止盈目标价格的稳定性（避免布林带随时间移动导致止盈逻辑紊乱）。
            # ------------------------------------------------------------------
            if current_direction in ("long", "short"):
                if is_near_middle_band(close_cur, entry_upper, entry_lower, PROFIT_BAND_RATIO):
                    profit = (
                        (close_cur - entry_price) * LOTS * 10
                        if current_direction == "long"
                        else (entry_price - close_cur) * LOTS * 10
                    )
                    logger.info(
                        f"价格回归中轨，止盈平仓！方向：{current_direction} | "
                        f"入场价：{entry_price:.0f} | 当前价：{close_cur:.0f} | "
                        f"预估盈亏：{profit:+.0f} 元"
                    )
                    target_pos.set_target_volume(0)
                    current_direction = "flat"
                    entry_price = stop_loss_price = 0.0
                    entry_upper = entry_lower = 0.0
                    continue   # 本轮不再判断开仓信号

            # ------------------------------------------------------------------
            # 6.6 开仓信号判断
            # 满足以下所有条件时才触发开仓，双重过滤避免频繁交易：
            # 开多：① 收盘价 < 下轨（价格超卖）  ② RSI < 超卖阈值（动能确认）
            # 开空：① 收盘价 > 上轨（价格超买）  ② RSI > 超买阈值（动能确认）
            # ------------------------------------------------------------------
            if current_direction == "flat":

                # ---- 做多条件 ------------------------------------------------
                if close_cur < lower_cur and rsi_value < RSI_OVERSOLD:
                    entry_price       = close_cur
                    stop_loss_price   = close_cur - ATR_STOP_MULT * atr_cur  # 止损：进一步下跌
                    entry_upper       = upper_cur
                    entry_lower       = lower_cur
                    target_pos.set_target_volume(LOTS)
                    current_direction = "long"
                    logger.info(
                        f"均值回归做多信号！收盘价：{close_cur:.0f} < 下轨：{lower_cur:.0f} | "
                        f"RSI：{rsi_value:.1f} < {RSI_OVERSOLD} | "
                        f"止损价：{stop_loss_price:.0f} | ATR：{atr_cur:.0f} | "
                        f"目标中轨：{middle_cur:.0f}"
                    )

                # ---- 做空条件 ------------------------------------------------
                elif close_cur > upper_cur and rsi_value > RSI_OVERBOUGHT:
                    entry_price       = close_cur
                    stop_loss_price   = close_cur + ATR_STOP_MULT * atr_cur  # 止损：进一步上涨
                    entry_upper       = upper_cur
                    entry_lower       = lower_cur
                    target_pos.set_target_volume(-LOTS)
                    current_direction = "short"
                    logger.info(
                        f"均值回归做空信号！收盘价：{close_cur:.0f} > 上轨：{upper_cur:.0f} | "
                        f"RSI：{rsi_value:.1f} > {RSI_OVERBOUGHT} | "
                        f"止损价：{stop_loss_price:.0f} | ATR：{atr_cur:.0f} | "
                        f"目标中轨：{middle_cur:.0f}"
                    )

            # ------------------------------------------------------------------
            # 6.7 账户状态日志（每根 K 线完成后打印，用于监控）
            # ------------------------------------------------------------------
            logger.info(
                f"账户权益：{account.balance:,.0f} | "
                f"可用资金：{account.available:,.0f} | "
                f"持仓净量：{position.pos} 手 | "
                f"当前方向：{current_direction}"
            )

    except BacktestFinished:
        # 回测模式下数据耗尽，属于正常结束
        logger.info("回测完成！")

    except KeyboardInterrupt:
        logger.info("策略被手动停止（Ctrl+C）")

    finally:
        # 关闭 API 连接，释放资源
        api.close()
        logger.info("TqApi 连接已关闭，策略退出")


# ==============================================================================
# 入口
# ==============================================================================
if __name__ == "__main__":
    logger.info("=" * 65)
    logger.info("豆粕期货布林带均值回归策略启动")
    logger.info(f"合约：{SYMBOL}")
    logger.info(f"布林带周期：{BOLL_PERIOD} | K 倍数：{BOLL_K}")
    logger.info(f"RSI 周期：{RSI_PERIOD} | 超卖阈值：{RSI_OVERSOLD} | 超买阈值：{RSI_OVERBOUGHT}")
    logger.info(f"ATR 周期：{ATR_PERIOD} | 止损倍数：{ATR_STOP_MULT}")
    logger.info(f"K线周期：{KLINE_DURATION}秒 | 开仓手数：{LOTS}")
    logger.info("=" * 65)