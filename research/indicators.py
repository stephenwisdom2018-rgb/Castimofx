"""Shared indicators for research scripts (no side effects on import)."""
import numpy as np, pandas as pd

def adx(h, l, c, n=14):
    up, dn = h.diff(), -l.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0); ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/n, adjust=False).mean()
    pdi = 100 * pd.Series(pdm, h.index).ewm(alpha=1/n, adjust=False).mean() / atr
    ndi = 100 * pd.Series(ndm, h.index).ewm(alpha=1/n, adjust=False).mean() / atr
    return (100 * (pdi - ndi).abs() / (pdi + ndi)).ewm(alpha=1/n, adjust=False).mean()
