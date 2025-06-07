// static/js/pdv.js
document.addEventListener('DOMContentLoaded', () => {
  let allProducts = []
  const form = document.getElementById('addForm')
  const codigoInp = document.getElementById('codigoInput')
  const quantInp = document.getElementById('quantidadeInput')
  const errCod = document.getElementById('error-codigo')
  const errQt = document.getElementById('error-quantidade')
  const cartArea = document.getElementById('cartItems')
  const totalSpan = document.getElementById('totalVenda')
  const btnFinal = document.getElementById('btnFinalizar')
  const btnMenu = document.getElementById('btn-menu')

  const payToggle = document.getElementById('modal-finalizar-toggle')
  const descInput = document.getElementById('modal-desconto')
  const recInput = document.getElementById('modal-recebido')
  const trocoCont = document.getElementById('trocoContainer')
  const trocoInput = document.getElementById('modal-troco')
  const payRads = document.querySelectorAll('input[name="pagamento"]')
  const btnConfirm = document.getElementById('btn-confirmar-venda')

  const searchToggle = document.getElementById('modal-search-toggle')
  const searchInput = document.getElementById('searchInput')
  const resultsBox = document.getElementById('searchResults')

  const toastBox = document.createElement('div')
  toastBox.style = `
    position: fixed;
    top: 1rem;
    left: 50%;
    transform: translateX(-50%);
    background: #323232;
    color: white;
    padding: 0.5rem 1rem;
    border-radius: 0.375rem;
    z-index: 9999;
    font-weight: 500;
    display: none;
  `
  document.body.appendChild(toastBox)

  function showToast(msg) {
    toastBox.textContent = msg
    toastBox.style.display = 'block'
    setTimeout(() => { toastBox.style.display = 'none' }, 2500)
  }

  window.dispatchEvent = (event => {
    if (event.detail) showToast(event.detail)
    return true
  })

  function parseNum(str) {
    return parseFloat(str.replace(/[^\d\.]/g, '')) || 0
  }

  function renderCarrinho(itens, total) {
    cartArea.innerHTML = itens.length
      ? itens.map((item, idx) => `
        <article class="bg-gray-50 p-4 rounded-lg shadow hover:shadow-md transition-all">
          <div class="flex justify-between items-start">
            <div>
              <h4 class="font-medium text-gray-800">${item.nome}</h4>
              <p class="text-sm text-gray-500">
                ${item.quantidade}${item.tipo==='peso'?'kg':'un'} × R$ ${item.preco.toFixed(2)}
              </p>
            </div>
            <div class="text-right">
              <span class="font-semibold text-gray-800">R$ ${item.subtotal.toFixed(2)}</span>
            </div>
          </div>
          <div class="mt-2 flex justify-end space-x-2">
            <button onclick="removerItem(${idx})"
                    class="text-red-600 hover:text-red-800 p-1 rounded-full hover:bg-red-50 transition-all">
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </article>
      `).join('')
      : `<div class="flex-1 flex flex-col items-center justify-center text-gray-400">
           <i class="fas fa-shopping-basket fa-2x mb-3 opacity-50"></i>
           <p>Seu carrinho está vazio</p>
           <p class="text-sm">Adicione produtos para começar</p>
         </div>`

    totalSpan.textContent = `R$ ${total.toFixed(2)}`
    updateFinal()
  }

  function updateFinal() {
    btnFinal.disabled = !(cartArea.querySelectorAll('article').length > 0)
  }

  form.addEventListener('submit', e => {
    e.preventDefault()
    errCod.classList.add('hidden')
    errQt.classList.add('hidden')

    fetch('/api/adicionar_produto', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        codigo_barras: codigoInp.value.trim(),
        quantidade: quantInp.value.trim()
      })
    })
    .then(r => r.json().then(data => ({ ok: r.ok, data })))
    .then(({ ok, data }) => {
      if (!ok) {
        showToast(data.error || 'Erro ao adicionar.')
        return
      }
      renderCarrinho(data.carrinho, data.total)
      form.reset()
      quantInp.value = '1.000'
      codigoInp.focus()
      showToast('Produto adicionado!')
    })
    .catch(() => showToast('Falha de conexão.'))
  })

  window.removerItem = idx => {
    if (!confirm('Remover este item?')) return
    fetch('/api/remove_item', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ index: idx })
    })
    .then(r => r.json())
    .then(data => {
      renderCarrinho(data.carrinho, data.total)
      showToast('Item removido.')
    })
    .catch(() => showToast('Erro ao remover.'))
  }

  window.abrirLocalizar = () => {
    searchToggle.checked = true
    searchInput.value = ''
    resultsBox.innerHTML = Array(5).fill().map(() =>
      `<div class="h-6 bg-gray-200 rounded animate-pulse my-2"></div>`
    ).join('')

    if (!allProducts.length) {
      fetch('/api/produtos')
        .then(r => r.json())
        .then(json => {
          allProducts = json
          resultsBox.innerHTML = `<p class="text-center text-gray-500">Digite acima para buscar.</p>`
        })
        .catch(() => {
          resultsBox.innerHTML = `<p class="text-center text-red-500">Falha ao carregar produtos.</p>`
        })
    } else {
      setTimeout(() => {
        resultsBox.innerHTML = `<p class="text-center text-gray-500">Digite acima para buscar.</p>`
      }, 300)
    }

    setTimeout(() => searchInput.focus(), 200)
  }
  window.localizarProduto = window.abrirLocalizar

  searchInput.addEventListener('input', () => {
    const q = searchInput.value.trim().toLowerCase()
    if (!q) {
      resultsBox.innerHTML = `<p class="text-center text-gray-500">Digite acima para buscar.</p>`
      return
    }
    const found = allProducts.filter(p =>
      (p.nome || '').toLowerCase().includes(q) || (p.codigo_barras || '').includes(q)
    )
    if (!found.length) {
      resultsBox.innerHTML = `<p class="text-center text-gray-500">Nenhum produto encontrado.</p>`
      return
    }
    resultsBox.innerHTML = ''
    found.forEach(p => {
      const el = document.createElement('div')
      el.className = 'p-3 hover:bg-gray-100 rounded-lg cursor-pointer flex justify-between items-center'
      el.innerHTML = `
        <div>
          <strong>${p.nome}</strong><br>
          <small class="text-gray-500">${p.codigo_barras}</small>
        </div>
        <div class="text-gray-600">R$ ${parseNum(p.preco).toFixed(2)}</div>
      `
      el.addEventListener('click', () => {
        codigoInp.value = p.codigo_barras
        quantInp.focus()
        searchToggle.checked = false
      })
      resultsBox.appendChild(el)
    })
  })

  function updateResumo() {
    const tot = parseNum(totalSpan.textContent)
    const pct = parseFloat(descInput.value) || 0
    document.getElementById('totalModal').textContent = (tot * (1 - pct/100)).toFixed(2)
    recInput.min = (tot * (1 - pct/100)).toFixed(2)
  }

  function calculaTroco() {
    const tot = parseNum(totalSpan.textContent)
    const pct = parseFloat(descInput.value) || 0
    const base = tot * (1 - pct/100)
    const rec = parseFloat(recInput.value) || 0
    const troco = rec - base
    const metodo = document.querySelector('input[name="pagamento"]:checked').value
    if (metodo === 'dinheiro' && rec >= base) {
      trocoCont.classList.remove('hidden')
      trocoInput.value = troco.toFixed(2)
    } else {
      trocoCont.classList.add('hidden')
      trocoInput.value = '0.00'
    }
  }

  function initModal() {
    descInput.value = '0'
    descInput.placeholder = 'Digite um desconto...'
    recInput.value = ''
    recInput.placeholder = 'Quanto o cliente pagou?'
    trocoCont.classList.add('hidden')
    updateResumo()
  }

  descInput.addEventListener('input', () => { updateResumo(); calculaTroco() })
  recInput.addEventListener('input', calculaTroco)
  payRads.forEach(r => r.addEventListener('change', calculaTroco))

  window.abrirModalPagamento = () => {
    payToggle.checked = true
    initModal()
  }

  btnConfirm.addEventListener('click', () => {
    const pagamento = document.querySelector('input[name="pagamento"]:checked').value
    const desconto = parseFloat(descInput.value) || 0
    const dados = { pagamento, desconto }

    fetch('/finalizar_venda', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(dados)
    })
    .then(r => {
      if (!r.ok) return r.json().then(d => { throw d })
      location.reload()
    })
    .catch(err => {
      showToast(err.error || 'Erro ao finalizar venda.')
    })
  })

  document.addEventListener('keydown', e => {
    if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return
    switch (e.key) {
      case 'F1': e.preventDefault(); window.location = '/?limpar=1'; break
      case 'F2': e.preventDefault(); abrirModalPagamento(); break
      case 'F3': e.preventDefault(); codigoInp.focus(); break
      case 'F5': e.preventDefault(); abrirLocalizar(); break
      case 'F6': e.preventDefault(); cancelarProduto(); break
      case 'F9': e.preventDefault(); cancelarVenda(); break
      case 'Escape':
        payToggle.checked = false
        searchToggle.checked = false
        break
    }
  })

  btnMenu.addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('hidden')
  })

  window.cancelarVenda = () => {
    if (confirm('Deseja cancelar todo o pedido?')) {
      fetch('/cancelar_venda', { method: 'POST' }).then(() => location.reload())
    }
  }
  window.cancelarProduto = () => {
    form.reset()
    quantInp.value = '1.000'
    codigoInp.focus()
  }

  updateFinal()
})
