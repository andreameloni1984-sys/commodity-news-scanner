"""Gagarin public-event research module. Returns WATCH context only."""

def classify(text):
    value = str(text or '').lower()
    domains = []
    if any(k in value for k in ('tariff', 'sanctions', 'trade war')): domains.append('TRADE_POLICY')
    if any(k in value for k in ('federal reserve', 'interest rate', 'inflation', 'dollar')): domains.append('RATES_MACRO')
    if any(k in value for k in ('iran', 'hormuz', 'war', 'missile', 'ceasefire')): domains.append('GEOPOLITICS')
    if any(k in value for k in ('oil', 'crude', 'brent', 'wti', 'opec')): domains.append('ENERGY')
    if any(k in value for k in ('coffee', 'cocoa', 'cacao', 'rice', 'sugar', 'wheat', 'corn', 'drought', 'harvest')): domains.append('AGRICULTURE')
    if any(k in value for k in ('gold', 'silver', 'platinum')): domains.append('METALS')
    instruments = {
      'TRADE_POLICY': ['NASDAQ100','GOLD','USD','WTI','BRENT'],
      'RATES_MACRO': ['GOLD','NASDAQ100','USD'],
      'GEOPOLITICS': ['GOLD','WTI','BRENT','DEFENSE'],
      'ENERGY': ['WTI','BRENT'],
      'AGRICULTURE': ['COFFEE','COCOA','RICE','SUGAR','WHEAT','CORN'],
      'METALS': ['GOLD','SILVER','PLATINUM']}
    watch = list(dict.fromkeys(i for d in domains for i in instruments.get(d, [])))
    return {'domains':domains,'watch_instruments':watch,'status':'WATCH' if domains else 'UNCLASSIFIED','trade_direction':None,'order_authorized':False,'caveat':'News is context only; confirm with live price, volume and Gagarin trigger.'}
