# 多交易所多账户 Telegram 下单面板

基于 python-telegram-bot、Binance 官方 API 和 OKX 官方 API 构建的轻量级 Telegram 手动下单面板，支持 Binance 和 OKX 的现货与合约交易，支持多账户管理。

## 🌟 核心新功能

- ⚡️ **全菜单化操作**: 无需记忆繁琐命令，通过 Inline Keyboard 一键切换账户、模式及下单。
- 💰 **USDT 本位下单**: 自动识别金额模式（如 `100u`），自动计算下单数量。
- 🔄 **多账户管理**: 支持多交易所、多子账户管理，通过 `sub1`, `sub2` 排序，支持备注（如邮箱）。
- 📉 **多市场支持**: 现货与合约无缝切换。
- 🛡 **保证金模式切换**: 合约模式下支持一键切换 **全仓 (Cross)** 或 **逐仓 (Isolated)**。
- 🎯 **止盈止损 (TP/SL)**: 下单时支持可选的 `tp` 和 `sl` 参数，采用 **Binance 2026 最新 Algo API**。
- 📋 **查询挂单**: 实时查看当前所有未成交订单，精准显示止盈/止损触发价及触发条件（如 Mark Price）。
- ## 🧪 测试网支持与注意事项

### **1. Binance 测试网**
- 需在 [Binance Futures Testnet](https://testnet.binancefuture.com/) 申请 API Key。
- 配置中设置 `testnet: true`。

### **2. OKX 模拟盘 (极其重要)**
- **API Key 类型**: OKX 的模拟盘与实盘 API Key 是**完全隔离**的。
- **申请路径**: 登录 OKX 官网 -> 资产管理 -> **开始模拟交易** -> 侧边栏 API -> 创建模拟盘 API Key。
- **注意**: 
  - **严禁**使用实盘 API Key 配合 `testnet: true`，否则会触发 `50038` 错误。
  - 必须在网页端至少进入一次“模拟交易”页面以激活账户。
  - 本 Bot 已自动处理模拟盘所需的 `x-simulated-trading` Header。

## 🌐 代理支持
- **本地测试**: 建议在 `config.yaml` 中设置 `proxy.port: 7897` (以 Clash 为例)。
- **服务器部署**: 若服务器在海外，请将 `port` 留空。

## 🎮 使用指南

### 📱 菜单模式 (推荐)
- 发送 `/start` 或 `/menu` 唤起主面板。
- **⚡️ 快捷下单**: 快速选择币种和金额下单。
- **📋 查询挂单**: 查看活跃的 TP/SL 单及普通限价单，精准抓取触发价。
- **� 撤销全部**: 一键清理当前账户下所有挂单（含 Algo 订单）。

### ⌨️ 命令行模式 (高级)
| 命令 | 说明 | 示例 | BN现货 | BN合约 | OKX现货 | OKX合约 |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| `/m` | 市价下单 | `/m buy ETH 500u` | ✅ | ✅ | ✅ | ✅ |
| `/l` | 限价下单 | `/l sell ETH 100u 3000` | ✅ | ✅ | ✅ | ✅ |
| `/tp` | 独立止盈 [--reduceonly] | `/tp sell BTC 0.05 75000` | ✅ | ✅ | ✅ | ✅ |
| `/sl` | 独立止损 [--reduceonly] | `/sl sell BTC 0.05 60000` | ✅ | ✅ | ✅ | ✅ |
| `/tpsl` | 双向止盈止损 [--reduceonly] | `/tpsl sell ETH 1 tp=3400 sl=2800`| ✅ | ✅ | ✅ | ✅ |
| `/ts` | 移动追踪止损 [--reduceonly] | `/ts sell ETH 1 0.01 px=3100` | ✅ | ✅ | ✅ | ✅ |
| `/order` | 查询当前挂单 | `/order` | ✅ | ✅ | ✅ | ✅ |
| `/order <ID>` | 订单底层溯源 | `/order 79373739` | ✅ | ✅ | ✅ | ✅ |
| `/balance` | 查询资产余额 | `/balance [币种]` | ✅ | ✅ | ✅ | ✅ |
| `/position` | 查询当前持仓 | `/position` | ✅(余额) | ✅ | ✅(余额) | ✅ |
| `/history` | 查询历史记录 | `/history` | ✅ | ✅ | ✅ | ✅ |
| `/cancel` | 智能撤单 | `/cancel <ALL\|币种\|ID>` | ✅ | ✅ | ✅ | ✅ |
| `/close` | 一键平仓（合约） | `/close eth` | — | ✅ | — | ✅ |
| `/margin` | 合约杠杆/保证金设置 | `/margin btc 5 isolated` | — | ✅ | — | ✅ |
| `/ctVal` | 合约面值查询（每张价值） | `/ctVal btc` | — | — | — | ✅ |
| `/posmode` | 查询/切换持仓模式 | `/posmode long_short_mode` | — | ✅ | — | ✅ |
| `/p` | 现货+合约双报价 | `/p btc` | ✅ | ✅ | ✅ | ✅ |

*注1：`/cancel` 支持极度智能的路由。输入纯数字如 `/cancel 18482` 走按 ID 撤单；输入 `/cancel BNB` 或 `/cancel BNB-USDT-SWAP` 走按交易对批量撤单。*

*注2：OKX 合约下单数量为**合约张数**，如 `/m buy btc 1` = 买入 1 张 BTC 合约（非 1 个 BTC）。每张价值可用 `/ctVal` 查询。*

*注3：`/tp` `/sl` `/tpsl` `/ts` 末尾加 `--reduceonly` 表示只减仓（不开新仓），不加则默认允许开新仓。*

## 🧩 止盈止损 (TP/SL) 实现机制

本项目深度适配了 **Binance 2026 年最新的 Algo Order API** 和 **OKX 原生策略委托**：

1. **针对 Binance**: 使用独立的算法单接口，确保止盈 (TAKE_PROFIT_MARKET) 和止损 (STOP_MARKET) 100% 成功推送且可见。
2. **针对 OKX**: 
   - **双向止盈止损 (OCO)**: 当同时设置 `tp` 和 `sl` 时，自动调用 OKX 原生的 `oco` 类型订单，实现一成交一撤销，UI 精准显示双向触发价。
   - **移动止盈止损 (Trailing Stop)**: 通过 `/ts` 命令调用 OKX `move_order_stop` 类型订单，支持设置回调幅度（Ratio）和激活价格。
3. **价格预校验**: 推送 TP/SL 前会自动获取当前价格进行逻辑校验，防止设置错误导致立即触发。
4. **精准显示**: 查询挂单时能正确抓取 `triggerPrice` 和 `workingType` (如 MARK_PRICE)，告别 `0.0000` 价格显示。

## 🛠 最近修复与优化 (2026-06-04)

- **🏗️ 全面模块化重构**: 按 spot/futures × 命令拆分 Mixin，每个文件单一职责 ≤500 行
- **⬆️ 新增 /margin 命令**: 合约模式下动态调整杠杆倍数和保证金模式（BN + OKX）
- **📐 新增 /ctVal 命令**: 查询合约面值（每张 = ctVal × 标记价格），OKX 专用
- **🛡 新增 --reduceonly**: /tp /sl /tpsl /ts 可选参数，只减仓不开新仓
- **📊 现货 /position 优化**: 不再显示虚假多空数据，改为余额+可用+USD估值
- **📜 /history 独立模块化**: 每个交易所 spot/futures 独立 history.py，30条
- **🔌 OKX Adapter 层**: `exchanges/okx/adapter.py` 隔离 SDK，为迁移 CLI/MCP 预留
- **🌐 网络稳定性**: polling 指数退避重试、超时放宽、代理修复
- **📝 日志系统**: 按日分割 TimedRotatingFileHandler，保留 30 天
- **🐛 修复 BUG-1~BUG-10**: OKX posSide/ctVal、trailing stop 方向判断、回调拆分、API 参数错误等

## 🔒 安全建议
1. **API 权限**: 仅开启交易权限，严禁开启提币权限。
2. **白名单**: 在 `config.yaml` 中设置 `allowed_users`。

## 🧬 架构设计

```
bot.py → handlers/ → core/exchange_client.py → exchanges/
                                                      ├── binance/spot/    (6 Mixin)
                                                      │         /futures/  (6 Mixin)
                                                      │         /history   (独立)
                                                      └── okx/spot/        (6 Mixin)
                                                               /futures/    (6 Mixin)
                                                               /history     (独立)
                                                               /adapter.py  ← 隔离SDK
```

**Adapter 层** (`exchanges/okx/adapter.py`)：
将 OKX Python SDK（TradeAPI / AccountAPI / MarketDataAPI）统一包装，所有 Mixin 通过 `self._adapter` 调用。将来 OKX 推出官方 CLI/MCP 替代 SDK 时，只需实现一个新的 Adapter，上层 Mixin 和 handler 零改动。

## 许可证
MIT
