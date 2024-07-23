import numpy as np # Bliblioteca matemática numpy
import matplotlib.pyplot as plt # Biblioteca para Plotagem
import pandas as pd # Bliblioteca da banco de dados Pandas
import os # Bliblioteca para mapear caminho de diretório
import win32com.client as win32  # Biblioteca para comunicação com hysys
from numpy import linalg as la # Bibliotecas de álgebra linear
from pulp import pulp, LpMaximize, LpProblem, LpStatus, LpVariable  # Biblioteca Pulp # Referencias: https://coin-or.github.io/pulp/index.html
import timeit # Contador de tempo computacional
import xlsxwriter # escrever em excel
from time import sleep # Usar a função sleep para atrasar o cálculo seguinte, se necessário

from func_auxiliar import (aloca_cargas,  # funcções auxiliares para rodar a simulação rogorosa (peguei da versão implementada no servidor)
                            ler_config,
                            ler_inputs,
                            simula_detalhada, # função com a simulação detalhada
                            )
 
from functions_v20 import (SimulaLP,  # Funçaõ de Simulação
                           Spec_prods,
                           plot_derivatives,
                           )
        
def SLP(simCase, edata, obj, R_min, R_max, R_cap, Carga, FObj_type):
    
    '''
    *************************************************************************************************************************************
    [1] DESCRIÇÃO: SLP: Sequential Linear Programming -> Rotina da Programação Linear Sucessiva
    
    [2] EXPLICAÇÃO: Essa é utilizada para realizar a otimização linear sequencial do processo. Um modelo linear, baseado nas equações
    de balanço de massa global, é utilizado e implementado, nessa versão, na toolbox PULP (https://coin-or.github.io/pulp/index.html).
    Uma explicação detalhada do procedimento matemático está documentada do arquivo ProgramaçãoLinearSucessiva.ppx da pasta do projeto.
    A função SLP deve receber algumas variáveis e parâmetros, para possibilitar a comunicação e troca de "informações" entre o Python e
    o Hysys, de modo a possibilitar a otimização. 
    
    [3] DADOS DE ENTRADA: 
        simCase -> Objeto resultante da comunicação entre Python e Hysys (usado para abrir, fechar e ou iniciar a simulação);
        edata   -> Dicionário contendo os valores de parâmetros e variáveis do arquivo de entrada Input.xls;
        obj     -> Dicionário contendo os objetos resultantes das variáveis e spreadsheets do hysys que serão utilizados
        R_min   -> Dicionário contendo os valores mínimos das restrições das especificações de produtos
        R_max   -> Dicionário contendo os valores máximos das restrições das especificações de produtos
        R_cap   -> Dicionário contendo os valores das restrições de capacidade das unidades
        Carga   -> Dicionário contendo os valores das vazões de carga da Unidade
        FObj_type -> Variável que indica a formulação da função objetivo: Obj_type = 'Custo'; 'Receita' ou 'Margem'
     
    [4] DADOS DE SAÌDA: 
        cod_SLP   -> Flag para indicar sucesso ou insucesso do cálculo
        rel_SLP   -> Dicionário contendo dados da otimização (iterações, derivadas, receitas, variáveis de decisão etc.)
        model     -> Objeto com todos os dados da otimização LP
        
    [5] OBSERVAÇÕES: Ao longo do código adicionaremos algumas anotações para facilitar a compreensão das considerações utilizadas
    
    [6] Modificações:


    07 de julho de 2024: Separação da função SLP das demais (nesse qruibo optimal_SLP)    
    07 de abril de 2024: Inclusão de flags para gravar restrições violadas
    *************************************************************************************************************************************
    '''
    
    
    '''
    SEÇÃO[1] DECLARAÇÃO DAS VARIÁVEIS
    *************************************************************************************************************************************
    '''
    'Iniciando contador de tempo'
    init_time = timeit.default_timer() # Estamos iniciando a contagem do tempo a partir daqui...
    
    'Descompactando o dicionário obj (somente os necessários para esta função)'
    MT_main = obj['MT_main'] # Objeto para se comunicar com as correntes do flowsheet principal
    F0 = edata['valor_inicial_manipuladas']  # Essa estimativa vem da planilha especificada pelo usuário!
    SS_f_OBJ =  obj['SS_f_OBJ'] 
    precos = edata['precos']
    SS_Receita=obj['SS_Receita']
         
    'Definição das variáveis da otimização LINEAR, de acordo com a notação do PULP'  
    G_295 = Carga['G_295']
    G_299 = Carga['G_299']
    G_302 = Carga['G_302']
    GASDUC_min = R_cap['GASDUC_min']
    GASDUC_max = R_cap['GASDUC_max']
    MIX_min = R_cap['MIX_min']
    MIX_max = R_cap['MIX_max']
    UPGN_min = R_cap['UPGN_min']
    UPGN_max = R_cap['UPGN_max']
    URGN_min = R_cap['URGN_min']
    URGN_max = R_cap['URGN_max']
    URLs_min = R_cap['URLs_min']
    URLs_max = R_cap['URLs_max']

    
    'Declaração das principais variáveis auxiliares e dimensões'
    itmax = 10 # número máximo de iterações [ESTAMOS USANDO ATUALEMNTE V13 ESTE CRITÉRIO DE PARADA]
    nD = len(F0) # Número de variáveis de decisão
    nC = 14 #Numero de restriçoes dos produtos
    R=np.zeros(itmax) # VETOR DE RECEITA PARA PLOTAGEM
    B=np.zeros(itmax) # VETOR DE RECEITA_BASE PARA PLOTAGEM
    D=np.zeros(itmax) # VETOR DE desvio PARA PLOTAGEM
    # C4p=np.zeros(itmax)
    manip = np.zeros([itmax, nD]) #Matriz das var manipuladas para receita
    x =[] # variáveis de decisão
    desvio = 1e-3 # desvio inicial para início do processo iterativo [SE FOR USAD]...
    index=0 # contador de iterações (inicia com valor zero)
    f_OBJ=np.zeros(nD) # Definindo o vetor da função OBJETIVO
    dR_dF=np.zeros(nD) # Definindo o vetor das derivadas das Margens
    dC_dF=np.zeros([nD, nC]) #Definindo a matriz das derivadas das restriçoes dos produtos
    delta=np.zeros(nD) # Perturbação da derivada
    ZC_min = np.zeros(17) # valor mínimo de frações molares de reciclo da UPCGN para normalização do desvio
    ZC_max = np.ones(17)  # valor máximo de frações molares de reciclo da UPCGN para normalização do desvio 
    ZF_min = 0.6e6  # valor mínimo de vazão de reciclo da UPCGN para normalização do desvio [atribuído heuristicamente]
    ZF_max = 9e6    # valor máximo de vazão de reciclo da UPCGN para normalização do desvio [atribuído heuristicamente]
    ix = np.linspace(0, itmax, itmax) # vetor de iterações para plotagem
    flag_max=np.zeros(14) # flag para gravar restricoes de mínimo já violadas
    flag_min=np.zeros(14) # flag para gravar restricoes de máximo já violadas
    
    'Ativando a simulação Essencial'
    simCase.Solver.CanSolve = True # Isso é necessário, pois nesse momento vamos ler algumas variáveis como reciclo da UPCGN
    
    'Obtendo os valores das vazões e frações molares da corrente de reciclo [DE saída] da UPCGN -> necessário para o processo ITERATIVO'
    G_Rec_UPCGNs_in = MT_main['Gás de Reciclo UPCGNs RCY'].MolarFlow.GetValue('m3/d_(gas)') # valor atual lido da vazão em m3/d de gás do reciclo da UPCGn
    G_Rec_UPCGNs_C_in = MT_main['Gás de Reciclo UPCGNs RCY'].ComponentMolarFractionValue # # valor atual lido da fração molar dos componentes do gás do reciclo da UPCGn
    
    
    'Especificando o tipo de função-objetivo'
    
    mapping = {'Receita': (1.0, 0.0), 'Custo': (0.0, 1.0), 'Margem': (1.0, 1.0)} # (FLAGS) valores binários a serem exportados para a planilha f_OBJ
    Rec, Ct = mapping.get(FObj_type, (1.0, 0.0)) # Especificação dos valores de R:Receita e C:Custo. [OBS: Valor Default: R=1, C=0]
    SS_f_OBJ.Cell('D2').CellValue = Rec  # A célula D2 recebe a flag da receita
    SS_f_OBJ.Cell('D3').CellValue = Ct  # A célula D3 recebe a flag do custo
    
    # Enviando os Preços para a planilha receitas da simulação em Hysys
    #====================================================================================================================
    SS_Receita.Cell('D2').CellValue = precos['LGN [USD/ MM btu]']
    SS_Receita.Cell('D3').CellValue = precos['GV [USD/ MM btu]']
    SS_Receita.Cell('D4').CellValue = precos['GLP [USD/ MM btu]']
    SS_Receita.Cell('D5').CellValue = precos['C5p [USD/ MM btu]']
    SS_Receita.Cell('D6').CellValue = precos['GASDUC [USD/ MM btu]']
    #====================================================================================================================
    
    # X0 = np.array(G_Rec_UPCGNs_C_0) # composição da corrente de reciclo de saída da UPCGN em forma vetorial
    # XO4 = np.array(G_Rec_UPCGNs_C) # composição da corrente de reciclo de entrada da UPCGN em forma vetorial
    # desvioX = (X0-XO4)/(XO4+1e-10) # valor do desvio inicial das composições (é um vetor)
    # desvioX = la.norm(desvioX) # definindo a norma do desvio das composições
    # desvio = abs( (G_Rec_UPCGNs - G_Rec_UPCGNs_0) / G_Rec_UPCGNs_0 ) + desvioX + 1E-3 # (O 1E-3 É PARA FORÇAR RODAR A PRIMEIRA VEZ) [Desvio= Desvio Vazão + Desvio Composição]
    # C4_L=[] # definindo valor inicial do vetor de c4+
    
    'Valores iniciais das variáveis de decisão (direto da planilha Input_Data)'
    x0 = list(F0.values())  # VALORES INICIAIS DAS VARIÁVEIS MANIPULADAS CONVERTENDO VALORES PARA LISTA (FACILITA)

    # 'Obtenção da Receita_Base, Corrente de Reciclo UPCGN e Vazões_Base das Unidades'  
    # Receita_Base, Reciclo_UPCGN, Cargas_Unidades = SimulaLP(x0, G_Rec_UPCGNs_in,G_Rec_UPCGNs_C_in, obj) # Reciclo_UPCGN -> Dicionário com Vazões e Composições do reciclo UPCGN 
                                                                                                        # Cargas_Unidades -> Vazão de carga das unidades
    # 'Obtenção dos valores-base das condições dass correntes de produto (GV e GLP)'
    # y_base, ppm_H2O_GV = Restricoes(x0,0, obj)
    
    # 'Desativando a simulação Essencial'
    # simCase.Solver.CanSolve = False # Desativo (mas não desligo) a simulação pois será ativada mais tarde....   


    '''
    SEÇÃO[2] PROCESSO ITERATIVO
    *************************************************************************************************************************************
    '''
    'Início do Processo Iterativo'
    # while (abs(desvio) > tol): # PROCESSO ITERATIVO... [não estamos usando desvio nessa versão]
    while (abs(index) < itmax ): # PROCESSO ITERATIVO...[enquanto for menos que itemax iterações]

        'Obtenção da Função_Objetivo_Base, Corrente de Reciclo UPCGN e Vazões_Base das Unidades'  
        f_OBJ_Base, Reciclo_UPCGN, Cargas_Unidades, Receita, Custo = SimulaLP(x0, G_Rec_UPCGNs_in,G_Rec_UPCGNs_C_in, obj) # Reciclo_UPCGN -> Dicionário com Vazões e Composições do reciclo UPCGN 
                                                                                                      # Cargas_Unidades -> Vazão de carga das unidades
        'Obtenção dos valores-base das condições das correntes de produto (GV e GLP)'
        y_base = Spec_prods(x0, 0, obj)
        
        index = index + 1 # Atualização do contador
        
        'Cálculo das Derivadas'
        
        if index<5: # Só atualiza a derivada nas primeiras iterações....[Default = 5]
            # delta=np.zeros(nD)
            for i in range(nD): # Para cada variável de decisão calcular a derivada da Receita em relação à variável de decisão atual
                delta[i]=1e4# Valor da perturbação [Especifciação heurística, em princípio]
                x = x0+delta # Incremento da perturbação na variável base (CÁLCULO VETORIAL)
                f_OBJ[i], Reciclo_UPCGN, Cargas_Unidades, Receita, Custo = SimulaLP(x, G_Rec_UPCGNs_in,G_Rec_UPCGNs_C_in, obj) # Cálculo da Receita para o novo ponto
                y = Spec_prods(x, 0, obj)
                dR_dF[i] = ( f_OBJ[i] - f_OBJ_Base ) / delta[i] # Cálculo da Derivada [usando o ponto_base]
                dC_dF[i,:] = (y - y_base) / delta[i] # Cálculo da Derivada das restriçoes
                delta[i]=0 # Zerando o incremento

        'Atribuindo os valores base das variáveis de decisão às variáveis do modelo LINEAR'
        
        A1_0 =   x0[0]  # A1 # G_295toGASDUC_0
        A2_0 =   x0[1]  # A2 # G_295toURGN_0
        A3_0 =   x0[2]  # A3 # G_295toURLs_0
        A4_0 =   x0[3]  # A4 # G_295toUPGN_0
        
        B1_0 =   x0[4]  # B1 #  G_299toGASDUC_0
        B2_0 =   x0[5]  # B2 # G_299toURGN_0
        B3_0 =   x0[6]  # B3 #  G_299toURLs_0
        B4_0 =   x0[7]  # B4 # G_299toUPGN_0
        
        C3_0 =   x0[8]  # C3 # G_302toURLs_0
        C4_0 =   x0[9]  # C4 # G_302toUPGN_0
        C5_0 =   x0[10] # C5 # G_302toMIX_0 
        
        'Derivadas parciais da Função Objetivo no ponto base (Delta f_OBJ / Delta Vazão) [$/(m3/d)]'
        
        dF_A1   = dR_dF[0]  # derivada da f_OBJ em relação ao A1   # d_295toGASDUC
        dF_A2   = dR_dF[1]  # derivada da f_OBJ em relação ao A2   # d_295toURGN
        dF_A3   = dR_dF[2]  # derivada da f_OBJ em relação ao A3   # d_295toURLs
        dF_A4   = dR_dF[3]  # derivada da f_OBJ em relação ao A4   # d_295toUPGN
        
        dF_B1   = dR_dF[4]  # derivada da f_OBJ em relação ao B1   # d_299toGASDUC
        dF_B2   = dR_dF[5]  # derivada da f_OBJ em relação ao B2   # d_299toURGN
        dF_B3   = dR_dF[6]  # derivada da f_OBJ em relação ao B3   # d_299toURLs
        dF_B4   = dR_dF[7]  # derivada da f_OBJ em relação ao B4   # d_299toUPGN
        
        dF_C3   = dR_dF[8]  # derivada da f_OBJ em relação ao C3   # d_302toURLs
        dF_C4   = dR_dF[9]  # derivada da f_OBJ em relação ao C4   # d_302toUPGN 
        dF_C5   = dR_dF[10] # derivada da f_OBJ em relação ao C5   # d_302toMIX
        
        'Derivadas parciais das restrições no ponto base (Delta f_OBJ / Delta Vazão) [$/(m3/d)]'

        dC_A1   = dC_dF[0,:]  # derivada da f_OBJ em relação ao A1   # d_295toGASDUC
        dC_A2   = dC_dF[1,:]  # derivada da f_OBJ em relação ao A2   # d_295toURGN
        dC_A3   = dC_dF[2,:]  # derivada da f_OBJ em relação ao A3   # d_295toURLs
        dC_A4   = dC_dF[3,:]  # derivada da f_OBJ em relação ao A4   # d_295toUPGN
        
        dC_B1   = dC_dF[4,:]  # derivada da f_OBJ em relação ao B1   # d_299toGASDUC
        dC_B2   = dC_dF[5,:]  # derivada da f_OBJ em relação ao B2   # d_299toURGN
        dC_B3   = dC_dF[6,:]  # derivada da f_OBJ em relação ao B3   # d_299toURLs
        dC_B4   = dC_dF[7,:]  # derivada da f_OBJ em relação ao B4   # d_299toUPGN
        
        dC_C3   = dC_dF[8,:]  # derivada da f_OBJ em relação ao C3   # d_302toURLs
        dC_C4   = dC_dF[9,:]  # derivada da f_OBJ em relação ao C4   # d_302toUPGN 
        dC_C5   = dC_dF[10,:] # derivada da f_OBJ em relação ao C5   # d_302toMIX




        
        'Criação do objeto "model" para construção do modelo no pulp'
        model = LpProblem(name="Essencial_LP", sense=LpMaximize)
        
        'Definição das variaveis de decisão no PULP'
                   
        A1 = LpVariable("Gás de 295 para GASDUC", lowBound=1e-6, upBound=GASDUC_max) # A1 # G_295toGASDUC
        A2 = LpVariable("Gás de 295 para URGN", lowBound=1,upBound=URGN_max)        # A2 # G_295toURGN
        A3 = LpVariable("Gás de 295 para URLs", lowBound=1e-6, upBound=URLs_max)       # A3 # G_295toURLs
        A4 = LpVariable("Gás de 295 para UPGN", lowBound=1e-6, upBound=UPGN_max)       # A4 # G_295toUPGN
        
        B1 = LpVariable("Gás de 299 para GASDUC", lowBound=1e-6, upBound=GASDUC_max) # B1 # G_299toGASDUC
        B2   = LpVariable("Gás de 299 para URGN", lowBound=1, upBound=URGN_max)     # B2 # G_299toURGN
        B3   = LpVariable("Gás de 299 para URLs", lowBound=1e-6, upBound=URLs_max)     # B3 # G_299toURLs 
        B4   = LpVariable("Gás de 299 para UPGN", lowBound=0, upBound=UPGN_max)     # B4 # G_299toUPGN
        
        C3 = LpVariable("Gás de 302 para URLs", lowBound=1e-6, upBound=URLs_max)  # C3 # G_302toURLs
        C4 = LpVariable("Gás de 302 para UPGN", lowBound=1e-6, upBound=UPGN_max)  # C4 # G_302toUPGN
        C5  = LpVariable("Gás de 302 para MIX", lowBound=1e-6, upBound=MIX_max) # C5 # G_302toMIX
        
        
        'INCLUSÃO DE RESTRIÇÕES ATIVAS [só vamos incluir no LP as restrições ativas]'
       
        'avaliação das restrições mínimas'
        itens_min = list(R_min.values())
        keys = list(R_min.keys())        
        for k in range(np.size(y_base)):
            if y_base[k]<itens_min[k] or flag_min[k]!=0:
                if flag_min[k] == 0:
                    print('************************************')
                    print('Violação do valor mínimo: ', keys[k], '=', itens_min[k], '>', y_base[k]  )
                    print('Incluindo restrição no LP')
                    print('************************************')
                else:
                    print('************************************')
                    print('Mantendo restrição no LP já violada previamente')
                    print('Violação do valor mínimo anterior: ', keys[k], '<', itens_min[k]  )
                    print('************************************')
                val_rest = (y_base[k] + 
                            dC_A1[k]*(A1-A1_0)   + dC_A2[k]*(A2-A2_0) + dC_A3[k]*(A3-A3_0) + dC_A4[k]*(A4-A4_0) + 
                            dC_B1[k]*(B1-B1_0)   + dC_B2[k]*(B2-B2_0) + dC_B3[k]*(B3-B3_0) + dC_B4[k]*(B4-B4_0) +
                            dC_C3[k]*(C3-C3_0)   + dC_C4[k]*(C4-C4_0) + dC_C5[k]*(C5-C5_0)) 
                val_rest = (y_base[k] + dC_C5[k]*(C5-C5_0))
                model += ((val_rest) - float(itens_min[k]) >= 0, keys[k]) # Restrição Incluída
                flag_min[k]=1
        'avaliação das restrições máximas'            
        itens_max = list(R_max.values())
        keys = list(R_max.keys())        
        for k in range(np.size(y_base)):
            if y_base[k]>itens_max[k] or flag_max[k]!=0:
                if flag_max[k] == 0:
                    print('************************************')
                    print('Violação do valor máximo: ', keys[k],'=', itens_max[k], '<', y_base[k])
                    print('Incluindo restrição no LP')
                    print('************************************')
                else:
                    print('************************************')
                    print('Mantendo restrição no LP já violada previamente')
                    print('Violação do valor máximo anterior: ', keys[k], '>', itens_max[k]  )
                    print('************************************')
                val_rest = (y_base[k] + 
                            dC_A1[k]*(A1-A1_0)   + dC_A2[k]*(A2-A2_0) + dC_A3[k]*(A3-A3_0) + dC_A4[k]*(A4-A4_0) + 
                            dC_B1[k]*(B1-B1_0)   + dC_B2[k]*(B2-B2_0) + dC_B3[k]*(B3-B3_0) + dC_B4[k]*(B4-B4_0) +
                            dC_C3[k]*(C3-C3_0)   + dC_C4[k]*(C4-C4_0) + dC_C5[k]*(C5-C5_0)) 
                val_rest = (y_base[k] + dC_C5[k]*(C5-C5_0))
                model += ((val_rest - float(itens_max[k])) <= 0, keys[k]) # Restrição Incluída
                flag_max[k] = 1
        'Função Objetivo (Linealizada no ponto base)'
        model += (f_OBJ_Base + 
                  dF_B1*(B1-B1_0)              + dF_A1*(A1-A1_0)       +
                  dF_B2*(B2-B2_0)              + dF_A2*(A2-A2_0)       + 
                  dF_B3*(B3-B3_0)              + dF_A3*(A3-A3_0)       +
                  dF_B4*(B4-B4_0)              + dF_A4*(A4-A4_0)       +
                  dF_C3*(C3-C3_0)              + dF_C4*(C4-C4_0)       + dF_C5*(C5-C5_0)   )
        
        'Restrições do Modelo'
          
        'IGUALDADE: EQUAÇÕES DE CONSERVAÇÃO DE MASSA'

        model += (C3 + C4 + C5 == G_302, "Alocar todo o gás do 302")
        model += (B1 +  B2 + B3 + B4 == G_299, "Alocar todo o gás do 299")
        model += (A1 + A2 +  A3 + A4 == G_295 + G_Rec_UPCGNs_in, "Alocar todo o gás do 295 e do Reciclo")

        'DESIGUALDADE: CAPACIDADE DAS UNIDADES'

        model += (GASDUC_min - (A1 + B1)              <= 0, "GASDUC mínimo")
        model += (             (A1 + B1) - GASDUC_max <= 0, "GASDUC máximo")
        
        model += (             MIX_min - C5 <= 0, "MIX mínimo")
        model += (C5 - MIX_max              <= 0, "MIX máximo")
        
        model += (UPGN_min - (A4 + B4 + C4)             <=0 , "UPGN mínimo")
        model += (           (A4 + B4 + C4) - UPGN_max <= 0, "UPGN máximo")
        
        model += (URGN_min - (A2 + B2)            <= 0, "URGN mínimo")
        model += (           (A2 + B2) - URGN_max <= 0, "URGN máximo")
        
        model += (URLs_min - (A3 + B3 + C3)            <= 0, "URLs mínimo")
        model += (           (A3 + B3 + C3) - URLs_max <= 0, "URLs máximo")
        # model += (           (C4_L) - C4_max <= 0, "C4 máximo") # Restrição de C4+ (está em fração) 
        
        'Executa otimização'
        status = model.solve(pulp.PULP_CBC_CMD(msg=False))
        print(status)

        'Redefinindo as variáveis de decisão com valores ótimos, para a próxima iteração'
        'NOTA: Vamos utilizar os valores ótimos das variáveis de decisão e realizar a simulção com esses valores para verificar a função_Objetivo'
        
        x[0] =A1.varValue      #A1           # Redefinindo as variáveis de decisão com valores ótimos
        x[1] =A2.varValue      #A2
        x[2] =A3.varValue      #A3
        x[3] =A4.varValue      #A4
        x[4] =B1.varValue      #B1
        x[5] =B2.varValue      #B2
        x[6] =B3.varValue      #B3
        x[7] =B4.varValue      #B4
        x[8] =C3.varValue      #C3 
        x[9] =C4.varValue      #C4
        x[10]=C5.varValue      #C5
        
        'Tratamendo de dados.. NOTA: Evitar vazões negativas'
        for i in range(nD):
            if x[i]<0:  # se alguma vazão for negativa, atribuir valor zero
                x[i]=1e-5
                cod_SLP = 1  # flag da função SLP para indicar que ocorreram vazões negativas
            else:
                cod_SLP = 0  # flag da função SLP para indicar que está ok
        
        'Obtenção da Receita_Simulada, Corrente de Reciclo UPCGN e Vazões_Base das Unidades' 
        f_OBJ_max, Reciclo_UPCGN, Cargas_Unidades, Receita, Custo = SimulaLP(x, G_Rec_UPCGNs_in,G_Rec_UPCGNs_C_in, obj) # Cálculo da Função-Onjetivo para o novo ponto
        x0  = x
        'Cálculo do Desvio' 
        G_Rec_UPCGNs_C_out = Reciclo_UPCGN['G_Rec_UPCGNs_C_out'] # Composição da corrente de reciclo da UPCNGN na saída
        G_Rec_UPCGNs_out   = Reciclo_UPCGN['G_Rec_UPCGN_out']      # Vazão de reciclo da UPCNGN na saída
        
        ZC_in  = ( np.array(G_Rec_UPCGNs_C_in) - ZC_min ) / (ZC_max - ZC_min)
        ZF_in  = ( np.array(G_Rec_UPCGNs_in) - ZF_min ) / (ZF_max - ZF_min)
        ZF_out = ( np.array(G_Rec_UPCGNs_out) - ZF_min ) /  (ZF_max - ZF_min)  # vazão da corrente de reiclo da UPCGN 
        ZC_out = ( np.array(G_Rec_UPCGNs_C_out) -  ZC_min ) / (ZC_max - ZC_min)  # composição da corrente de reiclo da UPCGN
        desvio_comp = (ZC_in-ZC_out)/(ZC_out+1e-10) # o valor 1e-10 é para evitar divisão por zero
        desvio_comp = la.norm(desvio_comp)
        desvio_vazão = abs( (ZF_in - ZF_out) / ZF_out )
        desvio = desvio_vazão + desvio_comp # cálculo do desvio
        desvio = np.linalg.norm(f_OBJ_max - f_OBJ_Base)  # Inserindo a norma da função objetivo como desvio...
        G_Rec_UPCGNs_in = G_Rec_UPCGNs_out # atualização da vazão de reciclo
        G_Rec_UPCGNs_C_in = G_Rec_UPCGNs_C_out # atualização da composição do reciclo
        
        ###################################################################################################################
        'Impressão de Resultados no Terminal'
        
        CARGA_G_URGN = Cargas_Unidades['CARGA_G_URGN']
        CARGA_G_URLI = Cargas_Unidades['CARGA_G_URLI']
        CARGA_G_URLII = Cargas_Unidades['CARGA_G_URLII']
        CARGA_G_URLIII = Cargas_Unidades['CARGA_G_URLIII']
        CARGA_G_UPGN = Cargas_Unidades['CARGA_G_UPGN']
        
        R[index-1]=f_OBJ_max # Funçao Objetivo calculada pelo Hysys
        B[index-1]=f_OBJ_Base # Funçao Objetivo base
        D[index-1]=desvio # desvio
        manip[index-1,:] = x # variáveis manipuladas
        
        'Imprimindo os resultados no TERMINAL'
        print('#'*50)
        print(f"Resultados iteração {index-1}:")
        print("Convergência: ", model.status)
        # The status of the solution is printed to the screen
        print("Status:", LpStatus[model.status])
        print(FObj_type, model.objective.value())
        print('Gás de reciclo: ', G_Rec_UPCGNs_in)
        print('Composicao do reciclo: ', 'C1=', G_Rec_UPCGNs_C_in[0], 'C2=', G_Rec_UPCGNs_C_in[1], 'C3=', G_Rec_UPCGNs_C_in[2]
              , 'iC4=', G_Rec_UPCGNs_C_in[3], 'nC4=', G_Rec_UPCGNs_C_in[4], 'iC5=', G_Rec_UPCGNs_C_in[5], 'C6=', G_Rec_UPCGNs_C_in[6]
              , 'C7=', G_Rec_UPCGNs_C_in[7], 'C8=', G_Rec_UPCGNs_C_in[8] , 'C9=', G_Rec_UPCGNs_C_in[9], 'C10=', G_Rec_UPCGNs_C_in[10]
              , 'N2=', G_Rec_UPCGNs_C_in[11], 'Co2=', G_Rec_UPCGNs_C_in[12], 'H2O=', G_Rec_UPCGNs_C_in[13]
              , 'H2S=', G_Rec_UPCGNs_C_in[14], 'EGLYC=', G_Rec_UPCGNs_C_in[15])
        print('*'*50)
        print('Manipuladas:')
        for var in model.variables():
            print(f"{var.name}: {var.value()}")
        print('*'*50)
        print('Restrições:')
        for name, constraint in model.constraints.items():
            print(f"{name}: {constraint.value()}")
        print('*'*50)
        print('Cargas totais para as unidades:')
        print('GASDUC: ', B1.value() + A1.value())
        print('MIX: ', C5.value())
        print('UPGN: ', A4.value() + B4.value() + C4.value())
        print('URGN: ', A2.value() + B2.value())
        print('URLs: ', A3.value() + B3.value() + C3.value())
        print('*'*50)
        
        # Gerando o arquivo .lp da otimização
        model.writeLP("Cabiunas_LP.lp")
        
        print( FObj_type, "_Base: ", f_OBJ_Base)
        print( FObj_type, "_max: ", f_OBJ_max)
        # Receita
        print( "Receita", Receita)
        print( "Custo", Custo)
        print( "Margem", Receita-Custo)
        print('Desvio:', D)
        print('*'*50)
        print('CARGA_GAS_URGN:', CARGA_G_URGN, '||', 'URGN:', A2.value() + B2.value(), 'CONDENSADO:', ((A2.value() + B2.value())-CARGA_G_URGN ) )
        URLI = (C3.value() + B3.value() + A3.value() )/3
        print('CARGA_GAS_URLI:', CARGA_G_URLI, '||', 'URLI:', URLI, 'CONDENSADO:', (CARGA_G_URLI - URLI))
        print('CARGA_GAS_URLII:', CARGA_G_URLII, '||', 'URLII:', URLI, 'CONDENSADO:', (CARGA_G_URLII - URLI))
        print('CARGA_GAS_URLIII:', CARGA_G_URLIII, '||', 'URLIII:', URLI, 'CONDENSADO:', (CARGA_G_URLIII - URLI))
        UPGN = C4.value() + B4.value() + A4.value()
        print('CARGA_GAS_UPGN:', CARGA_G_UPGN, '||', 'UPGN:', UPGN, 'CONDENSADO:', (UPGN - CARGA_G_UPGN))
        final_time = timeit.default_timer()
        tempo = final_time - init_time 
        print('Tempo de execução (seg) ', tempo)
        
        'Plotando as derivadas'    
        plot_derivatives(dR_dF, index)
        
        'Relatório com histórico de cálculos da SLP' # Ainda Implementando...
        rel_SLP = {'FOBJ_base': R,
                   'FOBJ': B,
                   'Desvio': D,
                   'Iterações': ix,
                   'Manipuladas':x,
                   }
    
    return cod_SLP, model, rel_SLP
