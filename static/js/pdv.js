// static/js/pdv.js
// --------------------------------------------------
// PDV Hortifrutti - Script completo (~230 linhas)
// Adiciona busca “Localizar Produtos” em modal + todo o resto
// --------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  // ——— estado da busca ———
  let allProducts = []

  // ——— adicionar produtos ———
  const form        = document.getElementById('addForm')
  const codigoInp   = document.getElementById('codigoInput')
  const quantInp    = document.getElementById('quantidadeInput')
  const errCod      = document.getElementById('error-codigo')
  const errQt       = document.getElementById('error-quantidade')

  // ——— carrinho & finalização ———
  const cartArea    = document.getElementById('cartItems')
  const btnFinal    = document.getElementById('btnFinalizar')
  const totalSpan   = document.getElementById('totalVenda')

  // ——— modal pagamento ———
  const payToggle   = document.getElementById('modal-finalizar-toggle')
  const descInput   = document.getElementById('modal-desconto')
  const recInput    = document.getElementById('modal-recebido')
  const trocoCont   = document.getElementById('trocoContainer')
  const trocoInput  = document.getElementById('modal-troco')
  const payRads     = document.querySelectorAll('input[name="pagamento"]')
  const btnConfirm  = document.getElementById('btn-confirmar-venda')

  // ——— modal busca ———
  const searchToggle  = document.getElementById('modal-search-toggle')
  const searchInput   = document.getElementById('searchInput')
  const resultsBox    = document.getElementById('searchResults')

  // converter R$ … ou texto → float
  function parseNum(str) {
    return parseFloat(str.replace(/[^\d\.]/g, '')) || 0
  }

  // ————————————————————————————————————————————————
  // ABRIR “LOCALIZAR PRODUTOS” — carrega only once
  // ————————————————————————————————————————————————
  window.abrirLocalizar = () => {
    searchToggle.checked = true
    searchInput.value = ''
    resultsBox.innerHTML = '<p class="text-center text-gray-500">Digite acima para buscar.</p>'

    if (!allProducts.length) {
      fetch('/api/produtos')
        .then(r => r.json())
        .then(json => {
          allProducts = json
        })
        .catch(_=>{
          resultsBox.innerHTML = '<p class="text-center text-red-500">Falha ao carregar produtos.</p>'
        })
    }
    // foco
    setTimeout(()=> searchInput.focus(), 200)
  }
  window.localizarProduto = window.abrirLocalizar

  // ————————————————————————————————————————————————
  // FILTRAR enquanto digita
  // ————————————————————————————————————————————————
  searchInput.addEventListener('input', ()=>{
    const q = searchInput.value.trim().toLowerCase()
    if (!q) {
      resultsBox.innerHTML = '<p class="text-center text-gray-500">Digite acima para buscar.</p>'
      return
    }
    const found = allProducts.filter(p=>{
      return (p.nome||'').toLowerCase().includes(q)
          || (p.codigo_barras||'').includes(q)
    })
    if (!found.length) {
      resultsBox.innerHTML = '<p class="text-center text-gray-500">Nenhum produto encontrado.</p>'
      return
    }
    // monta lista
    resultsBox.innerHTML = ''
    found.forEach(p=>{
      const el = document.createElement('div')
      el.className = 'p-3 hover:bg-gray-100 rounded-lg cursor-pointer flex justify-between items-center'
      el.innerHTML = `
        <div>
          <strong>${p.nome}</strong><br>
          <small class="text-gray-500">${p.codigo_barras}</small>
        </div>
        <div class="text-gray-600">R$ ${parseNum(p.preco).toFixed(2)}</div>
      `
      el.addEventListener('click', ()=>{
        codigoInp.value = p.codigo_barras
        quantInp.focus()
        searchToggle.checked = false
      })
      resultsBox.appendChild(el)
    })
  })

  // ————————————————————————————————————————————————
  // VALIDAR e enviar adicionar produto
  // ————————————————————————————————————————————————
  form.addEventListener('submit', e=>{
    e.preventDefault()
    errCod.classList.add('hidden'); errQt.classList.add('hidden')

    fetch('/validar_produto',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        codigo_barras: codigoInp.value.trim(),
        quantidade:    quantInp.value.trim()
      })
    })
    .then(async res=>{
      if (res.ok) return form.submit()
      const data = await res.json().catch(()=>({message:'Erro.'}))
      if (res.status===404) {
        errCod.textContent = data.message
        errCod.classList.remove('hidden')
        codigoInp.focus()
      } else {
        errQt.textContent = data.message
        errQt.classList.remove('hidden')
        quantInp.focus()
      }
    })
    .catch(_=>{
      window.dispatchEvent(new CustomEvent('toast',{detail:'Erro na validação.'}))
    })
  })

  // ————————————————————————————————————————————————
  // TOAST de carregamento
  // ————————————————————————————————————————————————
  window.dispatchEvent(new CustomEvent('toast',{detail:'PDV carregado!'}))

  // ————————————————————————————————————————————————
  // ATALHOS teclado
  // ————————————————————————————————————————————————
  document.addEventListener('keydown', e=>{
    if (['INPUT','TEXTAREA'].includes(e.target.tagName)) return
    switch(e.key){
      case 'F1': e.preventDefault(); openMenu(); break
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

  // ————————————————————————————————————————————————
  // MODAL Pagamento: resumo + troco
  // ————————————————————————————————————————————————
  function updateResumo(){
    const tot = parseNum(totalSpan.textContent)
    const pct = parseFloat(descInput.value)||0
    document.getElementById('modal-total').textContent          = tot.toFixed(2)
    document.getElementById('modal-desconto-total').textContent = `${pct.toFixed(0)}%`
    recInput.min = (tot*(1-pct/100)).toFixed(2)
  }
  function calculaTroco(){
    const tot = parseNum(totalSpan.textContent)
    const pct = parseFloat(descInput.value)||0
    const base = tot*(1-pct/100)
    const rec  = parseFloat(recInput.value)||0
    const troco = rec - base
    const metodo = document.querySelector('input[name="pagamento"]:checked').value
    if (metodo==='dinheiro' && rec>=base){
      trocoCont.classList.remove('hidden')
      trocoInput.value = troco.toFixed(2)
    } else {
      trocoCont.classList.add('hidden')
      trocoInput.value = '0.00'
    }
  }
  function initModal(){
    descInput.value = '0'
    recInput.value  = ''
    trocoCont.classList.add('hidden')
    updateResumo()
  }
  descInput.addEventListener('input', ()=>{
    updateResumo(); calculaTroco()
  })
  recInput.addEventListener('input', calculaTroco)
  payRads.forEach(r=> r.addEventListener('change', calculaTroco))

  window.abrirModalPagamento = ()=>{
    payToggle.checked = true
    initModal()
  }

  // ————————————————————————————————————————————————
  // habilita/desabilita Finalizar
  // ————————————————————————————————————————————————
  function updateFinal(){
    btnFinal.disabled = !(cartArea.querySelectorAll('article').length>0)
  }
  new MutationObserver(updateFinal)
    .observe(cartArea,{ childList:true, subtree:true })
  updateFinal()

  // ————————————————————————————————————————————————
  // confirmar venda
  // ————————————————————————————————————————————————
  btnConfirm.addEventListener('click', ()=>{
    const pagamento = document.querySelector('input[name="pagamento"]:checked').value
    const desconto  = parseFloat(descInput.value)||0
    const dados     = { pagamento, desconto }
    fetch('/finalizar_venda',{
      method:'POST',
      headers:{ 'Content-Type':'application/json' },
      body: JSON.stringify(dados)
    })
    .then(r=>{
      if (!r.ok) throw new Error()
      location.reload()
    })
    .catch(_=>{
      const pend = JSON.parse(localStorage.getItem('pendentes')||'[]')
      pend.push(dados)
      localStorage.setItem('pendentes', JSON.stringify(pend))
      window.dispatchEvent(new CustomEvent('toast',{detail:'Venda salva offline.'}))
      setTimeout(()=>location.reload(),1000)
    })
  })
  window.addEventListener('online', ()=>{
    const pend = JSON.parse(localStorage.getItem('pendentes')||'[]')
    pend.forEach(dados=>{
      fetch('/finalizar_venda',{
        method:'POST',
        headers:{ 'Content-Type':'application/json' },
        body: JSON.stringify(dados)
      })
    })
    localStorage.removeItem('pendentes')
  })

  // ————————————————————————————————————————————————
  // auxiliares finais
  // ————————————————————————————————————————————————
  window.cancelarVenda = ()=>{
    if (confirm('Deseja cancelar todo o pedido?')){
      fetch('/cancelar_venda',{ method:'POST' })
        .then(()=>location.reload())
    }
  }
  window.cancelarProduto = ()=>{
    form.reset()
    quantInp.value = '1.000'
    codigoInp.focus()
  }
  window.openMenu = ()=>{
    const sb = document.getElementById('sidebar')
    if (sb) sb.classList.toggle('hidden')
  }
  window.removerItem = idx=>{
    if (confirm('Remover este item?')){
      fetch('/remove_item',{
        method:'POST',
        headers:{ 'Content-Type':'application/json' },
        body: JSON.stringify({ index: idx })
      }).then(()=>location.reload())
    }
  }
  window.editarItem = idx=>{
    console.log('Editar', idx)
  }

})
