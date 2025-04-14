import streamlit as st
import locale
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from io import BytesIO
import platform
import uuid # Para chaves únicas

# --- PRIMEIRA COISA: Configuração da Página ---
st.set_page_config(page_title="Fechamento de Caixa Detalhado", layout="wide")

# --- Configuração de Localização (Moeda Brasileira) ---
# (Mantém a mesma lógica de antes para tentar definir o locale e ter o fallback)
try:
    if platform.system() == "Windows":
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    else:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

    def format_currency(value):
        try:
            return locale.currency(value, grouping=True, symbol='R$')
        except (TypeError, ValueError):
            return "R$ 0,00"
except locale.Error:
    #st.warning("Locale 'pt_BR.UTF-8' ou 'Portuguese_Brazil.1252' não encontrado. Usando formatação de moeda alternativa.")
    def format_currency(value):
        try:
            return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (TypeError, ValueError):
             return "R$ 0,00"

# --- Inicialização do Session State para listas ---
if 'lista_entradas' not in st.session_state:
    st.session_state.lista_entradas = [] # Formato: [{'id': uuid, 'descricao': str, 'valor': float}]
if 'lista_saidas' not in st.session_state:
    st.session_state.lista_saidas = [] # Formato: [{'id': uuid, 'descricao': str, 'valor': float}]

# --- Função para Gerar o PDF (Modificada para aceitar totais) ---
# (A função gerar_pdf permanece quase a mesma, mas recebe os totais calculados)
def gerar_pdf(data_fechamento, responsavel, saldo_inicial, total_entradas_registradas, total_saidas_registradas, saldo_esperado, saldo_contado, diferenca, observacoes=""):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    margem_esquerda = 2 * cm
    margem_superior = height - 2 * cm
    espaco_linha = 0.7 * cm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(margem_esquerda, margem_superior, "Relatório de Fechamento de Caixa (Dinheiro)")
    c.setFont("Helvetica", 11)
    c.drawString(margem_esquerda, margem_superior - espaco_linha, f"Data: {data_fechamento.strftime('%d/%m/%Y')}")
    c.drawString(margem_esquerda, margem_superior - 2 * espaco_linha, f"Responsável: {responsavel}")

    y_pos = margem_superior - 4 * espaco_linha

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margem_esquerda, y_pos, "Resumo do Caixa:")
    y_pos -= espaco_linha * 1.5

    c.setFont("Helvetica", 11)
    items = [
        ("Saldo Inicial (Fundo de Troco):", saldo_inicial),
        # Alterado para refletir que são totais das listas
        ("(+) Total Entradas Registradas (Dinheiro):", total_entradas_registradas),
        ("(-) Total Saídas Registradas (Dinheiro):", total_saidas_registradas),
        ("(=) Saldo Final Esperado em Dinheiro:", saldo_esperado),
        ("Valor Contado em Dinheiro:", saldo_contado),
        ("Diferença (Sobra/Falta):", diferenca),
    ]

    # Ajuste a largura do label se necessário (mantenha o valor que funcionou antes, ex: 9.5*cm)
    largura_label = 9.5 * cm

    for label, value in items:
        c.drawString(margem_esquerda, y_pos, label)
        valor_formatado = format_currency(value if isinstance(value, (int, float)) else 0.0)
        c.drawRightString(margem_esquerda + largura_label, y_pos, valor_formatado)
        y_pos -= espaco_linha

    # --- Indicação Sobra/Falta (igual antes) ---
    y_pos -= espaco_linha * 0.5
    if diferenca > 0:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margem_esquerda + largura_label + 0.5*cm, y_pos + espaco_linha, "(SOBRA)")
    elif diferenca < 0:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margem_esquerda + largura_label + 0.5*cm, y_pos + espaco_linha, "(FALTA)")
    else:
        c.setFont("Helvetica", 11)
        c.drawString(margem_esquerda + largura_label + 0.5*cm, y_pos + espaco_linha, "(CORRETO)")
    c.setFont("Helvetica", 11)

    # --- Observações e Assinatura (igual antes) ---
    y_pos -= espaco_linha * 1.5
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margem_esquerda, y_pos, "Observações:")
    y_pos -= espaco_linha
    # ... (resto da lógica de observações e assinatura igual) ...
    c.setFont("Helvetica", 11)
    if observacoes:
        linhas_obs = observacoes.split('\n')
        for linha in linhas_obs:
             if y_pos < 3 * cm:
                c.showPage()
                c.setFont("Helvetica", 11)
                y_pos = height - 2 * cm
             c.drawString(margem_esquerda, y_pos, linha)
             y_pos -= espaco_linha * 0.6
    else:
        c.drawString(margem_esquerda, y_pos, "Nenhuma observação.")

    y_pos = 4 * cm
    c.line(margem_esquerda, y_pos, width - margem_esquerda, y_pos)
    y_pos -= espaco_linha
    c.drawCentredString(width / 2, y_pos, "Assinatura do Responsável / Conferente")

    c.save()
    buffer.seek(0)
    return buffer

# --- Funções Auxiliares para manipular listas ---
def adicionar_entrada(descricao, valor):
    if valor > 0:
        st.session_state.lista_entradas.append({
            'id': uuid.uuid4(), # ID único para cada item
            'descricao': descricao or "Entrada Diversa",
            'valor': valor
        })
    else:
        st.warning("Valor da entrada deve ser maior que zero.")

def adicionar_saida(descricao, valor):
    if not descricao:
        st.warning("Descrição da saída é obrigatória.")
        return
    if valor > 0:
        st.session_state.lista_saidas.append({
            'id': uuid.uuid4(),
            'descricao': descricao,
            'valor': valor
        })
    else:
        st.warning("Valor da saída deve ser maior que zero.")

def remover_item(lista_key, item_id):
    st.session_state[lista_key] = [item for item in st.session_state[lista_key] if item['id'] != item_id]

# --- Interface Streamlit ---
st.title("Controle Detalhado de Caixa - Dinheiro")

# --- Inputs Iniciais (Data, Responsável, Saldo Inicial) ---
col1, col2 = st.columns(2)
with col1:
    data_fechamento = st.date_input("Data do Fechamento", date.today())
with col2:
    responsavel = st.text_input("Nome do Responsável/Operador", placeholder="Digite o nome")

saldo_inicial = st.number_input("1. Saldo Inicial (Fundo de Troco)", min_value=0.0, step=0.01, format="%.2f", key="saldo_inicial", value=0.0)

st.divider()

# --- Seção para Registrar Entradas e Saídas ---
col_input1, col_input2 = st.columns(2)

with col_input1:
    st.subheader("Registrar Nova Entrada (Dinheiro)")
    with st.form("form_entrada", clear_on_submit=True):
        desc_entrada = st.text_input("Descrição da Entrada (Opcional)", placeholder="Ex: Venda X, Suprimento Y")
        val_entrada = st.number_input("Valor da Entrada (R$)", min_value=0.01, step=0.01, format="%.2f")
        submitted_entrada = st.form_submit_button("Adicionar Entrada")
        if submitted_entrada:
            adicionar_entrada(desc_entrada, val_entrada)
            st.rerun() # Força o recarregamento para atualizar listas e totais

    st.subheader("Entradas Registradas")
    if not st.session_state.lista_entradas:
        st.caption("Nenhuma entrada registrada.")
    else:
        for item in st.session_state.lista_entradas:
            col_item1, col_item2, col_item3 = st.columns([4, 2, 1])
            col_item1.write(item['descricao'])
            col_item2.write(format_currency(item['valor']))
            col_item3.button("🗑️", key=f"rem_ent_{item['id']}", on_click=remover_item, args=('lista_entradas', item['id']))

with col_input2:
    st.subheader("Registrar Nova Saída (Dinheiro)")
    with st.form("form_saida", clear_on_submit=True):
        desc_saida = st.text_input("Descrição da Saída (Obrigatória)", placeholder="Ex: Pagto Fornecedor Z, Sangria")
        val_saida = st.number_input("Valor da Saída (R$)", min_value=0.01, step=0.01, format="%.2f")
        submitted_saida = st.form_submit_button("Adicionar Saída")
        if submitted_saida:
            adicionar_saida(desc_saida, val_saida)
            st.rerun() # Força o recarregamento

    st.subheader("Saídas Registradas")
    if not st.session_state.lista_saidas:
        st.caption("Nenhuma saída registrada.")
    else:
        for item in st.session_state.lista_saidas:
            col_item1, col_item2, col_item3 = st.columns([4, 2, 1])
            col_item1.write(item['descricao'])
            col_item2.write(format_currency(item['valor']))
            col_item3.button("🗑️", key=f"rem_sai_{item['id']}", on_click=remover_item, args=('lista_saidas', item['id']))

st.divider()

# --- Cálculos Totais a partir das listas ---
total_entradas = sum(item['valor'] for item in st.session_state.lista_entradas)
total_saidas = sum(item['valor'] for item in st.session_state.lista_saidas)

# --- Seção de Conferência Final (igual antes, mas usa os totais calculados) ---
st.subheader("Conferência Final do Caixa")

# Valor contado ainda é um input manual
saldo_contado = st.number_input("Valor Contado no Caixa (Dinheiro Físico)", min_value=0.0, step=0.01, format="%.2f", key="saldo_contado", value=0.0)

# Cálculo do saldo esperado e diferença
saldo_esperado = (saldo_inicial or 0.0) + total_entradas - total_saidas
diferenca = (saldo_contado or 0.0) - saldo_esperado

st.divider()

# --- Exibição dos Resultados (igual antes) ---
st.subheader("Resultado do Fechamento")
col_res1, col_res2, col_res3 = st.columns(3) # Adicionada coluna para totalizadores

with col_res1:
     st.metric(label="Total Entradas Registradas", value=format_currency(total_entradas))
     st.metric(label="Saldo Final Esperado (Dinheiro)", value=format_currency(saldo_esperado))

with col_res2:
    st.metric(label="Total Saídas Registradas", value=format_currency(total_saidas))
    # Exibe a diferença com cor e texto indicativo (Sobra/Falta/Correto)
    delta_text = f"{format_currency(diferenca)} {'(SOBRA)' if diferenca > 0 else '(FALTA)' if diferenca < 0 else '(CORRETO)'}"
    st.metric(label="Diferença (Contado - Esperado)", value=format_currency(diferenca), delta=delta_text)

# Aplica cor manualmente com base na diferença para melhor visualização (opcional)
with col_res3: # Usa a coluna 3 ou ajusta layout
    st.markdown("##") # Espaçamento
    if diferenca > 0:
        st.markdown(f"<p style='color: green; font-weight: bold; font-size: 1.1em;'>Status: {delta_text}</p>", unsafe_allow_html=True)
    elif diferenca < 0:
        st.markdown(f"<p style='color: red; font-weight: bold; font-size: 1.1em;'>Status: {delta_text}</p>", unsafe_allow_html=True)
    else:
        st.markdown(f"<p style='color: blue; font-weight: bold; font-size: 1.1em;'>Status: {delta_text}</p>", unsafe_allow_html=True)


st.divider()

# --- Campo de Observações e Botão de Download (igual antes, mas passa os totais) ---
observacoes = st.text_area("Observações (Opcional)", placeholder="Registre aqui qualquer evento relevante, justificativa para diferenças, etc.")

st.divider()

if st.button("Gerar Relatório PDF Final"):
    if not responsavel:
        st.error("Por favor, informe o nome do responsável.")
    else:
        nome_arquivo = f"Fechamento_Caixa_{responsavel.replace(' ','_')}_{data_fechamento.strftime('%Y%m%d')}.pdf"

        # Passa os TOTAIS calculados das listas para a função gerar_pdf
        pdf_bytes = gerar_pdf(
            data_fechamento,
            responsavel,
            saldo_inicial or 0.0,
            total_entradas, # Passa o total calculado
            total_saidas,   # Passa o total calculado
            saldo_esperado,
            saldo_contado or 0.0,
            diferenca,
            observacoes
        )

        st.download_button(
            label="Baixar PDF do Fechamento",
            data=pdf_bytes,
            file_name=nome_arquivo,
            mime="application/pdf"
        )
        st.success(f"Relatório PDF '{nome_arquivo}' gerado com sucesso!")
