"""账户/会话管理 — 修复 BUG-10: margin_mode 未持久化"""
import logging
import json
import os
from typing import Dict, Optional
from core.exchange_client import ExchangeClient

logger = logging.getLogger(__name__)


class AccountManager:
    """账户管理器，负责初始化客户端、切换账户/模式、持久化会话"""

    def __init__(self, config: Dict):
        self.config = config
        self.clients: Dict[str, ExchangeClient] = {}
        self.active_accounts: Dict[int, Dict[str, str]] = {}  # chat_id -> {exchange, account, mode, margin_mode}
        self.session_file = 'sessions.json'
        self._load_sessions()
        self._init_clients()

    def _load_sessions(self) -> None:
        """从文件加载会话状态"""
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # json key 是 string，转换为 int chat_id
                    self.active_accounts = {int(k): v for k, v in data.items()}
                logger.info(f"成功加载 {len(self.active_accounts)} 个会话状态")
            except Exception as e:
                logger.error(f"加载会话状态失败: {str(e)}")

    def _save_sessions(self) -> None:
        """保存会话状态到文件

        BUG-10 修复: margin_mode 随 mode 一起持久化到 sessions.json
        """
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(self.active_accounts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存会话状态失败: {str(e)}")

    def _init_clients(self) -> None:
        """初始化所有交易所客户端"""
        exchanges_config = self.config.get('exchanges', {})
        proxy_port = self.config.get('proxy', {}).get('port')

        for exchange_name, accounts in exchanges_config.items():
            for account_id, account_config in accounts.items():
                key = f"{exchange_name}.{account_id}"
                try:
                    self.clients[key] = ExchangeClient(exchange_name, account_id, account_config, proxy_port)
                    logger.info(f"成功初始化账户: {key}")
                except Exception as e:
                    logger.error(f"初始化账户 {key} 失败: {str(e)}")

    def get_client(self, chat_id: int) -> Optional[ExchangeClient]:
        """获取当前激活的交易所客户端"""
        if chat_id not in self.active_accounts:
            return None

        account_info = self.active_accounts[chat_id]
        key = f"{account_info['exchange']}.{account_info['account']}"
        client = self.clients.get(key)

        if client:
            # 同步模式设置
            if 'mode' in account_info:
                client.set_mode(account_info['mode'])
            # BUG-10 修复: 同步保证金模式
            if 'margin_mode' in account_info:
                client.margin_mode = account_info['margin_mode']

        return client

    def switch_account(self, chat_id: int, exchange: str, account_id: str,
                       mode: Optional[str] = None) -> bool:
        """切换账户"""
        key = f"{exchange}.{account_id}"
        if key not in self.clients:
            logger.warning(f"尝试切换到不存在的账户: {key}")
            return False

        self.active_accounts[chat_id] = {
            'exchange': exchange,
            'account': account_id
        }

        if mode:
            self.active_accounts[chat_id]['mode'] = mode
        else:
            client = self.clients[key]
            self.active_accounts[chat_id]['mode'] = client.mode
            logger.info(f"[{key}] 自动切换交易模式为: {self.active_accounts[chat_id]['mode']}")

        # BUG-10 修复: 切换账户时恢复 margin_mode
        client = self.clients[key]
        self.active_accounts[chat_id]['margin_mode'] = client.margin_mode

        self._save_sessions()
        return True

    def switch_mode(self, chat_id: int, mode: str) -> bool:
        """切换交易模式"""
        if chat_id not in self.active_accounts:
            return False

        if mode not in ['spot', 'future']:
            return False

        self.active_accounts[chat_id]['mode'] = mode
        self._save_sessions()

        # 同步到客户端
        client = self.get_client(chat_id)
        if client:
            client.set_mode(mode)

        logger.info(f"Chat {chat_id} 切换模式到: {mode}")
        return True

    def switch_margin_mode(self, chat_id: int, margin_mode: str) -> bool:
        """切换保证金模式（全仓/逐仓）"""
        if chat_id not in self.active_accounts:
            return False

        if margin_mode not in ['cross', 'isolated']:
            return False

        # BUG-10 修复: margin_mode 写入 active_accounts 并持久化
        self.active_accounts[chat_id]['margin_mode'] = margin_mode
        self._save_sessions()

        # 同步到客户端
        client = self.get_client(chat_id)
        if client:
            client.margin_mode = margin_mode

        logger.info(f"Chat {chat_id} 切换保证金模式到: {margin_mode}")
        return True

    def get_current_account_info(self, chat_id: int) -> Optional[Dict[str, str]]:
        """获取当前账户信息

        当客户端初始化失败（self.clients 无对应 key）时返回 None，
        避免 menu.py 访问不存在的 key 导致 KeyError
        """
        info = self.active_accounts.get(chat_id)
        if not info:
            return None
        key = f"{info['exchange']}.{info['account']}"
        client = self.clients.get(key)
        if not client:
            # 客户端初始化失败，清除无效会话并返回 None
            logger.warning(f"账户 {key} 客户端未初始化，清除会话引用")
            self.active_accounts.pop(chat_id, None)
            self._save_sessions()
            return None
        info['name'] = client.name
        info['testnet'] = client.testnet
        # BUG-10 修复: 优先使用持久化的 margin_mode，fallback 到 client 配置
        info['margin_mode'] = info.get('margin_mode', client.margin_mode)
        return info

    def list_available_accounts_with_info(self) -> Dict[str, list]:
        """列出所有可用账户及其详细信息"""
        result = {}
        for key, client in self.clients.items():
            exchange, account_id = key.split('.', 1)
            if exchange not in result:
                result[exchange] = []
            result[exchange].append({
                'id': account_id,
                'name': client.name,
                'testnet': client.testnet
            })
        return result
