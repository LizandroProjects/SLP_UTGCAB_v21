Ver comentários no Histórico (Lizandro)



COMENTÁRIOS DO PAIVA
=

1. FEITO: Substituido o termo *Hysysconect* por **Hysysconnect** - foram 9 ocorrências e 3 arquivos.  
2. A FAZER: Evitar a linha 14 do optLP_v19.py, citada a seguir:  
       `ÚLTIMA MODIFICAÇÃO: 11 DE JANEIRO DE 2024, 11H 25 MIN.`  
3. A FAZER: ***import matplotlib.pyplot as plt***  - é citado duas vezes, podemos suprimir a chamada do *optLP_v19.py*  





## As linhas abaixo necessitam de atenção - linha 905 do arquivo functions_v19.py
 # Versão 19 [CO2 nas URLs]
    SS_URLI.Cell('C5').CellValue = e29*0.95 # FRAÇÃO MOLAR de C1 no fundo da T01 DA URL-1 (CALCULADA PELA SIMULAÇÃO RIGOROSA)
    SS_URLII.Cell('C5').CellValue = e30*0.95 # FRAÇÃO MOLAR DE C2 NO TOPO DA T01 DA URL-1 (CALCULADA PELA SIMULAÇÃO RIGOROSA)  
    SS_URLIII.Cell('C5').CellValue = e31*0.95 # FRAÇÃO MOLAR DE C2 NO TOPO DA T01 DA URL-1 (CALCULADA PELA SIMULAÇÃO RIGOROSA)

## Várias especificações adotadas são bastante polêmicas e carecem de base teórica e necessitam ser revistas da função SpecVar

## Não entendi esta parte das derivadas das derivadas.
[2] EXPLICAÇÃO: Essa função é utilizada para obter os valores das restrições de produtos, dadas os valores das variáveis
    de decisão. A função tambem pode ser utilizada para calcular as derivadas das derivadas das especificações em relação às
    variáveis de decisão.

## o tal do delta_MIX pode sair daqui.
       MT_main['C5'].MolarFlow.SetValue(x[10]+delta_MIX,'m3/d_(gas)')        #M11   

## Esta função gerou muitas dúvidas. (explicar melhor step by step e também o conceito)
       def Spec_prods(x, delta_MIX, obj):


## aqui aparenta que estou calculando as derivadas para cada uma das variáveis de decisão?
dR_dF[i] = ( f_OBJ[i] - f_OBJ_Base ) / delta[i] # Cálculo da Derivada [usando o ponto_base]
                dC_dF[i,:] = (y - y_base) / delta[i] # Cálculo da Derivada das restriçoes


