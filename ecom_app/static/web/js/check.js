 const shipRadios = document.querySelectorAll('input[name="ship"]');
  const shipCostEl = document.getElementById('shipCost');
  const totalEl = document.getElementById('grandTotal');

  const baseSubtotal = 2097; // demo value (update from real cart)

  function formatINR(n){
    return '₹' + n.toLocaleString('en-IN');
  }

  function updateTotals(){
    // Standard ₹0, Express ₹99 (based on selected index)
    const selected = [...shipRadios].findIndex(r => r.checked);
    const ship = selected === 1 ? 99 : 0;
    shipCostEl.textContent = formatINR(ship);
    totalEl.textContent = formatINR(baseSubtotal + ship);
  }

  shipRadios.forEach(r => r.addEventListener('change', updateTotals));
  updateTotals();