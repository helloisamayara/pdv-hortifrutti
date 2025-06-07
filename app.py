import os
import ast
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecretkey')

# Caminhos dos arquivos
DATA_DIR = 'data'
PRODUTOS_FILE = os.path.join(DATA_DIR, 'produtos.xlsx')
VENDAS_FILE   = os.path.join(DATA_DIR, 'vendas.xlsx')
CAIXA_FILE    = os.path.join(DATA_DIR, 'movimentos_caixa.xlsx')

# Inicializa planilhas se não existirem
def inicializar_planilhas():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(PRODUTOS_FILE):
        pd.DataFrame(columns=[
            'id', 'codigo_barras', 'nome', 'tipo', 'preco_venda',
            'estoque', 'categoria', 'perecivel', 'validade', 'preco_custo'
        ]).to_excel(PRODUTOS_FILE, index=False)
    if not os.path.exists(VENDAS_FILE):
        pd.DataFrame(columns=[
            'data', 'hora', 'produtos', 'pagamento', 'total'
        ]).to_excel(VENDAS_FILE, index=False)
    if not os.path.exists(CAIXA_FILE):
        pd.DataFrame(columns=[
            'data', 'hora', 'tipo', 'valor', 'descricao'
        ]).to_excel(CAIXA_FILE, index=False)

inicializar_planilhas()
@app.before_request
def ensure_carrinho():
    session.setdefault('carrinho', [])

@app.context_processor
def inject_now():
    return {
        'now': datetime.now,
        'current_year': datetime.now().year
    }

# Página inicial
@app.route('/')
def index():
    if request.args.get('limpar') == '1':
        session['carrinho'] = []
        session.modified = True

    df_v = pd.read_excel(VENDAS_FILE, dtype={'data': str})
    hoje_str = datetime.now().strftime('%Y-%m-%d')
    vendas_hoje = df_v[df_v['data'] == hoje_str]
    total_vendas_hoje = round(vendas_hoje['total'].sum(), 2)

    total_itens_hoje = 0
    for prod_list in vendas_hoje['produtos'].dropna():
        for it in ast.literal_eval(prod_list):
            if ' x' in it:
                _, q = it.rsplit(' x', 1)
                try:
                    total_itens_hoje += float(q)
                except:
                    total_itens_hoje += 1
            else:
                total_itens_hoje += 1

    return render_template(
        'index.html',
        total_vendas_hoje=total_vendas_hoje,
        total_itens_hoje=int(total_itens_hoje)
    )

# Página de venda
@app.route('/vender')
def vender():
    if request.args.get('limpar') == '1':
        session['carrinho'] = []
        session.modified = True

    total = sum(item['subtotal'] for item in session['carrinho'])
    return render_template(
        'vender.html',
        carrinho=session['carrinho'],
        total=round(total, 2)
    )

# Listar produtos
@app.route('/produtos')
def listar_produtos():
    df = pd.read_excel(PRODUTOS_FILE, dtype={'codigo_barras': str})
    q = request.args.get('search', '').strip().lower()
    if q:
        df = df[df['nome'].str.lower().str.contains(q) | df['codigo_barras'].str.contains(q)]
    return render_template('produtos.html', produtos=df.to_dict('records'))

@app.route('/cadastrar_produto')
def cadastrar_produto():
    return redirect(url_for('editar_produto', id=0))

@app.route('/editar_produto/<int:id>', methods=['GET', 'POST'])
def editar_produto(id):
    df = pd.read_excel(PRODUTOS_FILE, dtype={'codigo_barras': str})
    campos = [
        'codigo_barras', 'nome', 'tipo', 'preco_venda',
        'estoque', 'categoria', 'perecivel', 'validade', 'preco_custo'
    ]
    if request.method == 'POST':
        v_custo = request.form.get('preco_custo', '').strip()
        preco_custo = float(v_custo) if v_custo else None

        if id == 0:
            novo = {
                k: request.form.get(k) for k in campos if k != 'preco_custo'
            }
            novo['preco_venda'] = float(request.form['preco_venda'])
            novo['preco_custo'] = preco_custo
            novo['estoque'] = float(request.form['estoque'])
            novo['perecivel'] = 'sim' if request.form.get('perecivel') else 'nao'
            novo['validade'] = request.form.get('validade', '')
            novo['id'] = int(df['id'].max() + 1) if not df.empty else 1
            df = pd.concat([df, pd.DataFrame([novo])], ignore_index=True)
        else:
            df.loc[df['id'] == id, 'codigo_barras'] = request.form['codigo_barras']
            df.loc[df['id'] == id, 'nome'] = request.form['nome']
            df.loc[df['id'] == id, 'tipo'] = request.form['tipo']
            df.loc[df['id'] == id, 'preco_venda'] = float(request.form['preco_venda'])
            df.loc[df['id'] == id, 'preco_custo'] = preco_custo
            df.loc[df['id'] == id, 'estoque'] = float(request.form['estoque'])
            df.loc[df['id'] == id, 'categoria'] = request.form.get('categoria', '')
            df.loc[df['id'] == id, 'perecivel'] = 'sim' if request.form.get('perecivel') else 'nao'
            df.loc[df['id'] == id, 'validade'] = request.form.get('validade', '')

        df.to_excel(PRODUTOS_FILE, index=False)
        return redirect(url_for('listar_produtos'))

    produto = None
    if id != 0:
        recs = df[df['id'] == id].to_dict('records')
        if recs:
            produto = recs[0]
    return render_template('editar_produto.html', produto=produto)

@app.route('/excluir_produto/<int:id>', methods=['DELETE'])
def excluir_produto(id):
    df = pd.read_excel(PRODUTOS_FILE, dtype={'codigo_barras': str})
    df = df[df['id'] != id]
    df.to_excel(PRODUTOS_FILE, index=False)
    return jsonify(status='success')

@app.route('/relatorio')
def relatorio():
    selected_date = request.args.get('data') or datetime.now().strftime('%Y-%m-%d')
    df_v = pd.read_excel(VENDAS_FILE, dtype={'data': str})
    df_v = df_v[df_v['data'] == selected_date]

    vendas = []
    resumo = {}
    for _, row in df_v.iterrows():
        try:
            itens = ast.literal_eval(row.get('produtos', '')) if pd.notna(row.get('produtos')) else []
        except:
            itens = []

        vendas.append({
            'data': row.get('data', ''),
            'hora': row.get('hora', ''),
            'produtos': itens,
            'pagamento': row.get('pagamento', ''),
            'total': row.get('total', 0)
        })

        for it in itens:
            if ' x' in it:
                nome, qtd = it.rsplit(' x', 1)
                try: qtd = float(qtd)
                except: qtd = 1.0
            else:
                nome, qtd = it, 1.0
            resumo[nome] = resumo.get(nome, 0) + qtd

    produtos_vendidos = [{'nome': nome, 'quantidade': resumo[nome]} for nome in sorted(resumo.keys())]

    return render_template(
        'relatorio.html',
        vendas=vendas,
        produtos_vendidos=produtos_vendidos,
        selected_date=selected_date
    )

@app.route('/caixa', methods=['GET', 'POST'])
def caixa():
    hoje = datetime.now().strftime('%Y-%m-%d')
    hora = datetime.now().strftime('%H:%M:%S')

    if request.method == 'POST':
        tipo = request.form.get('tipo')
        valor = float(request.form.get('valor', 0))
        descricao = request.form.get('descricao', '').strip()

        if tipo in ['entrada', 'saida', 'saldo_inicial'] and valor > 0:
            df_mov = pd.read_excel(CAIXA_FILE)
            df_mov.loc[len(df_mov)] = {
                'data': hoje,
                'hora': hora,
                'tipo': tipo,
                'valor': valor,
                'descricao': descricao
            }
            df_mov.to_excel(CAIXA_FILE, index=False)

    df_vendas = pd.read_excel(VENDAS_FILE)
    vendas_hoje = df_vendas[df_vendas['data'] == hoje]

    df_mov = pd.read_excel(CAIXA_FILE)
    df_mov_dia = df_mov[df_mov['data'] == hoje]

    saldo_inicial = df_mov_dia[df_mov_dia['tipo'] == 'saldo_inicial']['valor'].sum()
    entradas = df_mov_dia[df_mov_dia['tipo'] == 'entrada']['valor'].sum()
    saidas = df_mov_dia[df_mov_dia['tipo'] == 'saida']['valor'].sum()
    total_vendas = vendas_hoje['total'].sum()
    saldo_total = saldo_inicial + entradas + total_vendas - saidas

    return render_template('caixa.html',
        vendas=vendas_hoje.to_dict('records'),
        movimentos=df_mov_dia.to_dict('records'),
        saldo_inicial=saldo_inicial,
        entradas=entradas,
        saidas=saidas,
        total_vendas=total_vendas,
        saldo_total=saldo_total
    )
# API: listar produtos para modal AJAX
@app.route('/api/produtos')
def api_listar_produtos():
    df = pd.read_excel(PRODUTOS_FILE, dtype={'codigo_barras': str})
    produtos = df[['codigo_barras', 'nome', 'tipo', 'preco_venda']].rename(columns={'preco_venda': 'preco'}).to_dict('records')
    return jsonify(produtos)

# API: adicionar produto ao carrinho
@app.route('/api/adicionar_produto', methods=['POST'])
def api_adicionar_produto():
    data = request.get_json() or {}
    codigo = data.get('codigo_barras', '').strip()
    try:
        quantidade = float(data.get('quantidade', 0))
    except ValueError:
        return jsonify(error="Quantidade inválida."), 400

    df = pd.read_excel(PRODUTOS_FILE, dtype={'codigo_barras': str})
    prod = df[df['codigo_barras'] == codigo]
    if prod.empty:
        return jsonify(error="Produto não encontrado."), 404

    d = prod.iloc[0].to_dict()
    tipo = d['tipo']
    estoque = float(d['estoque'])

    if tipo == 'unidade' and not quantidade.is_integer():
        return jsonify(error="Unidades devem ser inteiras."), 400
    if quantidade > estoque:
        return jsonify(error=f"Estoque insuficiente ({estoque:.3f})."), 400

    subtotal = round(d['preco_venda'] * quantidade, 2)
    session['carrinho'].append({
        'codigo': d['codigo_barras'],
        'nome': d['nome'],
        'preco': d['preco_venda'],
        'tipo': d['tipo'],
        'quantidade': quantidade,
        'subtotal': subtotal
    })
    session.modified = True
    total = sum(i['subtotal'] for i in session['carrinho'])
    return jsonify(carrinho=session['carrinho'], total=round(total, 2))

# API: remover item do carrinho
@app.route('/api/remove_item', methods=['POST'])
def api_remove_item():
    idx = int(request.json.get('index', -1))
    if 0 <= idx < len(session['carrinho']):
        session['carrinho'].pop(idx)
        session.modified = True
    total = sum(i['subtotal'] for i in session['carrinho'])
    return jsonify(carrinho=session['carrinho'], total=round(total, 2))

# Cancelar venda
@app.route('/cancelar_venda', methods=['POST'])
def cancelar_venda():
    session.pop('carrinho', None)
    return redirect(url_for('vender'))

# Finalizar venda
@app.route('/finalizar_venda', methods=['POST'])
def finalizar_venda():
    dados = request.get_json() or {}
    pagamento = dados.get('pagamento', 'dinheiro')
    desconto = float(dados.get('desconto', 0))
    carrinho = session.pop('carrinho', [])

    df_p = pd.read_excel(PRODUTOS_FILE, dtype={'codigo_barras': str})
    data_hoje = datetime.now().date()
    for item in carrinho:
        produto = df_p[df_p['codigo_barras'] == item['codigo']]
        if not produto.empty and produto.iloc[0]['perecivel'] == 'sim':
            validade_str = produto.iloc[0]['validade']
            if validade_str:
                try:
                    validade = datetime.strptime(validade_str, '%Y-%m-%d').date()
                    if validade < data_hoje:
                        return jsonify(error=f"O produto '{item['nome']}' está vencido (validade: {validade_str}). Venda bloqueada."), 400
                except:
                    pass

    total = round(sum(i['subtotal'] for i in carrinho) * (1 - desconto / 100), 2)

    df_v = pd.read_excel(VENDAS_FILE)
    df_v.loc[len(df_v)] = {
        'data': datetime.now().strftime('%Y-%m-%d'),
        'hora': datetime.now().strftime('%H:%M:%S'),
        'produtos': str([f"{i['nome']} x{i['quantidade']}" for i in carrinho]),
        'pagamento': pagamento,
        'total': total
    }
    df_v.to_excel(VENDAS_FILE, index=False)

    for item in carrinho:
        idxs = df_p[df_p['codigo_barras'] == item['codigo']].index
        if not idxs.empty:
            df_p.loc[idxs, 'estoque'] -= item['quantidade']
    df_p.to_excel(PRODUTOS_FILE, index=False)

    return jsonify(status='success')

# Roda o app
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)
