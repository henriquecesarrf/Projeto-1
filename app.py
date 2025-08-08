import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Análise Financeira Completa", layout="wide")
st.title("📊 Análise Financeira de Projetos")

# --- Funções auxiliares ---
def calcular_vpl(fluxos_completos, tma):
    """
    fluxos_completos = [investimento_inicial, FC1, FC2, ...]
    """
    return sum([fc / (1 + tma) ** t for t, fc in enumerate(fluxos_completos)])

def calcular_tir(fluxos, max_iter=1000, tolerancia=1e-6):
    """
    Calcula a TIR usando método numérico robusto
    """
    sinais = [1 if f >= 0 else -1 for f in fluxos]
    if sum(sinais) == len(fluxos) or sum(sinais) == -len(fluxos):
        return None  # Todos positivos ou todos negativos

    def vpl(taxa):
        return sum([f / (1 + taxa)**t for t, f in enumerate(fluxos)])
    
    def vpl_derivada(taxa):
        return sum([-t * f / (1 + taxa)**(t+1) for t, f in enumerate(fluxos) if t > 0])

    taxa = 0.1
    for _ in range(max_iter):
        v = vpl(taxa)
        if abs(v) < tolerancia:
            return taxa * 100
        
        derivada = vpl_derivada(taxa)
        if abs(derivada) < 1e-10:
            break
            
        taxa = taxa - v / derivada
    
    esquerda, direita = -0.99, 1.0
    for _ in range(max_iter):
        if direita - esquerda < tolerancia:
            break
        meio = (esquerda + direita) / 2
        if vpl(esquerda) * vpl(meio) < 0:
            direita = meio
        else:
            esquerda = meio
    
    tir_calculada = (esquerda + direita) / 2 * 100
    return tir_calculada if abs(vpl((esquerda + direita)/2)) < tolerancia else None

def calcular_payback_descontado(fluxos_completos, tma):
    """
    fluxos_completos = [investimento_inicial, FC1, FC2, ...]
    Calcula o Payback Descontado.
    """
    acumulado = 0
    for t, fc in enumerate(fluxos_completos):
        fluxo_desc = fc / ((1 + tma) ** t)
        acumulado += fluxo_desc
        if acumulado >= 0:
            if t == 0:
                return 0
            acumulado_sem_ano = acumulado - fluxo_desc
            return (t - 1) + (abs(acumulado_sem_ano) / fluxo_desc)
    return None

# --- Entradas do usuário ---
with st.expander("📋 Dados do Projeto", expanded=True):
    col1, col2 = st.columns(2)
    
    with col1:
        investimento_inicial = st.number_input("Investimento inicial (R$)", value=-100.0, format="%.2f")
        tma_base = st.slider("TMA base (%)", min_value=0.0, max_value=30.0, value=10.0, step=0.1) / 100
    
    with col2:
        num_anos = st.number_input("Número de anos", min_value=1, max_value=20, value=3)
        
        st.markdown("**Fluxos de Caixa por Ano**")
        fluxos = []
        for ano in range(num_anos):
            fluxo = st.number_input(f"Ano {ano+1} (R$)", value=60.0, format="%.2f", key=f"fluxo_{ano}")
            fluxos.append(fluxo)

# --- Cálculos principais ---
fluxos_com_investimento = [investimento_inicial] + fluxos
vpl_base = calcular_vpl(fluxos_com_investimento, tma_base)
tir = calcular_tir(fluxos_com_investimento) if investimento_inicial < 0 else None
payback = calcular_payback_descontado(fluxos_com_investimento, tma_base)

# --- Resultados ---
st.divider()
st.header("📈 Resultados Financeiros")

col_res1, col_res2, col_res3 = st.columns(3)
with col_res1:
    st.metric("VPL", f"R$ {vpl_base:,.2f}")
with col_res2:
    if tir is None:
        st.metric("TIR", "N/A", 
                 help="TIR não calculável - verifique se o investimento inicial é negativo e há variação nos fluxos")
    else:
        st.metric("TIR", f"{tir:.2f}%")
with col_res3:
    payback_txt = f"{payback:.2f} anos" if payback else "Não recuperado"
    st.metric("Payback Descontado", payback_txt)

# Interpretação
if vpl_base > 0:
    st.success("✅ O projeto é VIÁVEL pelo método do VPL")
else:
    st.error("❌ O projeto é INVIÁVEL pelo método do VPL")

if tir:
    if tir > tma_base*100:
        st.success(f"✅ TIR ({tir:.2f}%) superior à TMA ({tma_base*100:.2f}%)")
    else:
        st.error(f"❌ TIR ({tir:.2f}%) inferior à TMA ({tma_base*100:.2f}%)")

# --- Análise de Sensibilidade ---
st.divider()
st.header("🔍 Análise de Sensibilidade")

tab1, tab2 = st.tabs(["Variação da TMA", "Variação dos Fluxos"])

with tab1:
    st.subheader("Sensibilidade do VPL à TMA")
    tma_min = st.slider("TMA mínima (%)", 0.0, 30.0, 5.0, step=0.5, key="tma_min") / 100
    tma_max = st.slider("TMA máxima (%)", 0.0, 30.0, 15.0, step=0.5, key="tma_max") / 100
    
    tma_range = np.linspace(tma_min, tma_max, 20)
    vpls_tma = [calcular_vpl(fluxos_com_investimento, tma) for tma in tma_range]
    
    fig1, ax1 = plt.subplots(figsize=(10,5))
    ax1.plot(tma_range*100, vpls_tma, 'b-o')
    ax1.axhline(0, color='r', linestyle='--')
    ax1.set_xlabel("TMA (%)")
    ax1.set_ylabel("VPL (R$)")
    ax1.set_title("Variação do VPL com a TMA")
    ax1.grid(True)
    st.pyplot(fig1)

with tab2:
    st.subheader("Sensibilidade do VPL aos Fluxos")
    variacao = st.slider("Variação dos fluxos (%)", -50, 50, 0)
    
    fluxos_var = [fluxos_com_investimento[0]] + [f * (1 + variacao/100) for f in fluxos]
    vpl_var = calcular_vpl(fluxos_var, tma_base)
    
    st.metric("Novo VPL", f"R$ {vpl_var:,.2f}", delta=f"{variacao}% nos fluxos")
    
    variacoes = np.linspace(-0.5, 0.5, 20)
    vpls_fluxo = [calcular_vpl([fluxos_com_investimento[0]] + [f * (1 + v) for f in fluxos], tma_base) for v in variacoes]
    
    fig2, ax2 = plt.subplots(figsize=(10,5))
    ax2.plot(variacoes*100, vpls_fluxo, 'g-s')
    ax2.axhline(0, color='r', linestyle='--')
    ax2.set_xlabel("Variação dos Fluxos (%)")
    ax2.set_ylabel("VPL (R$)")
    ax2.set_title("Sensibilidade do VPL aos Fluxos de Caixa")
    ax2.grid(True)
    st.pyplot(fig2)

# --- Fundamentação Teórica ---
with st.expander("📚 Fundamentação Teórica"):
    st.markdown("""
    ### Métodos de Avaliação Financeira
    
    **VPL (Valor Presente Líquido):**
    $$
    VPL = \\sum_{t=0}^{n} \\frac{FC_t}{(1 + TMA)^t}
    $$
    Onde \(FC_0\) é o investimento inicial (normalmente negativo).
    
    **TIR (Taxa Interna de Retorno):**
    Taxa de desconto que torna o VPL igual a zero.
    
    **Payback Descontado:**
    Tempo necessário para recuperar o investimento, considerando o valor do dinheiro no tempo.
    """)
