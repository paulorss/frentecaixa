import streamlit as st
import locale
from datetime import date, datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from io import BytesIO
import platform
import uuid
import csv # Para ler/escrever CSV
import json # Para serializar/desserializar o estado
import os # Para verificar se o arquivo existe

# --- Constantes ---
CSV_FILE = "diario.csv"
CSV_HEADER = ["Timestamp", "SessionStateJSON"]

# --- PRIMEIRA COISA: Configuração da Página ---
st.set_page_config(page_title="Fechamento de Caixa Persistente", layout="wide")

# --- Configuração de Localização (Moeda Brasileira) ---
# (Será definida após a inicialização do estado)
def format_currency(value): # Define uma função padrão inicial
    try: return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError): return "R$ 0,00"

# --- Funções para Salvar e Carregar Estado do CSV ---

def save_state_to_csv():
    """Salva o estado relevante da sessão atual em diario.csv"""
    now = datetime.now().isoformat()
    # Coleta o estado relevante de st.session_state
    state_to_save = {
        'data_fechamento': st.session_state.get('data_fechamento', date.today()).isoformat(),
        'responsavel': st.session_state.get('responsavel', ''),
        'saldo_inicial': st.session_state.get('saldo_inicial', 0.0),
        'lista_entradas': st.session_state.get('lista_entradas', []),
        'lista_saidas': st.session_state.get('lista_saidas', []),
        'saldo_contado': st.session_state.get('saldo_contado', 0.0),
        'observacoes': st.session_state.get('observacoes', '')
    }
    # Converte listas para JSON (UUID vira string)
    state_to_save['lista_entradas'] = [{'id': str(item['id']), 'descricao': item['descricao'], 'valor': item['valor']} for item in state_to_save['lista_entradas']]
    state_to_save['lista_saidas'] = [{'id': str(item['id']), 'descricao': item['descricao'], 'valor': item['valor']} for item in state_to_save['lista_saidas']]

    json_state = json.dumps(state_to_save, ensure_ascii=False)

    file_exists = os.path.isfile(CSV_FILE)
    try:
        with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists or os.path.getsize(CSV_FILE) == 0:
                writer.writerow(CSV_HEADER)
            writer.writerow([now, json_state])
        print(f"Estado salvo em {CSV_FILE} às {now}")
    except IOError as e:
        st.error(f"Erro Crítico ao salvar estado no CSV: {e}")
    except Exception as e:
        st.error(f"Erro inesperado ao salvar estado: {e}")


def load_state_from_csv():
    """Carrega o último estado válido do diario.csv"""
    default_state_structure = {
        'data_fechamento': date.today(),
        'responsavel': '',
        'saldo_inicial': 0.0,
        'lista_entradas': [],
        'lista_saidas': [],
        'saldo_contado': 0.0,
        'observacoes': ''
    }
    if not os.path.isfile(CSV_FILE) or os.path.getsize(CSV_FILE) == 0:
        print("Arquivo diario.csv não encontrado ou vazio. Usando estado padrão.")
        return default_state_structure

    try:
        last_valid_state_dict = default_state_structure # Começa com a estrutura padrão
        with open(CSV_FILE, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header != CSV_HEADER:
                 print(f"Cabeçalho inválido ou ausente em {CSV_FILE}. Tentando ler.")
                 f.seek(0) # Volta para o início

            last_row_content = None
            for row in reader:
                if len(row) >= 2:
                    last_row_content = row[1] # Pega o JSON

        if last_row_content:
            loaded_data_raw = json.loads(last_row_content)

            # Converte data string de volta para objeto date
            if 'data_fechamento' in loaded_data_raw:
                 try:
                    loaded_data_raw['data_fechamento'] = date.fromisoformat(loaded_data_raw['data_fechamento'])
                 except (ValueError, TypeError):
                     loaded_data_raw['data_fechamento'] = date.today()

            # Garante que listas sejam listas
            loaded_data_raw['lista_entradas'] = loaded_data_raw.get('lista_entradas', []) if isinstance(loaded_data_raw.get('lista_entradas'), list) else []
            loaded_data_raw['lista_saidas'] = loaded_data_raw.get('lista_saidas', []) if isinstance(loaded_data_raw.get('lista_saidas'), list) else []

            # Atualiza o dicionário de estado válido com os dados carregados
            last_valid_state_dict.update(loaded_data_raw)
            print("Estado carregado com sucesso do CSV.")

        else:
             print("Nenhuma linha válida encontrada no CSV após o cabeçalho.")
             # Retorna a estrutura padrão se não achou nada válido

        return last_valid_state_dict

    except (IOError, csv.Error, json.JSONDecodeError, IndexError) as e:
        st.error(f"Erro ao carregar/ler estado do CSV: {e}. Usando estado padrão.")
        return default_state_structure
    except Exception as e:
        st.error(f"Erro inesperado ao carregar estado: {e}. Usando estado padrão.")
        return default_state_structure

# --- Carregar estado e inicializar session_state ---
# **ESTA É A SEÇÃO MODIFICADA PARA CORRIGIR O ERRO**
if 'state_loaded_from_csv' not in st.session_state:
    print("Tentando carregar estado do CSV...")
    loaded_state = load_state_from_csv() # Retorna dict com dados do CSV ou defaults

    # INICIALIZA/ATUALIZA st.session_state com os valores carregados (ou defaults)
    # Garantindo que todas as chaves necessárias existam
    st.session_state.update({
        'data_fechamento': loaded_state.get('data_fechamento', date.today()),
        'responsavel': loaded_state.get('responsavel', ''),
        'saldo_inicial': loaded_state.get('saldo_inicial', 0.0),
        'lista_entradas': loaded_state.get('lista_entradas', []),
        'lista_saidas': loaded_state.get('lista_saidas', []),
        'saldo_contado': loaded_state.get('saldo_contado', 0.0), # Garante que exista
        'observacoes': loaded_state.get('observacoes', ''),
        'state_loaded_from_csv': True # Marca que o estado foi carregado/inicializado
    })
    print("Estado carregado/inicializado a partir do CSV (ou padrão).")
else:
    # Em reruns normais, apenas garante que as chaves essenciais ainda existem
    # (Defesa extra)
    keys_to_ensure = ['data_fechamento', 'responsavel', 'saldo_inicial', 'lista_entradas', 'lista_saidas', 'saldo_contado', 'observacoes']
    defaults_ensure = [date.today(), '', 0.0, [], [], 0.0, '']
    for key, default_val in zip(keys_to_ensure, defaults_ensure):
        if key not in st.session_state:
            st.session_state[key] = default_val
            print(f"Chave '{key}' reinicializada em rerun.") # Log para depuração


# --- Lógica do Locale e formatação de moeda (após inicialização do estado) ---
try:
    if platform.system() == "Windows": locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    else: locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    # Redefine a função para usar o locale se funcionou
    def format_currency(value):
        try: return locale.currency(value, grouping=True, symbol='R$')
        except (TypeError, ValueError): return "R$ 0,00"
    print("Locale pt_BR definido com sucesso.")
except locale.Error:
    #st.warning("Locale 'pt_BR.UTF-8' ou 'Portuguese_Brazil.1252' não encontrado. Usando formatação de moeda alternativa.")
    # Mantém a função de fallback definida no início
    print("Falha ao definir locale pt_BR. Usando fallback.")


# --- Funções Auxiliares para manipular listas (disparam save_state_to_csv) ---
def adicionar_entrada(descricao, valor):
    if valor > 0:
        st.session_state.lista_entradas.append({
            'id': str(uuid.uuid4()),
            'descricao': descricao or "Entrada Diversa",
            'valor': valor
        })
        save_state_to_csv()
    else:
        st.warning("Valor da entrada deve ser maior que zero.")

def adicionar_saida(descricao, valor):
    if not descricao:
        st.warning("Descrição da saída é obrigatória.")
        return False
    if valor > 0:
        st.session_state.lista_saidas.append({
            'id': str(uuid.uuid4()),
            'descricao': descricao,
            'valor': valor
        })
        save_state_to_csv()
        return True
    else:
        st.warning("Valor da saída deve ser maior que zero.")
        return False

def remover_item(lista_key, item_id):
    original_length = len(st.session_state[lista_key])
    st.session_state[lista_key] = [item for item in st.session_state[lista_key] if str(item['id']) != str(item_id)]
    if len(st.session_state[lista_key]) < original_length:
        save_state_to_csv()

# --- Função PDF (igual antes, recebe totais calculados) ---
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
        ("(+) Total Entradas Registradas (Dinheiro):", total_entradas_registradas),
        ("(-) Total Saídas Registradas (Dinheiro):", total_saidas_registradas),
        ("(=) Saldo Final Esperado em Dinheiro:", saldo_esperado),
        ("Valor Contado em Dinheiro:", saldo_contado),
        ("Diferença (Sobra/Falta):", diferenca),
    ]

    largura_label = 9.5 * cm # Ajuste conforme necessário

    for label, value in items:
        c.drawString(margem_esquerda, y_pos, label)
        valor_formatado = format_currency(value if isinstance(value, (int, float)) else 0.0)
        c.drawRightString(margem_esquerda + largura_label, y_pos, valor_formatado)
        y_pos -= espaco_linha

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

    y_pos -= espaco_linha * 1.5
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margem_esquerda, y_pos, "Observações:")
    y_pos -= espaco_linha

    c.setFont("Helvetica", 11)
    if observacoes:
        linhas_obs = observacoes.split('\n')
        for linha in linhas_obs:
            if y_pos < 3 * cm:
                c.showPage(); c.setFont("Helvetica", 11); y_pos = height - 2 * cm
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


# --- Interface Streamlit ---
st.title("Controle Detalhado de Caixa - Dinheiro (com Persistência)")

# --- Inputs Iniciais (usam valores do session_state) ---
col1, col2 = st.columns(2)
with col1:
    st.date_input("Data do Fechamento",
                  key='data_fechamento',
                  # value=st.session_state.data_fechamento, # Não precisa mais de value, key busca no state
                  on_change=save_state_to_csv)
with col2:
    st.text_input("Nome do Responsável/Operador",
                  key='responsavel',
                  # value=st.session_state.responsavel, # Não precisa mais de value
                  placeholder="Digite o nome",
                  on_change=save_state_to_csv)

st.number_input("1. Saldo Inicial (Fundo de Troco)",
                key='saldo_inicial',
                # value=st.session_state.saldo_inicial, # Não precisa mais de value
                min_value=0.0, step=0.01, format="%.2f",
                on_change=save_state_to_csv)

st.divider()

# --- Seção para Registrar Entradas e Saídas ---
col_input1, col_input2 = st.columns(2)

with col_input1:
    st.subheader("Registrar Nova Entrada (Dinheiro)")
    with st.form("form_entrada", clear_on_submit=True):
        desc_entrada_form = st.text_input("Descrição da Entrada (Opcional)", key="desc_ent_form", placeholder="Ex: Venda X, Suprimento Y")
        val_entrada_form = st.number_input("Valor da Entrada (R$)", key="val_ent_form", min_value=0.01, step=0.01, format="%.2f")
        submitted_entrada = st.form_submit_button("Adicionar Entrada")
        if submitted_entrada:
            adicionar_entrada(desc_entrada_form, val_entrada_form)
            # Limpar campos do form manualmente após adicionar (clear_on_submit pode ser instável)
            # st.session_state.desc_ent_form = "" # Comentado - clear_on_submit deve bastar
            # st.session_state.val_ent_form = 0.01 # Comentado
            st.rerun()

    st.subheader("Entradas Registradas")
    if not st.session_state.lista_entradas:
        st.caption("Nenhuma entrada registrada.")
    else:
        for i in range(len(st.session_state.lista_entradas) - 1, -1, -1):
            item = st.session_state.lista_entradas[i]
            col_item1, col_item2, col_item3 = st.columns([4, 2, 1])
            col_item1.write(item['descricao'])
            col_item2.write(format_currency(item['valor']))
            col_item3.button("🗑️", key=f"rem_ent_{item['id']}", on_click=remover_item, args=('lista_entradas', item['id']))


with col_input2:
    st.subheader("Registrar Nova Saída (Dinheiro)")
    with st.form("form_saida", clear_on_submit=True):
        desc_saida_form = st.text_input("Descrição da Saída (Obrigatória)", key="desc_sai_form", placeholder="Ex: Pagto Fornecedor Z, Sangria")
        val_saida_form = st.number_input("Valor da Saída (R$)", key="val_sai_form", min_value=0.01, step=0.01, format="%.2f")
        submitted_saida = st.form_submit_button("Adicionar Saída")
        if submitted_saida:
            if adicionar_saida(desc_saida_form, val_saida_form):
                st.rerun()

    st.subheader("Saídas Registradas")
    if not st.session_state.lista_saidas:
        st.caption("Nenhuma saída registrada.")
    else:
        for i in range(len(st.session_state.lista_saidas) - 1, -1, -1):
            item = st.session_state.lista_saidas[i]
            col_item1, col_item2, col_item3 = st.columns([4, 2, 1])
            col_item1.write(item['descricao'])
            col_item2.write(format_currency(item['valor']))
            col_item3.button("🗑️", key=f"rem_sai_{item['id']}", on_click=remover_item, args=('lista_saidas', item['id']))

st.divider()

# --- Cálculos Totais (usam listas do session_state) ---
total_entradas = sum(item['valor'] for item in st.session_state.lista_entradas)
total_saidas = sum(item['valor'] for item in st.session_state.lista_saidas)

# --- Seção de Conferência Final ---
st.subheader("Conferência Final do Caixa")

st.number_input("Valor Contado no Caixa (Dinheiro Físico)",
                key='saldo_contado',
                # value=st.session_state.saldo_contado, # Não precisa mais de value
                min_value=0.0, step=0.01, format="%.2f",
                on_change=save_state_to_csv)

# Pega valores do state garantindo defaults caso algo falhe (embora inicialização deva prevenir)
saldo_inicial_calc = st.session_state.get('saldo_inicial', 0.0)
saldo_contado_calc = st.session_state.get('saldo_contado', 0.0)

saldo_esperado = saldo_inicial_calc + total_entradas - total_saidas
diferenca = saldo_contado_calc - saldo_esperado

st.divider()

# --- Exibição dos Resultados ---
st.subheader("Resultado do Fechamento")
col_res1, col_res2, col_res3 = st.columns(3)

with col_res1:
     st.metric(label="Total Entradas Registradas", value=format_currency(total_entradas))
     st.metric(label="Saldo Final Esperado", value=format_currency(saldo_esperado))

with col_res2:
    st.metric(label="Total Saídas Registradas", value=format_currency(total_saidas))
    delta_text = f"{format_currency(diferenca)} {'(SOBRA)' if diferenca > 0 else '(FALTA)' if diferenca < 0 else '(CORRETO)'}"
    st.metric(label="Diferença (Contado - Esperado)", value=format_currency(diferenca), delta=delta_text)

with col_res3:
    st.markdown("##")
    if diferenca > 0: st.markdown(f"<p style='color: green; font-weight: bold; font-size: 1.1em;'>Status: {delta_text}</p>", unsafe_allow_html=True)
    elif diferenca < 0: st.markdown(f"<p style='color: red; font-weight: bold; font-size: 1.1em;'>Status: {delta_text}</p>", unsafe_allow_html=True)
    else: st.markdown(f"<p style='color: blue; font-weight: bold; font-size: 1.1em;'>Status: {delta_text}</p>", unsafe_allow_html=True)


st.divider()

# --- Campo de Observações e Botão de Download ---
st.text_area("Observações (Opcional)",
             key='observacoes',
             # value=st.session_state.observacoes, # Não precisa mais de value
             placeholder="Registre aqui qualquer evento relevante...",
             on_change=save_state_to_csv)

st.divider()

if st.button("Gerar Relatório PDF Final"):
    resp = st.session_state.get('responsavel', '')
    if not resp:
        st.error("Por favor, informe o nome do responsável.")
    else:
        data_f = st.session_state.get('data_fechamento', date.today())
        if isinstance(data_f, str):
            try: data_f = date.fromisoformat(data_f)
            except: data_f = date.today()

        nome_arquivo = f"Fechamento_Caixa_{resp.replace(' ','_')}_{data_f.strftime('%Y%m%d')}.pdf"

        pdf_bytes = gerar_pdf(
            data_f,
            resp,
            saldo_inicial_calc,
            total_entradas,
            total_saidas,
            saldo_esperado,
            saldo_contado_calc,
            diferenca,
            st.session_state.get('observacoes', '')
        )

        st.download_button(
            label="Baixar PDF do Fechamento",
            data=pdf_bytes,
            file_name=nome_arquivo,
            mime="application/pdf"
        )
        st.success(f"Relatório PDF '{nome_arquivo}' gerado com sucesso!")

# --- (Opcional) Botão para limpar estado e CSV (CUIDADO!) ---
st.divider()
if st.button("⚠️ Limpar Dados e Começar Novo Dia ⚠️", type="secondary"):
    keys_to_clear = ['data_fechamento', 'responsavel', 'saldo_inicial', 'lista_entradas', 'lista_saidas', 'saldo_contado', 'observacoes', 'state_loaded_from_csv']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    try:
        if os.path.exists(CSV_FILE):
            os.remove(CSV_FILE)
        st.success("Dados da sessão e arquivo diario.csv removidos. A página será recarregada.")
        st.rerun() # Força recarregar, agora vai carregar estado padrão vazio
    except OSError as e:
        st.error(f"Não foi possível remover o arquivo {CSV_FILE}: {e}")
