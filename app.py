import os
import ast
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecretkey')

# Caminhos dos arquivos
PRODUTOS_FILE = os.path.join('data', 'produtos.xlsx')
VENDAS_FILE   = os.path.join('data', 'vendas.xlsx')

def inicializar_planilhas():
    os.makedirs('data', exist_ok=True)
    if not os.path.exists(PRODUTOS_FILE):
        pd.DataFrame(columns=[
            'id', 'codigo_barras', 'nome', 'tipo', 'preco_venda',
            'estoque', 'categoria', 'perecivel', 'validade'
        ]).to_excel(PRODUTOS_FILE, index=False)
    if not os.path.exists(VENDAS_FILE):
        pd.DataFrame(columns=[
            'data', 'hora', 'produtos', 'pagamento', 'total'
        ]).to_excel(VENDAS_FILE, index=False)

inicializar_planilhas()

@app.before_request
def ensure_carrinho():
    session.setdefault('carrinho', [])

@app.context_processor
def inject_now():
    return {'now': datetime.now}

@app.route('/')
def index():
    # se vier ?limpar=1, esvazia o carrinho
    if request.args.get('limpar') == '1':
        session['carrinho'] = []
        session.modified = True
    return render_template('index.html')

@app.route('/vender')
def vender():
    if request.args.get('limpar') == '1':
        session['carrinho'] = []
        session.modified = True

    total = sum(item['subtotal'] for item in session['carrinho'])
    return render_template('vender.html',
                           carrinho=session['carrinho'],
                           total=round(total, 2))

@app.route('/validar_produto', methods=['POST'])
def validar_produto():
    data = request.get_json() or {}
    codigo = data.get('codigo_barras','').strip()
    try:
        quantidade = float(data.get('quantidade',0))
    except ValueError:
        return jsonify(found=False, message="Quantidade inválida."), 400

    df = pd.read_excel(PRODUTOS_FILE, dtype={'codigo_barras':str})
    prod = df[df['codigo_barras']==codigo]
    if prod.empty:
        return jsonify(found=False, message="Produto não encontrado."), 404

    estoque = float(prod.iloc[0]['estoque'])
    tipo    = prod.iloc[0]['tipo']
    if tipo=='unidade' and not quantidade.is_integer():
        return jsonify(found=False,
                       message="Quantidade deve ser inteira para unidades."), 400

    if quantidade>estoque:
        unidade = 'kg' if tipo=='peso' else 'un'
        return jsonify(
            found=False,
            message=f"Estoque insuficiente (só há {estoque:.3f}{unidade})."
        ), 400

    return jsonify(found=True)

@app.route('/adicionar_produto', methods=['POST'])
def adicionar_produto():
    codigo     = request.form.get('codigo_barras','')
    quantidade = float(request.form.get('quantidade',1))
    df = pd.read_excel(PRODUTOS_FILE, dtype={'codigo_barras':str})
    prod = df[df['codigo_barras']==codigo]
    if not prod.empty:
        d = prod.iloc[0].to_dict()
        subtotal = round(d['preco_venda'] * quantidade, 2)
        session['carrinho'].append({
            'codigo':     d['codigo_barras'],
            'nome':       d['nome'],
            'preco':      d['preco_venda'],
            'quantidade': quantidade,
            'subtotal':   subtotal
        })
        session.modified = True
    return redirect(url_for('vender'))

@app.route('/cancelar_venda', methods=['POST'])
def cancelar_venda():
    session.pop('carrinho', None)
    return redirect(url_for('vender'))

@app.route('/remove_item', methods=['POST'])
def remove_item():
    idx = int(request.json.get('index',-1))
    if 0 <= idx < len(session['carrinho']):
        session['carrinho'].pop(idx)
        session.modified = True
    return jsonify(status='success')

@app.route('/finalizar_venda', methods=['POST'])
def finalizar_venda():
    dados     = request.get_json() or {}
    pagamento = dados.get('pagamento','dinheiro')
    desconto  = float(dados.get('desconto',0))
    carrinho  = session.pop('carrinho', [])
    total     = round(sum(i['subtotal'] for i in carrinho)*(1-desconto/100),2)

    df_v = pd.read_excel(VENDAS_FILE)
    df_v.loc[len(df_v)] = {
        'data':      datetime.now().strftime('%Y-%m-%d'),
        'hora':      datetime.now().strftime('%H:%M:%S'),
        'produtos':  str([f"{i['nome']} x{i['quantidade']}" for i in carrinho]),
        'pagamento': pagamento,
        'total':     total
    }
    df_v.to_excel(VENDAS_FILE, index=False)

    df_p = pd.read_excel(PRODUTOS_FILE, dtype={'codigo_barras':str})
    for item in carrinho:
        idxs = df_p[df_p['codigo_barras']==item['codigo']].index
        if not idxs.empty:
            df_p.loc[idxs,'estoque'] -= item['quantidade']
    df_p.to_excel(PRODUTOS_FILE, index=False)

    return jsonify(status='success')

@app.route('/produtos')
def listar_produtos():
    df = pd.read_excel(PRODUTOS_FILE, dtype={'codigo_barras':str})
    return render_template('produtos.html', produtos=df.to_dict('records'))

@app.route('/cadastrar_produto')
def cadastrar_produto():
    return redirect(url_for('editar_produto', id=0))

@app.route('/editar_produto/<int:id>', methods=['GET','POST'])
def editar_produto(id):
    df = pd.read_excel(PRODUTOS_FILE, dtype={'codigo_barras':str})
    campos = ['codigo_barras','nome','tipo','preco_venda','estoque','categoria','perecivel','validade']
    if request.method=='POST':
        if id==0:
            novo = {k: request.form.get(k) for k in campos}
            novo['id'] = int(df['id'].max()+1) if not df.empty else 1
            df = pd.concat([df,pd.DataFrame([novo])], ignore_index=True)
        else:
            for k in campos:
                v = request.form.get(k)
                if k in ('preco_venda','estoque'):
                    v = float(v)
                df.loc[df['id']==id,k] = v
        df.to_excel(PRODUTOS_FILE, index=False)
        return redirect(url_for('listar_produtos'))
    produto = None if id==0 else df[df['id']==id].to_dict('records')[0]
    return render_template('editar_produto.html', produto=produto)

@app.route('/excluir_produto/<int:id>', methods=['DELETE'])
def excluir_produto(id):
    df = pd.read_excel(PRODUTOS_FILE, dtype={'codigo_barras':str})
    df = df[df['id'] != id]
    df.to_excel(PRODUTOS_FILE, index=False)
    return jsonify(status='success')

@app.route('/caixa')
def caixa():
    df = pd.read_excel(VENDAS_FILE)
    hoje = datetime.now().strftime('%Y-%m-%d')
    vendas_hoje = df[df['data']==hoje].to_dict('records')
    total = round(df[df['data']==hoje]['total'].sum(), 2)
    return render_template('caixa.html', vendas=vendas_hoje, total=total)

@app.route('/produtos_vendidos')
def produtos_vendidos():
    df_v = pd.read_excel(VENDAS_FILE, dtype={'data':str})
    registros = []
    for _, row in df_v.iterrows():
        data_venda = row.get('data','')
        linha       = row.get('produtos')
        # ignora registros sem lista de produtos
        if pd.isna(linha):
            continue
        try:
            itens = ast.literal_eval(linha)
        except:
            continue
        for it in itens:
            if ' x' in it:
                nome, qtd = it.rsplit(' x',1)
                try: qtd = float(qtd)
                except: qtd = 1.0
            else:
                nome, qtd = it, 1.0
            registros.append({'data': data_venda, 'nome': nome, 'quantidade': qtd})
    registros.sort(key=lambda x: x['data'], reverse=True)
    return render_template('produtos_vendidos.html', registros=registros)

@app.route('/relatorio')
def relatorio():
    df_v = pd.read_excel(VENDAS_FILE, dtype={'data':str})
    vendas = []
    resumo = {}
    for _, row in df_v.iterrows():
        data_venda = row.get('data','')
        linha       = row.get('produtos')
        if pd.isna(linha):
            continue
        try:
            itens = ast.literal_eval(linha)
        except:
            continue
        vendas.append({
            'data': data_venda,
            'hora': row.get('hora',''),
            'produtos': itens,
            'pagamento': row.get('pagamento',''),
            'total': row.get('total',0)
        })
        for it in itens:
            if ' x' in it:
                nome, qtd = it.rsplit(' x',1)
                try: qtd = float(qtd)
                except: qtd = 1.0
            else:
                nome, qtd = it, 1.0
            resumo[nome] = resumo.get(nome, 0) + qtd

    # prepara lista de resumo ordenada
    produtos_vendidos = [
        {'nome': n, 'quantidade': resumo[n]}
        for n in sorted(resumo.keys())
    ]
    return render_template('relatorio.html',
                           vendas=vendas,
                           produtos_vendidos=produtos_vendidos)

if __name__ == '__main__':
    # Executa na porta 5001
    app.run(host='127.0.0.1', port=5001, debug=True)
