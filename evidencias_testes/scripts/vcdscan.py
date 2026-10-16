import re, sys
path = sys.argv[1]
ids = {}
scope = []
for l in open(path):
    l = l.strip()
    if l.startswith('$scope'):
        scope.append(l.split()[2])
    elif l.startswith('$upscope'):
        scope.pop()
    elif l.startswith('$var'):
        p = l.split()
        name = '.'.join(scope) + '.' + p[4]
        ids.setdefault(p[3], name)
    elif l.startswith('$enddefinitions'):
        break
want = [k for k, v in ids.items() if v.endswith(('tb_probe2.uut.ready', 'tb_probe2.uut.fund_ready', 'tb_probe2.uut.ess_ready', 'tb_probe2.uut.pose_done', 'tb_probe2.uut.tri_done', 'tb_probe2.uut.fund_start', 'tb_probe2.start', 'tb_probe2.ready'))]
t = None
for l in open(path):
    l = l.strip()
    if l.startswith('#'):
        t = int(l[1:]) / 1e6
    elif len(l) >= 2 and l[0] in '01UXZ' and l[1:] in want:
        print(f"{t:10.1f} ns  {ids[l[1:]]}  {l[0]}")
