\* Essencial_LP *\
Maximize
OBJ: 0.0031145654575 Gás_de_295_para_GASDUC
 + 0.00308787387651 Gás_de_295_para_UPGN
 + 0.00289508418132 Gás_de_295_para_URGN
 + 0.00266457870406 Gás_de_295_para_URLs
 + 0.00304813414633 Gás_de_299_para_GASDUC
 + 0.00303352589954 Gás_de_299_para_UPGN
 + 0.0028288713231 Gás_de_299_para_URGN
 + 0.00264892484582 Gás_de_299_para_URLs + 0.0032452438095 Gás_de_302_para_MIX
 + 0.00304409159445 Gás_de_302_para_UPGN
 + 0.00256871749859 Gás_de_302_para_URLs
Subject To
Alocar_todo_o_gás_do_295_e_do_Reciclo: Gás_de_295_para_GASDUC
 + Gás_de_295_para_UPGN + Gás_de_295_para_URGN + Gás_de_295_para_URLs
 = 1704079.4897
Alocar_todo_o_gás_do_299: Gás_de_299_para_GASDUC + Gás_de_299_para_UPGN
 + Gás_de_299_para_URGN + Gás_de_299_para_URLs = 3236021.23707
Alocar_todo_o_gás_do_302: Gás_de_302_para_MIX + Gás_de_302_para_UPGN
 + Gás_de_302_para_URLs = 16722064.6943
GASDUC_máximo: Gás_de_295_para_GASDUC + Gás_de_299_para_GASDUC <= 6000000
GASDUC_mínimo: - Gás_de_295_para_GASDUC - Gás_de_299_para_GASDUC <= 0
MIX_máximo: Gás_de_302_para_MIX <= 4000000
MIX_mínimo: - Gás_de_302_para_MIX <= -1e-06
UPGN_máximo: Gás_de_295_para_UPGN + Gás_de_299_para_UPGN
 + Gás_de_302_para_UPGN <= 5400000
UPGN_mínimo: - Gás_de_295_para_UPGN - Gás_de_299_para_UPGN
 - Gás_de_302_para_UPGN <= -1e-06
URGN_máximo: Gás_de_295_para_URGN + Gás_de_299_para_URGN <= 2000000
URGN_mínimo: - Gás_de_295_para_URGN - Gás_de_299_para_URGN <= -1e-06
URLs_máximo: Gás_de_295_para_URLs + Gás_de_299_para_URLs
 + Gás_de_302_para_URLs <= 12900000
URLs_mínimo: - Gás_de_295_para_URLs - Gás_de_299_para_URLs
 - Gás_de_302_para_URLs <= -1e-06
Bounds
 1e-06 <= Gás_de_295_para_GASDUC <= 6000000
 1e-06 <= Gás_de_295_para_UPGN <= 5400000
 1 <= Gás_de_295_para_URGN <= 2000000
 1e-06 <= Gás_de_295_para_URLs <= 12900000
 1e-06 <= Gás_de_299_para_GASDUC <= 6000000
 Gás_de_299_para_UPGN <= 5400000
 1 <= Gás_de_299_para_URGN <= 2000000
 1e-06 <= Gás_de_299_para_URLs <= 12900000
 1e-06 <= Gás_de_302_para_MIX <= 4000000
 1e-06 <= Gás_de_302_para_UPGN <= 5400000
 1e-06 <= Gás_de_302_para_URLs <= 12900000
End
