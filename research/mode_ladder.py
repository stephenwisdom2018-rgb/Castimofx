"""Monthly path of a mode with lot = 0.01 per $per of balance, capped. Balance from closed trades at each entry."""
import sys
sys.path.insert(0, '.')
import research.final_check as FC

def path(tr, start, per=200, cap=20):
    bal = peak = low = start; worst = worstd = 0; pend = []; rows = {}; sb = {}
    for t, e, p in sorted(tr):
        done = sorted([x for x in pend if x[0] <= t]); pend = [x for x in pend if x[0] > t]
        for ex, v in done:
            bal += v; peak = max(peak, bal); worst = min(worst, (bal - peak) / peak); worstd = min(worstd, bal - peak); low = min(low, bal)
            m = ex.strftime('%Y-%m'); rows.setdefault(m, [bal, bal, 0]); rows[m][1] = bal
        lot = min(cap, max(1, int(bal // per))); pend.append((e, p * lot))
        m = t.strftime('%Y-%m'); sb.setdefault(m, bal); rows.setdefault(m, [bal, bal, 0]); rows[m][2] = max(rows[m][2], lot)
    for ex, v in sorted(pend): bal += v; rows[ex.strftime('%Y-%m')][1] = bal
    for m in sorted(rows):
        s0 = sb.get(m, rows[m][0]); e = rows[m][1]
        print(f'{m} | ${s0:>8,.0f} | ${e:>8,.0f} | {e-s0:>+8,.0f} | {rows[m][2]/100:.2f}')
    print(f'worst drop {100*worst:.0f}% (${-worstd:,.0f}), lowest ${low:,.0f}')

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else '400'
    trs = {'100': FC.mode(FC.V['C+3m+MZ'], maxopen=1, cap=15), '200': FC.mode(FC.V['C+3m+MZ'], maxopen=2, cap=15),
           '400': FC.mode(FC.V['C'], dedupe=True), 'full': FC.CHOSEN}
    print('=='); path(trs[mode], float(sys.argv[2]) if len(sys.argv) > 2 else 400)
