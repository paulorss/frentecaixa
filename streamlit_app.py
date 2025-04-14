import streamlit as st
import locale
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from io import BytesIO
import platform

# --- Configuração de Localização (Moeda Brasileira) ---
try:
    # Tenta definir o locale pt_BR para formatação de moeda
    # No Windows, pode ser 'Portuguese_Brazil.1252' ou 'pt-BR'
    # No Linux/macOS geralmente é 'pt_BR.UTF-8'
    if platform.system() == "Windows":
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    else:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    st.warning("Locale 'pt_BR.UTF-8' ou 'Portuguese_Brazil.1252' não encontrado. A formatação de moeda pode não funcionar corretamente.")
    # Define um fallback simples se o locale falhar
    def format_currency(value):
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
else:
    def format_currency(value):
        try:
            # Usa a formatação do locale se ele foi configurado com sucesso
            return locale.currency(value, grouping=True, symbol='R$')
        except (TypeError, ValueError):
             # Fallback caso o valor não seja numérico
            return "R$ 0,00"


# --- Função para Gerar o PDF ---
def gerar_pdf(data_fechamento, responsavel, saldo_inicial, vendas_dinheiro, suprimentos, saidas, saldo_esperado, saldo_contado, diferenca, observacoes=""):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4 # Pega as dimensões da página A4

    # --- Configurações Iniciais ---
    margem_esquerda = 2 * cm
    margem_superior = height - 2 * cm
    espaco_linha = 0.7 * cm

    # --- Desenha o Cabeçalho ---
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margem_esquerda, margem_superior, "Relatório de Fechamento de Caixa (Dinheiro)")
    c.setFont("Helvetica", 11)
    c.drawString(margem_esquerda, margem_superior - espaco_linha, f"Data: {data_fechamento.strftime('%d/%m/%Y')}")
    c.drawString(margem_esquerda, margem_superior - 2 * espaco_linha, f"Responsável: {responsavel}")

    # Define posição inicial para os detalhes
    y_pos = margem_superior - 4 * espaco_linha

    # --- Desenha os Detalhes ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margem_esquerda, y_pos, "Detalhes do Caixa:")
    y_pos -= espaco_linha * 1.5 # Aumenta o espaço após o título da seção

    c.setFont("Helvetica", 11)
    items = [
        ("Saldo Inicial (Fundo de Troco):", saldo_inicial),
        ("(+) Vendas em Dinheiro:", vendas_dinheiro),
        ("(+) Suprimentos / Reforços:", suprimentos),
        ("(-) Saídas / Sangrias / Pagamentos:", saidas),
        ("(=) Saldo Final Esperado em Dinheiro:", saldo_esperado),
        ("Valor Contado em Dinheiro:", saldo_contado),
        ("Diferença (Sobra/Falta):", diferenca),
    ]

    # Largura para os labels para alinhar os valores
    largura_label = 7 * cm

    for label, value in items:
        c.drawString(margem_esquerda, y_pos, label)
        # Formata o valor como moeda e alinha à direita
        valor_formatado = format_currency(value if isinstance(value, (int, float)) else 0.0)
        # Alinha o valor à direita em relação à largura do label
        c.drawRightString(margem_esquerda + largura_label, y_pos, valor_formatado)
        y_pos -= espaco_linha

    # Adiciona a indicação de Sobra/Falta visualmente
    y_pos -= espaco_linha * 0.5 # Pequeno espaço extra
    if diferenca > 0:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margem_esquerda + largura_label + 0.5*cm, y_pos + espaco_linha, "(SOBRA)") # Ajusta a posição Y para alinhar com a linha da diferença
    elif diferenca < 0:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margem_esquerda + largura_label + 0.5*cm, y_pos + espaco_linha, "(FALTA)") # Ajusta a posição Y para alinhar com a linha da diferença
    else:
        c.setFont("Helvetica", 11)
        c.drawString(margem_esquerda + largura_label + 0.5*cm, y_pos + espaco_linha, "(CORRETO)") # Ajusta a posição Y para alinhar com a linha da diferença

    c.setFont("Helvetica", 11) # Volta para a fonte normal

    # --- Observações ---
    y_pos -= espaco_linha * 1.5 # Espaço antes das observações
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margem_esquerda, y_pos, "Observações:")
    y_pos -= espaco_linha

    c.setFont("Helvetica", 11)
    if observacoes:
        # Simples quebra de linha (pode ser melhorado para textos longos)
        linhas_obs = observacoes.split('\n')
        for linha in linhas_obs:
             # Verifica se ainda cabe na página antes de desenhar
            if y_pos < 3 * cm: # Define uma margem inferior
                c.showPage() # Cria nova página
                c.setFont("Helvetica", 11)
                y_pos = height - 2 * cm # Reinicia no topo da nova página
            c.drawString(margem_esquerda, y_pos, linha)
            y_pos -= espaco_linha * 0.6 # Espaço menor entre linhas de observação
    else:
        c.drawString(margem_esquerda, y_pos, "Nenhuma observação.")

    # --- Rodapé / Assinatura (Opcional) ---
    y_pos = 4 * cm # Posição fixa perto da base
    c.line(margem_esquerda, y_pos, width - margem_esquerda, y_pos) # Linha para assinatura
    y_pos -= espaco_linha
    c.drawCentredString(width / 2, y_pos, "Assinatura do Responsável / Conferente")


    # --- Salva o PDF ---
    c.save()
    buffer.seek(0)
    return buffer

# --- Interface Streamlit ---
st.set_page_config(page_title="Fechamento de Caixa (Dinheiro)", layout="wide")

st.title("Controle de Fechamento de Caixa - Dinheiro")
st.markdown("Preencha os valores abaixo para calcular o fechamento do caixa referente apenas às movimentações em **dinheiro**.")

# --- Inputs do Usuário ---
col1, col2 = st.columns(2)
with col1:
    data_fechamento = st.date_input("Data do Fechamento", date.today())
with col2:
    responsavel = st.text_input("Nome do Responsável/Operador", placeholder="Digite o nome")

st.divider()

st.subheader("Valores em Dinheiro (R$)")
col_val1, col_val2, col_val3 = st.columns(3)

with col_val1:
    saldo_inicial = st.number_input("1. Saldo Inicial (Fundo de Troco)", min_value=0.0, step=0.01, format="%.2f", key="saldo_inicial", value=0.0)
    vendas_dinheiro = st.number_input("2. Total de Vendas em Dinheiro", min_value=0.0, step=0.01, format="%.2f", key="vendas_dinheiro", value=0.0)

with col_val2:
    suprimentos = st.number_input("3. Suprimentos / Reforços (Dinheiro Adicionado)", min_value=0.0, step=0.01, format="%.2f", key="suprimentos", value=0.0)
    saidas = st.number_input("4. Saídas / Sangrias / Pagamentos (Dinheiro Retirado)", min_value=0.0, step=0.01, format="%.2f", key="saidas", value=0.0)

with col_val3:
    st.markdown("<br/>"*3, unsafe_allow_html=True) # Adiciona espaço para alinhar visualmente
    saldo_contado = st.number_input("6. Valor Contado no Caixa (Dinheiro)", min_value=0.0, step=0.01, format="%.2f", key="saldo_contado", value=0.0)

st.divider()

# --- Cálculos ---
saldo_esperado = (saldo_inicial or 0.0) + (vendas_dinheiro or 0.0) + (suprimentos or 0.0) - (saidas or 0.0)
diferenca = (saldo_contado or 0.0) - saldo_esperado

# --- Exibição dos Resultados ---
st.subheader("Resultado do Fechamento")
col_res1, col_res2 = st.columns(2)

with col_res1:
    st.metric(label="5. Saldo Final Esperado (Dinheiro)", value=format_currency(saldo_esperado))

with col_res2:
    st.metric(label="7. Diferença (Contado - Esperado)", value=format_currency(diferenca), delta=f"{format_currency(diferenca)} {'(Sobra)' if diferenca > 0 else '(Falta)' if diferenca < 0 else '(Correto)'}")

st.divider()

# --- Campo de Observações e Botão de Download ---
observacoes = st.text_area("Observações (Opcional)", placeholder="Registre aqui qualquer evento relevante, justificativa para diferenças, etc.")

st.divider()

if st.button("Gerar Relatório PDF"):
    if not responsavel:
        st.error("Por favor, informe o nome do responsável.")
    else:
        # Gera o nome do arquivo
        nome_arquivo = f"Fechamento_Caixa_{responsavel.replace(' ','_')}_{data_fechamento.strftime('%Y%m%d')}.pdf"

        # Gera o PDF em memória
        pdf_bytes = gerar_pdf(
            data_fechamento,
            responsavel,
            saldo_inicial or 0.0,
            vendas_dinheiro or 0.0,
            suprimentos or 0.0,
            saidas or 0.0,
            saldo_esperado,
            saldo_contado or 0.0,
            diferenca,
            observacoes
        )

        # Cria o botão de download
        st.download_button(
            label="Baixar PDF do Fechamento",
            data=pdf_bytes,
            file_name=nome_arquivo,
            mime="application/pdf"
        )
        st.success(f"Relatório PDF '{nome_arquivo}' gerado com sucesso!")
