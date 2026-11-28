"""Basket spacing $1-$5, both kinds: LIMITS (add against us, basket2, stop = entry's stop) and STOPS (add with the move,
basket3). 2026, 0.01 per order, true data, real fills."""
import sys
sys.path.insert(0, '.')
import pandas as pd
import research.basket2 as B2, research.basket3 as B3

if __name__ == '__main__':
    for v, E in B2.VERS.items():
        cols = {}
        for Sg in (1, 2, 3, 4, 5):
            r = B2.run(E, Sg, 1); cols[f'lim ${Sg}'] = r
        for Sg in (1, 2, 3, 4, 5):
            cols[f'stop ${Sg}'] = B3.run(E, Sg)
        df = pd.DataFrame(cols).loc[['Profit', 'Win', 'Avg orders', 'Green days', 'Worst day', 'Min bal']]
        print(v); print(df.T.to_string(), flush=True)
