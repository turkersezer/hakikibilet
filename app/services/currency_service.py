"""
Çoklu Para Birimi & Döviz Kuru Servisi
Desteklenen Birimler: TRY (₺), EUR (€), USD ($), GBP (£)
TCMB / Uluslararası Döviz Kurları ve Anlık Çevrim Motoru
"""
import time
import urllib.request
import json
from typing import Dict, Any, Optional

class CurrencyService:
    # Desteklenen Para Birimleri ve Sembolleri
    CURRENCIES = {
        "TRY": {"symbol": "₺", "name": "Türk Lirası", "flag": "🇹🇷"},
        "EUR": {"symbol": "€", "name": "Euro", "flag": "🇪🇺"},
        "USD": {"symbol": "$", "name": "Amerikan Doları", "flag": "🇺🇸"},
        "GBP": {"symbol": "£", "name": "İngiliz Sterlini", "flag": "🇬🇧"}
    }

    # Güvenli Varsayılan Kurlar (Baz: 1 EUR)
    DEFAULT_RATES_BASE_EUR = {
        "EUR": 1.0,
        "TRY": 38.65,
        "USD": 1.09,
        "GBP": 0.85
    }

    _cached_rates: Dict[str, float] = {}
    _last_fetched: float = 0
    CACHE_DURATION: int = 3600  # 1 Saat

    @classmethod
    def get_symbol(cls, currency_code: str) -> str:
        curr = currency_code.upper() if currency_code else "TRY"
        return cls.CURRENCIES.get(curr, {}).get("symbol", "₺")

    @classmethod
    def get_rates(cls) -> Dict[str, float]:
        """Güncel döviz kurlarını getirir (1 saatlik bellek içi önbellek ile)"""
        now = time.time()
        if cls._cached_rates and (now - cls._last_fetched < cls.CACHE_DURATION):
            return cls._cached_rates

        try:
            # Açık ve hızlı kur API'si (Frankfurter / ExchangeRate)
            req = urllib.request.Request(
                "https://api.frankfurter.app/latest?from=EUR&to=TRY,USD,GBP",
                headers={"User-Agent": "NetRotaTravel/1.0"}
            )
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                rates = {"EUR": 1.0}
                for k, v in data.get("rates", {}).items():
                    rates[k] = float(v)
                cls._cached_rates = rates
                cls._last_fetched = now
                return cls._cached_rates
        except Exception:
            # Bağlantı gecikmesi veya internet kesintisinde anında güvenli kurlara dön
            cls._cached_rates = cls.DEFAULT_RATES_BASE_EUR.copy()
            cls._last_fetched = now
            return cls._cached_rates

    @classmethod
    def convert(cls, amount: Optional[float], from_curr: str = "TRY", to_curr: str = "TRY") -> Optional[float]:
        """Bir para biriminden diğerine anlık kurla çevirir"""
        if amount is None:
            return None

        from_curr = (from_curr or "TRY").upper()
        to_curr = (to_curr or "TRY").upper()

        if from_curr == to_curr:
            return round(amount, 2)

        rates = cls.get_rates()
        from_rate = rates.get(from_curr, cls.DEFAULT_RATES_BASE_EUR.get(from_curr, 1.0))
        to_rate = rates.get(to_curr, cls.DEFAULT_RATES_BASE_EUR.get(to_curr, 1.0))

        # EUR bazına çevir -> Hedef kura çevir
        amount_in_eur = amount / from_rate
        converted = amount_in_eur * to_rate
        return round(converted, 2)

    @classmethod
    def format_amount(cls, amount: Optional[float], currency_code: str = "TRY") -> str:
        if amount is None:
            return ""
        symbol = cls.get_symbol(currency_code)
        curr = currency_code.upper()
        
        # Türkiye & Avrupa gösterim standardı
        if curr in ("USD", "GBP"):
            return f"{symbol}{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            return f"{amount:,.2f} {symbol}".replace(",", "X").replace(".", ",").replace("X", ".")
