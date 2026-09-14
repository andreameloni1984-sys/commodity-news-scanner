import os, json, time
from datetime import datetime, timezone
import requests

LIVE_PRICE_ENABLED = os.getenv('LIVE_PRICE_ENABLED','1') == '1'
LIVE_PRICE_PRIMARY = os.getenv('LIVE_PRICE_PRIMARY','OANDA').upper()
LIVE_PRICE_REQUIRE_BID_ASK = os.getenv('LIVE_PRICE_REQUIRE_BID_ASK','1') == '1'
LIVE_PRICE_MAX_AGE_SECONDS = float(os.getenv('LIVE_PRICE_MAX_AGE_SECONDS','30'))

DEFAULT_OANDA_MAP = {
    'Oro':'XAU_USD','Argento':'XAG_USD','Rame':'XCU_USD','WTI':'WTICO_USD','Brent':'BCO_USD',
    'Gas Naturale':'NATGAS_USD','Grano':'WHEAT_USD','Mais':'CORN_USD','Soia':'SOYBN_USD',
    'Caffè':'COFFEE_USD','Cacao':'COCOA_USD','Zucchero':'SUGAR_USD','Cotone':'COTTON_USD'
}

def _map():
    m=dict(DEFAULT_OANDA_MAP)
    raw=os.getenv('OANDA_INSTRUMENT_MAP_JSON','').strip()
    if raw:
        try: m.update(json.loads(raw))
        except Exception: pass
    return m

def _stamp(): return datetime.now(timezone.utc).isoformat()

def get_live_quote_oanda(name, symbol=None):
    token=os.getenv('OANDA_API_TOKEN','').strip(); account=os.getenv('OANDA_ACCOUNT_ID','').strip()
    if not token or not account: return None
    instrument=_map().get(name) or symbol
    if not instrument: return None
    base=os.getenv('OANDA_BASE_URL','https://api-fxpractice.oanda.com').rstrip('/')
    url=f'{base}/v3/accounts/{account}/pricing'
    r=requests.get(url, params={'instruments':instrument}, headers={'Authorization':f'Bearer {token}'}, timeout=10)
    r.raise_for_status(); data=r.json(); prices=data.get('prices') or []
    if not prices: return None
    p=prices[0]
    bids=p.get('bids') or []; asks=p.get('asks') or []
    bid=float(bids[0]['price']) if bids else None
    ask=float(asks[0]['price']) if asks else None
    if LIVE_PRICE_REQUIRE_BID_ASK and (bid is None or ask is None): return None
    mid=float(p.get('closeoutBid') or bid or ask)
    if ask is not None and bid is not None: mid=(bid+ask)/2
    ts=p.get('time') or _stamp()
    return {'bid':bid,'ask':ask,'mid':mid,'timestamp':ts,'provider':'OANDA','instrument':instrument,'spread':(ask-bid if bid is not None and ask is not None else None)}

def get_live_quote_trading_economics(name, symbol=None):
    # TE can be used as fallback only when its endpoint returns bid/ask; no invented quote.
    return None

def get_live_quote_twelvedata(name, symbol=None):
    # Twelve Data quote is a fallback source, but it may not expose bid/ask.
    key=os.getenv('TWELVE_DATA_API_KEY','').strip()
    if not key or not symbol: return None
    try:
        r=requests.get('https://api.twelvedata.com/quote',params={'symbol':symbol,'apikey':key},timeout=10)
        r.raise_for_status(); d=r.json(); price=d.get('close') or d.get('price')
        if price is None: return None
        if LIVE_PRICE_REQUIRE_BID_ASK: return None
        return {'bid':None,'ask':None,'mid':float(price),'timestamp':_stamp(),'provider':'TWELVE_DATA','instrument':symbol,'spread':None}
    except Exception: return None

def get_live_quote(name, symbol=None):
    if not LIVE_PRICE_ENABLED: return None
    providers=[]
    if LIVE_PRICE_PRIMARY == 'OANDA': providers=[get_live_quote_oanda,get_live_quote_trading_economics,get_live_quote_twelvedata]
    else: providers=[get_live_quote_oanda,get_live_quote_trading_economics,get_live_quote_twelvedata]
    for fn in providers:
        try:
            q=fn(name,symbol)
            if not q: continue
            q['_retrieved_epoch']=time.time()
            return q
        except Exception as e:
            print(f'   ⚠️ LIVE PRICE {fn.__name__}: {e}')
    return None

def apply_live_quote(analysis, name, symbol=None):
    q=get_live_quote(name,symbol)
    analysis['live_price_status']='UNAVAILABLE'
    if not q: return False
    bid=q.get('bid'); ask=q.get('ask'); mid=q.get('mid')
    direction=(analysis.get('setup_direction') or analysis.get('model_signal') or '').upper()
    entry=ask if direction=='LONG' else bid if direction=='SHORT' else mid
    analysis.update({
        'price':mid,'entry':entry,'live_price':mid,'live_price_bid':bid,'live_price_ask':ask,
        'live_price_basis':('ASK' if direction=='LONG' else 'BID' if direction=='SHORT' else 'MID'),
        'live_price_provider':q.get('provider'),'live_price_instrument':q.get('instrument'),
        'live_price_timestamp':q.get('timestamp'),'live_price_spread':q.get('spread'),
        'live_price_status':'LIVE'
    })
    return True
