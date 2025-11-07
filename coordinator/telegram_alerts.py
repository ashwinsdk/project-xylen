"""
Telegram Alert System for Project Xylen
Sends real-time notifications for trades, errors, and system events
"""

import asyncio
import logging
import os
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger.warning("aiohttp not available, telegram alerts disabled")


class TelegramAlerter:
    """Send alerts via Telegram Bot API"""
    
    def __init__(self, config: Dict):
        self.enabled = config.get('telegram', {}).get('enabled', False)
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN') or config.get('telegram', {}).get('bot_token')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID') or config.get('telegram', {}).get('chat_id')
        
        self.alert_levels = config.get('telegram', {}).get('alert_levels', ['ERROR', 'TRADE', 'CIRCUIT_BREAKER'])
        self.rate_limit_seconds = config.get('telegram', {}).get('rate_limit_seconds', 5)
        
        self.last_alert_time = {}
        self.session: Optional[aiohttp.ClientSession] = None
        
        if self.enabled:
            if not self.bot_token or not self.chat_id:
                logger.error("Telegram enabled but bot_token or chat_id not configured")
                self.enabled = False
            elif not AIOHTTP_AVAILABLE:
                logger.error("Telegram enabled but aiohttp not installed")
                self.enabled = False
            else:
                logger.info(f"Telegram alerts enabled for levels: {self.alert_levels}")
    
    async def initialize(self):
        """Initialize HTTP session"""
        if self.enabled and AIOHTTP_AVAILABLE:
            self.session = aiohttp.ClientSession()
            # Test connection
            try:
                await self.send_message("🤖 *Xylen Trading Bot Started*\n\n✅ Telegram alerts activated", alert_type='SYSTEM')
            except Exception as e:
                logger.error(f"Failed to send test telegram message: {e}")
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def send_message(self, message: str, alert_type: str = 'INFO', parse_mode: str = 'Markdown'):
        """Send message to Telegram"""
        if not self.enabled or not self.session:
            return
        
        # Check if this alert type should be sent
        if alert_type not in self.alert_levels and alert_type != 'SYSTEM':
            return
        
        # Rate limiting per alert type
        now = datetime.utcnow().timestamp()
        last_time = self.last_alert_time.get(alert_type, 0)
        
        if now - last_time < self.rate_limit_seconds:
            logger.debug(f"Rate limiting telegram alert: {alert_type}")
            return
        
        self.last_alert_time[alert_type] = now
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }
            
            async with self.session.post(url, json=payload, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning(f"Telegram API error {resp.status}: {await resp.text()}")
                else:
                    logger.debug(f"Telegram alert sent: {alert_type}")
        
        except Exception as e:
            logger.error(f"Failed to send telegram message: {e}")
    
    async def alert_trade_opened(self, trade_info: Dict):
        """Alert when trade is opened"""
        message = f"""
🟢 *TRADE OPENED*

*Symbol:* {trade_info.get('symbol', 'N/A')}
*Side:* {trade_info.get('side', 'N/A').upper()}
*Size:* {trade_info.get('quantity', 0):.4f}
*Entry:* ${trade_info.get('entry_price', 0):.2f}
*Stop Loss:* ${trade_info.get('stop_loss', 0):.2f}
*Take Profit:* ${trade_info.get('take_profit', 0):.2f}

*Confidence:* {trade_info.get('confidence', 0):.1%}
*Expected Value:* {trade_info.get('expected_value', 0):.2%}

*Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        """.strip()
        
        await self.send_message(message, alert_type='TRADE')
    
    async def alert_trade_closed(self, trade_info: Dict):
        """Alert when trade is closed"""
        pnl = trade_info.get('pnl', 0)
        pnl_pct = trade_info.get('pnl_percent', 0)
        
        emoji = "🟢" if pnl > 0 else "🔴"
        result = "PROFIT" if pnl > 0 else "LOSS"
        
        message = f"""
{emoji} *TRADE CLOSED - {result}*

*Symbol:* {trade_info.get('symbol', 'N/A')}
*Side:* {trade_info.get('side', 'N/A').upper()}
*Entry:* ${trade_info.get('entry_price', 0):.2f}
*Exit:* ${trade_info.get('exit_price', 0):.2f}

*P&L:* ${pnl:.2f} ({pnl_pct:+.2f}%)
*Duration:* {trade_info.get('duration_minutes', 0):.0f} min
*Exit Reason:* {trade_info.get('exit_reason', 'N/A')}

*Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        """.strip()
        
        await self.send_message(message, alert_type='TRADE')
    
    async def alert_circuit_breaker(self, reason: str, details: Dict):
        """Alert when circuit breaker is triggered"""
        message = f"""
🔴 *CIRCUIT BREAKER TRIGGERED*

*Reason:* {reason}

*Details:*
{self._format_details(details)}

⏸️ Trading halted for cooldown period
        """.strip()
        
        await self.send_message(message, alert_type='CIRCUIT_BREAKER')
    
    async def alert_daily_summary(self, summary: Dict):
        """Send daily performance summary"""
        total_pnl = summary.get('total_pnl', 0)
        emoji = "🟢" if total_pnl > 0 else "🔴" if total_pnl < 0 else "⚪"
        
        message = f"""
📊 *DAILY SUMMARY*

{emoji} *Total P&L:* ${total_pnl:.2f}

*Trades:* {summary.get('total_trades', 0)}
*Wins:* {summary.get('wins', 0)} | *Losses:* {summary.get('losses', 0)}
*Win Rate:* {summary.get('win_rate', 0):.1%}

*Best Trade:* ${summary.get('best_trade', 0):.2f}
*Worst Trade:* ${summary.get('worst_trade', 0):.2f}
*Avg P&L:* ${summary.get('avg_pnl', 0):.2f}

*Date:* {datetime.utcnow().strftime('%Y-%m-%d')}
        """.strip()
        
        await self.send_message(message, alert_type='DAILY_SUMMARY')
    
    async def alert_error(self, error_type: str, message: str, details: Optional[Dict] = None):
        """Alert on errors"""
        msg = f"""
⚠️ *ERROR: {error_type}*

*Message:* {message}

{self._format_details(details) if details else ''}

*Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        """.strip()
        
        await self.send_message(msg, alert_type='ERROR')
    
    async def alert_model_offline(self, model_name: str, duration_seconds: int):
        """Alert when model server goes offline"""
        message = f"""
⚠️ *MODEL OFFLINE*

*Model:* {model_name}
*Offline Duration:* {duration_seconds // 60} minutes

Ensemble will continue with remaining models.
        """.strip()
        
        await self.send_message(message, alert_type='WARNING')
    
    async def alert_balance_low(self, current_balance: float, threshold: float):
        """Alert when balance is low"""
        message = f"""
⚠️ *LOW BALANCE WARNING*

*Current Balance:* ${current_balance:.2f}
*Threshold:* ${threshold:.2f}

Consider depositing more funds or reducing position sizes.
        """.strip()
        
        await self.send_message(message, alert_type='WARNING')
    
    def _format_details(self, details: Dict) -> str:
        """Format details dict for message"""
        if not details:
            return ""
        
        lines = []
        for key, value in details.items():
            key_formatted = key.replace('_', ' ').title()
            if isinstance(value, float):
                lines.append(f"• *{key_formatted}:* {value:.4f}")
            else:
                lines.append(f"• *{key_formatted}:* {value}")
        
        return '\n'.join(lines)


# Singleton instance
_alerter: Optional[TelegramAlerter] = None


def get_alerter(config: Optional[Dict] = None) -> Optional[TelegramAlerter]:
    """Get or create telegram alerter singleton"""
    global _alerter
    
    if _alerter is None and config:
        _alerter = TelegramAlerter(config)
    
    return _alerter


async def initialize_alerter(config: Dict):
    """Initialize telegram alerter"""
    alerter = get_alerter(config)
    if alerter and alerter.enabled:
        await alerter.initialize()
    return alerter


async def close_alerter():
    """Close telegram alerter"""
    global _alerter
    if _alerter:
        await _alerter.close()
        _alerter = None
