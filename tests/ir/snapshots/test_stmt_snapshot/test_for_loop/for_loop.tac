i := 0
Lfor_cond0:
< i, 3 -> t0
if t0 goto Lfor_body1
goto Lfor_end3
Lfor_body1:
print i
Lfor_step2:
+ i, 1 -> t1
i := t1
goto Lfor_cond0
Lfor_end3: