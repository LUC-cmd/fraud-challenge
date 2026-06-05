"""
Défi — Détection de fraude financière.

Vous devez implémenter la fonction `detect_fraud`.
La fonction `load_transactions` vous est FOURNIE (ne la modifiez pas).
"""

import csv
import math
from datetime import datetime
from typing import List, Dict, Any, Optional, Set


def load_transactions(path):
    """Lit un fichier CSV de transactions et renvoie une liste de dicts."""
    transactions = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            transactions.append(_clean_row(row))
    return transactions


def _clean_row(row):
    def get(key):
        v = row.get(key)
        return v.strip() if isinstance(v, str) and v.strip() != "" else None

    amount_raw = get("amount")
    try:
        amount = float(amount_raw) if amount_raw is not None else None
    except ValueError:
        amount = None

    card_raw = get("card_present")
    if card_raw is None:
        card_present = None
    else:
        card_present = card_raw.lower() in ("true", "1", "yes", "oui")

    return {
        "transaction_id": get("transaction_id"),
        "timestamp": get("timestamp"),
        "user_id": get("user_id"),
        "amount": amount,
        "currency": get("currency"),
        "merchant": get("merchant"),
        "country": get("country"),
        "card_present": card_present,
    }


# ── Seuils calibrés ────────────────────────────────────────────────────────
THRESHOLD_SUSPICIOUS  = 0.5
Z_SCORE_STRONG        = 3.5
Z_SCORE_MODERATE      = 2.5
IQR_MULTIPLIER        = 1.5
MIN_HISTORY_FOR_IQR   = 4
MIN_HISTORY_FOR_MERCH = 5
MAX_TRAVEL_SPEED_KMH  = 900
GEO_FAST_HOURS        = 2
GEO_FAST_DISTANCE_KM  = 500
FREQ_CRITICAL         = 5
FREQ_ELEVATED         = 3
FREQ_WINDOW_SEC       = 60

# ── Coordonnées pays ────────────────────────────────────────────────────────
COUNTRY_COORDS = {
    'FR': (48.8566,  2.3522), 'US': (37.7749, -122.4194), 'GB': (51.5074,  -0.1278),
    'DE': (52.5200,  13.405), 'IT': (41.9028,  12.4964),  'ES': (40.4168,  -3.7038),
    'BE': (50.8503,   4.352), 'NL': (52.3676,   4.9041),  'CH': (46.9479,   7.4474),
    'AT': (48.2082,  16.374), 'PL': (52.2297,  21.0122),  'SE': (59.3293,  18.0686),
    'NO': (59.9139,  10.752), 'DK': (55.6761,  12.5683),  'FI': (60.1695,  24.9354),
    'JP': (35.6762, 139.650), 'CN': (39.9042, 116.4074),  'IN': (28.6139,  77.2090),
    'BR': (-23.550, -46.633), 'MX': (19.4326, -99.1332),  'CA': (43.6532, -79.3832),
    'AU': (-33.869, 151.209), 'KR': (37.5665, 126.9780),  'TH': (13.7563, 100.5018),
    'SN': (14.7167, -17.467), 'CI': (6.8276,  -5.2893),   'TG': (6.1256,   1.2317),
    'BF': (12.3714,  -1.520), 'ML': (12.6392,  -8.0029),  'NE': (13.5116,  2.1257),
    'AE': (25.2048,  55.270), 'ZA': (-26.205,  28.0473),  'MA': (31.7917,  -7.0926),
}


def _is_empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip() == ""


def _parse_ts(ts) -> Optional[datetime]:
    if _is_empty(ts):
        return None
    try:
        if isinstance(ts, datetime):
            return ts.replace(tzinfo=None) if ts.tzinfo else ts
        parsed = datetime.fromisoformat(str(ts).strip().replace('Z', '+00:00'))
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except Exception:
        return None


def _parse_amount(raw) -> Optional[float]:
    if _is_empty(raw):
        return None
    try:
        return float(raw)
    except Exception:
        return None


def _parse_card(raw) -> bool:
    if isinstance(raw, bool):
        return raw
    if _is_empty(raw):
        return False
    return str(raw).strip().lower() in ('true', '1', 'yes', 'oui', 'vrai')


def _mean(vals: List[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _std(vals: List[float], m: Optional[float] = None) -> float:
    if len(vals) < 2:
        return 0.0
    m = m or _mean(vals)
    return math.sqrt(sum((x - m) ** 2 for x in vals) / len(vals))


def _iqr_fence(vals: List[float]) -> Optional[float]:
    if len(vals) < MIN_HISTORY_FOR_IQR:
        return None
    s = sorted(vals)
    n = len(s)
    q1, q3 = s[n // 4], s[(3 * n) // 4]
    iqr = q3 - q1
    return (q3 + IQR_MULTIPLIER * iqr) if iqr > 0 else None


def _dist_km(c1: str, c2: str) -> float:
    if not c1 or not c2:
        return 0.0
    c1, c2 = c1.upper(), c2.upper()
    if c1 not in COUNTRY_COORDS or c2 not in COUNTRY_COORDS:
        return 5000.0
    la1, lo1 = COUNTRY_COORDS[c1]
    la2, lo2 = COUNTRY_COORDS[c2]
    return math.sqrt((la2 - la1) ** 2 + (lo2 - lo1) ** 2) * 111


def _normalize(tx: dict) -> dict:
    try:
        return {
            'transaction_id': str(tx.get('transaction_id') or '').strip(),
            'user_id':        str(tx.get('user_id') or '').strip(),
            'amount':         _parse_amount(tx.get('amount')),
            'currency':       str(tx.get('currency') or '').strip().upper(),
            'merchant':       str(tx.get('merchant') or '').strip().lower(),
            'country':        str(tx.get('country') or '').strip().upper(),
            'timestamp':      _parse_ts(tx.get('timestamp')),
            'card_present':   _parse_card(tx.get('card_present')),
        }
    except Exception:
        return {'transaction_id': '', 'user_id': '', 'amount': None,
                'currency': '', 'merchant': '', 'country': '',
                'timestamp': None, 'card_present': False}


def _history(txs, idx, uid):
    amounts, countries, merchants, currencies = [], set(), set(), set()
    card_ok, total = 0, 0
    cur_ts = txs[idx]['timestamp']
    for i, t in enumerate(txs):
        if i >= idx or t['user_id'] != uid:
            continue
        if cur_ts and t['timestamp'] and t['timestamp'] >= cur_ts:
            continue
        if t['amount'] and t['amount'] > 0:
            amounts.append(t['amount'])
        if t['country']:   countries.add(t['country'])
        if t['merchant']:  merchants.add(t['merchant'])
        if t['currency']:  currencies.add(t['currency'])
        if t['card_present']:
            card_ok += 1
        total += 1
    return dict(amounts=amounts, countries=countries, merchants=merchants,
                currencies=currencies, card_ok=card_ok, total=total)


def _last_country(txs, idx, uid, ts):
    lc, lt = None, None
    for i, t in enumerate(txs):
        if i == idx or t['user_id'] != uid: continue
        if not t['timestamp'] or not t['country']: continue
        if t['timestamp'] >= ts: continue
        if lt is None or t['timestamp'] > lt:
            lc, lt = t['country'], t['timestamp']
    return lc, lt


def _nearby(txs, idx, uid, ts) -> int:
    return sum(1 for t in txs
               if t['user_id'] == uid and t['timestamp']
               and abs((t['timestamp'] - ts).total_seconds()) < FREQ_WINDOW_SEC)


def _is_dup(txs, idx, norm) -> bool:
    tid = norm['transaction_id']
    for i, t in enumerate(txs):
        if i >= idx: break
        if tid and t['transaction_id'] == tid: return True
        if (t['user_id'] == norm['user_id'] and t['amount'] == norm['amount']
                and t['merchant'] == norm['merchant']
                and t['timestamp'] and norm['timestamp']
                and t['timestamp'] == norm['timestamp']):
            return True
    return False


def detect_fraud(transactions):
    """Analyse une liste de transactions et renvoie un verdict pour chacune.

    Retour : list[dict] avec transaction_id, fraud_score (0-1),
    is_suspicious (bool), reason (str) — un résultat par transaction, même ordre.
    """
    if not transactions:
        return []

    # Normaliser toutes les transactions
    txs = []
    for tx in transactions:
        txs.append(_normalize(tx if isinstance(tx, dict) else {}))

    results = []
    for idx, n in enumerate(txs):
        tid    = n['transaction_id'] or 'unknown'
        amount = n['amount']
        uid    = n['user_id']
        ts     = n['timestamp']
        country= n['country']
        merch  = n['merchant']
        curr   = n['currency']
        card   = n['card_present']

        score = 0.0
        reasons = []

        # ── Champs critiques manquants ──────────────────────────────────────
        missing = [f for f, v in [('transaction_id', tid),
                                   ('user_id', uid)] if _is_empty(v)]
        if amount is None:
            missing.append('amount')

        if missing:
            score = 1.0
            reasons.append(f"Champ(s) manquant(s) : {', '.join(missing)}")

        # ── Montant invalide ─────────────────────────────────────────────────
        elif amount <= 0:
            score = 1.0
            reasons.append("Montant invalide (nul ou negatif)")

        else:
            hist = _history(txs, idx, uid)
            prev = hist['amounts']
            m    = _mean(prev)
            s    = _std(prev, m)

            # Doublon
            if _is_dup(txs, idx, n):
                score += 0.40
                reasons.append("Transaction dupliquee detectee")

            # Anomalie montant (IQR > Z-score > ratio)
            flagged = False
            fence = _iqr_fence(prev)
            if fence and amount > fence:
                excess = (amount - fence) / max(fence, 1)
                score += min(0.40, 0.20 + excess * 0.05)
                reasons.append(f"Montant hors plage : {amount:.2f} > IQR {fence:.2f}")
                flagged = True
            elif m > 0 and s > 0:
                z = (amount - m) / s
                if z > Z_SCORE_STRONG:
                    score += 0.35
                    reasons.append(f"Montant anormal : {amount:.2f} vs moy {m:.2f} (z={z:.1f})")
                    flagged = True
                elif z > Z_SCORE_MODERATE and len(prev) >= 3:
                    score += 0.15
                    reasons.append(f"Montant eleve : {amount:.2f} vs moy {m:.2f}")
                    flagged = True
            elif prev and amount > max(prev) * 3:
                score += 0.15
                reasons.append(f"Montant 3x sup. au max historique ({max(prev):.2f})")
                flagged = True

            # Nouveau commerçant (signal faible)
            if (merch and merch not in hist['merchants']
                    and len(hist['merchants']) >= MIN_HISTORY_FOR_MERCH
                    and not flagged):
                score += 0.05
                reasons.append(f"Commercant nouveau : {merch}")

            # Devise inhabituelle
            if (curr and hist['currencies'] and curr not in hist['currencies']
                    and len(hist['currencies']) >= 2):
                score += 0.08
                reasons.append(f"Devise inhabituelle : {curr}")

            # Carte absente vs profil
            if hist['total'] >= 3 and hist['card_ok'] / hist['total'] > 0.8 and not card:
                score += 0.10
                reasons.append("Paiement sans carte (profil en magasin)")

            # Géographie impossible
            if ts and country:
                lc, lt = _last_country(txs, idx, uid, ts)
                if lc and lc != country and lt:
                    dt_h = (ts - lt).total_seconds() / 3600
                    dist = _dist_km(lc, country)
                    if dt_h > 0 and dist / dt_h > MAX_TRAVEL_SPEED_KMH:
                        score += 0.25
                        reasons.append(
                            f"Deplacement impossible : {lc}->{country} "
                            f"en {dt_h:.1f}h ({dist:.0f} km)")
                    elif dt_h < GEO_FAST_HOURS and dist > GEO_FAST_DISTANCE_KM:
                        score += 0.15
                        reasons.append(
                            f"Deplacement rapide : {dist:.0f} km en {dt_h:.1f}h")

            # Fréquence suspecte
            if ts:
                nb = _nearby(txs, idx, uid, ts)
                if nb >= FREQ_CRITICAL:
                    score += 0.55
                    reasons.append(f"Frequence excessive : {nb} tx/min")
                elif nb >= FREQ_ELEVATED:
                    score += 0.15
                    reasons.append(f"Frequence elevee : {nb} tx/min")

        score = round(max(0.0, min(1.0, score)), 3)
        if not reasons:
            reason = "Transaction normale"
            score  = 0.0

        results.append({
            'transaction_id': tid,
            'fraud_score':    score,
            'is_suspicious':  score >= THRESHOLD_SUSPICIOUS,
            'reason':         " | ".join(reasons) if reasons else "Transaction normale",
        })

    return results
