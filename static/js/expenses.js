// ============================================================
// FocusPulse — Expense Tracker Module
// expenses.js — All CRUD, analytics, filter, chart logic
// ============================================================

// ─── Constants ───────────────────────────────────────────────
const STORAGE_KEY = 'fp_expenses';
const BUDGET_KEY  = 'fp_expense_budget';

const CATEGORIES = [
  { label: '🍔 Food',             value: 'Food',             color: '#f59e0b' },
  { label: '📚 Study Materials',  value: 'Study Materials',  color: '#6366f1' },
  { label: '🚌 Transport',        value: 'Transport',        color: '#10b981' },
  { label: '🎮 Entertainment',    value: 'Entertainment',    color: '#ec4899' },
  { label: '🏥 Health',           value: 'Health',           color: '#ef4444' },
  { label: '🛍️ Shopping',         value: 'Shopping',         color: '#8b5cf6' },
  { label: '🏠 Housing/Rent',     value: 'Housing',          color: '#14b8a6' },
  { label: '📱 Utilities',        value: 'Utilities',        color: '#64748b' },
  { label: '💡 Other',            value: 'Other',            color: '#94a3b8' },
];

// ─── State ───────────────────────────────────────────────────
let expenses   = [];
let editingId  = null;
let filterCat  = 'All';
let filterDate = '';
let chart      = null;

// ─── LocalStorage Helpers ─────────────────────────────────────
function loadExpenses() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
  } catch {
    return [];
  }
}

function saveExpenses() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(expenses));
}

function getBudget() {
  return parseFloat(localStorage.getItem(BUDGET_KEY)) || 0;
}

function saveBudget(val) {
  localStorage.setItem(BUDGET_KEY, val);
}

// ─── Unique ID Generator ──────────────────────────────────────
function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

// ─── Date Helpers ─────────────────────────────────────────────
function todayStr() {
  return new Date().toISOString().split('T')[0];
}

function currentMonthLabel() {
  return new Date().toLocaleString('default', { month: 'long', year: 'numeric' });
}

function isCurrentMonth(dateStr) {
  const d   = new Date(dateStr);
  const now = new Date();
  return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
}

function isCurrentWeek(dateStr) {
  const d   = new Date(dateStr);
  const now = new Date();
  const startOfWeek = new Date(now);
  startOfWeek.setDate(now.getDate() - now.getDay());
  startOfWeek.setHours(0, 0, 0, 0);
  return d >= startOfWeek;
}

// ─── Core CRUD ───────────────────────────────────────────────
function addExpense(amount, category, date, description) {
  const expense = {
    id: generateId(),
    amount: parseFloat(amount),
    category,
    date,
    description: description.trim(),
    createdAt: Date.now(),
  };
  expenses.unshift(expense);
  saveExpenses();
  return expense;
}

function deleteExpense(id) {
  expenses = expenses.filter(e => e.id !== id);
  saveExpenses();
}

function updateExpense(id, amount, category, date, description) {
  const idx = expenses.findIndex(e => e.id === id);
  if (idx !== -1) {
    expenses[idx] = { ...expenses[idx], amount: parseFloat(amount), category, date, description: description.trim() };
    saveExpenses();
  }
}

// ─── Filtering ───────────────────────────────────────────────
function getFiltered() {
  return expenses.filter(e => {
    const catOk  = filterCat === 'All' || e.category === filterCat;
    const dateOk = !filterDate || e.date === filterDate;
    return catOk && dateOk;
  });
}

// ─── Analytics Helpers ────────────────────────────────────────
function getMonthlyTotal() {
  return expenses
    .filter(e => isCurrentMonth(e.date))
    .reduce((s, e) => s + e.amount, 0);
}

function getWeeklyTotal() {
  return expenses
    .filter(e => isCurrentWeek(e.date))
    .reduce((s, e) => s + e.amount, 0);
}

function getCategoryBreakdown() {
  const map = {};
  expenses.filter(e => isCurrentMonth(e.date)).forEach(e => {
    map[e.category] = (map[e.category] || 0) + e.amount;
  });
  return map;
}

function getTopCategory() {
  const bd  = getCategoryBreakdown();
  let top   = null, max = 0;
  for (const [cat, amt] of Object.entries(bd)) {
    if (amt > max) { max = amt; top = cat; }
  }
  return top;
}

// ─── DOM Rendering Helpers ────────────────────────────────────
function catColor(catValue) {
  const c = CATEGORIES.find(c => c.value === catValue);
  return c ? c.color : '#94a3b8';
}

function catLabel(catValue) {
  const c = CATEGORIES.find(c => c.value === catValue);
  return c ? c.label : catValue;
}

function fmt(amount) {
  return '₹' + amount.toLocaleString('en-IN', { minimumFractionDigits: 2 });
}

// ─── UI: Stats Cards ─────────────────────────────────────────
function renderStats() {
  const monthTotal = getMonthlyTotal();
  const weekTotal  = getWeeklyTotal();
  const topCat     = getTopCategory();
  const budget     = getBudget();
  const budgetPct  = budget > 0 ? Math.min(100, (monthTotal / budget) * 100) : 0;
  const overBudget = budget > 0 && monthTotal > budget;

  document.getElementById('stat-month-total').textContent = fmt(monthTotal);
  document.getElementById('stat-week-total').textContent  = fmt(weekTotal);
  document.getElementById('stat-top-cat').textContent     = topCat ? catLabel(topCat) : '—';
  document.getElementById('stat-count').textContent       = expenses.filter(e => isCurrentMonth(e.date)).length;
  document.getElementById('month-label').textContent      = currentMonthLabel();

  // Budget bar
  const budgetSection = document.getElementById('budget-section');
  if (budget > 0) {
    budgetSection.style.display = 'block';
    document.getElementById('budget-bar-fill').style.width       = budgetPct + '%';
    document.getElementById('budget-bar-fill').style.background  = overBudget ? '#ef4444' : '#6366f1';
    document.getElementById('budget-text').textContent           = fmt(monthTotal) + ' / ' + fmt(budget);
    document.getElementById('budget-alert').style.display        = overBudget ? 'flex' : 'none';
  } else {
    budgetSection.style.display = 'none';
  }

  // Cross-module insight
  renderInsight(monthTotal, budget);
}

function renderInsight(monthTotal, budget) {
  const insightBox = document.getElementById('expense-insight');
  if (!insightBox) return;
  let msg = '';
  if (budget > 0 && monthTotal > budget * 0.8) {
    msg = '⚠️ You\'ve used over 80% of your monthly budget. Consider cutting back on entertainment!';
  } else if (monthTotal > 5000) {
    msg = '💡 You\'ve spent a significant amount this month. Review your spending in the breakdown below.';
  } else {
    msg = '✅ Your spending looks healthy this month. Keep tracking to stay on top of your finances!';
  }
  insightBox.textContent = msg;
}

// ─── UI: Expense Table ────────────────────────────────────────
function renderTable() {
  const list    = getFiltered();
  const tbody   = document.getElementById('expense-tbody');
  const empty   = document.getElementById('expense-empty');
  tbody.innerHTML = '';

  if (list.length === 0) {
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';

  list.forEach(e => {
    const tr = document.createElement('tr');
    tr.dataset.id = e.id;
    tr.innerHTML = `
      <td style="padding:14px 16px; font-size:14px; color:var(--core-muted);">${e.date}</td>
      <td style="padding:14px 16px; font-weight:600;">${e.description || '<span style="color:var(--core-muted);font-style:italic;">No description</span>'}</td>
      <td style="padding:14px 16px;">
        <span style="background:${catColor(e.category)}22; color:${catColor(e.category)}; padding:4px 10px; border-radius:20px; font-size:12px; font-weight:700;">${catLabel(e.category)}</span>
      </td>
      <td style="padding:14px 16px; font-weight:700; font-size:16px;">${fmt(e.amount)}</td>
      <td style="padding:14px 16px;">
        <div style="display:flex; gap:8px;">
          <button onclick="openEdit('${e.id}')" style="background:var(--indigo-primary)22; color:var(--indigo-primary); border:none; padding:6px 12px; border-radius:8px; font-size:12px; font-weight:600; cursor:pointer;">✏️ Edit</button>
          <button onclick="confirmDelete('${e.id}')" style="background:#ef444422; color:#ef4444; border:none; padding:6px 12px; border-radius:8px; font-size:12px; font-weight:600; cursor:pointer;">🗑️ Delete</button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// ─── UI: Chart.js Pie Chart ───────────────────────────────────
function renderChart() {
  const breakdown = getCategoryBreakdown();
  const labels    = Object.keys(breakdown).map(catLabel);
  const data      = Object.values(breakdown);
  const colors    = Object.keys(breakdown).map(catColor);

  const ctx = document.getElementById('expense-chart');
  if (!ctx) return;

  if (chart) chart.destroy();

  if (data.length === 0) {
    document.getElementById('chart-empty').style.display = 'flex';
    ctx.style.display = 'none';
    return;
  }
  document.getElementById('chart-empty').style.display = 'none';
  ctx.style.display = 'block';

  chart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data, backgroundColor: colors, borderWidth: 3, borderColor: 'var(--core-surface)' }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#94a3b8', font: { size: 12, family: 'Inter, sans-serif' }, padding: 16 }
        },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.label}: ₹${ctx.raw.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
          }
        }
      }
    }
  });
}

// ─── Full Re-render ───────────────────────────────────────────
function renderAll() {
  renderStats();
  renderTable();
  renderChart();
}

// ─── Modal Logic ─────────────────────────────────────────────
function openAdd() {
  editingId = null;
  document.getElementById('modal-title').textContent = 'Add New Expense';
  document.getElementById('exp-amount').value      = '';
  document.getElementById('exp-category').value    = 'Food';
  document.getElementById('exp-date').value        = todayStr();
  document.getElementById('exp-description').value = '';
  document.getElementById('delete-exp-btn').style.display = 'none';
  document.getElementById('expense-modal').style.display  = 'flex';
  document.getElementById('exp-amount').focus();
}

function openEdit(id) {
  const e = expenses.find(ex => ex.id === id);
  if (!e) return;
  editingId = id;
  document.getElementById('modal-title').textContent = 'Edit Expense';
  document.getElementById('exp-amount').value      = e.amount;
  document.getElementById('exp-category').value    = e.category;
  document.getElementById('exp-date').value        = e.date;
  document.getElementById('exp-description').value = e.description;
  document.getElementById('delete-exp-btn').style.display = 'inline-flex';
  document.getElementById('expense-modal').style.display  = 'flex';
  document.getElementById('exp-amount').focus();
}

function closeModal() {
  document.getElementById('expense-modal').style.display = 'none';
  editingId = null;
}

function confirmDelete(id) {
  if (confirm('Delete this expense? This cannot be undone.')) {
    deleteExpense(id);
    renderAll();
    closeModal();
  }
}

// ─── Form Submission ─────────────────────────────────────────
function handleFormSubmit(e) {
  e.preventDefault();
  const amount      = document.getElementById('exp-amount').value.trim();
  const category    = document.getElementById('exp-category').value;
  const date        = document.getElementById('exp-date').value;
  const description = document.getElementById('exp-description').value;

  // Validation
  if (!amount || isNaN(parseFloat(amount)) || parseFloat(amount) <= 0) {
    showError('Please enter a valid positive amount.');
    return;
  }
  if (!date) {
    showError('Please select a date.');
    return;
  }

  if (editingId) {
    updateExpense(editingId, amount, category, date, description);
  } else {
    addExpense(amount, category, date, description);
  }

  closeModal();
  renderAll();
  checkBudgetAlert();
}

function showError(msg) {
  const el = document.getElementById('form-error');
  el.textContent = msg;
  el.style.display = 'block';
  setTimeout(() => { el.style.display = 'none'; }, 3000);
}

// ─── Budget Alert ─────────────────────────────────────────────
function checkBudgetAlert() {
  const budget = getBudget();
  if (!budget) return;
  const monthly = getMonthlyTotal();
  if (monthly > budget) {
    document.getElementById('budget-alert').style.display = 'flex';
  }
}

// ─── Budget Modal ─────────────────────────────────────────────
function openBudgetModal() {
  document.getElementById('budget-input').value = getBudget() || '';
  document.getElementById('budget-modal').style.display = 'flex';
}

function closeBudgetModal() {
  document.getElementById('budget-modal').style.display = 'none';
}

function saveBudgetSetting() {
  const val = parseFloat(document.getElementById('budget-input').value);
  if (!isNaN(val) && val > 0) {
    saveBudget(val);
  } else {
    saveBudget(0);
  }
  closeBudgetModal();
  renderAll();
}

// ─── Filters ─────────────────────────────────────────────────
function applyFilters() {
  filterCat  = document.getElementById('filter-cat').value;
  filterDate = document.getElementById('filter-date').value;
  renderTable();
}

function clearFilters() {
  filterCat  = 'All';
  filterDate = '';
  document.getElementById('filter-cat').value  = 'All';
  document.getElementById('filter-date').value = '';
  renderTable();
}

// ─── Populate Category Dropdowns ──────────────────────────────
function populateCategoryDropdowns() {
  const formSelect   = document.getElementById('exp-category');
  const filterSelect = document.getElementById('filter-cat');

  CATEGORIES.forEach(c => {
    const opt1 = new Option(c.label, c.value);
    formSelect.appendChild(opt1);
    const opt2 = new Option(c.label, c.value);
    filterSelect.appendChild(opt2);
  });
}

// ─── Boot ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  expenses = loadExpenses();

  populateCategoryDropdowns();
  renderAll();

  // Form submit
  document.getElementById('expense-form').addEventListener('submit', handleFormSubmit);

  // Close modal on backdrop click
  document.getElementById('expense-modal').addEventListener('click', e => {
    if (e.target === document.getElementById('expense-modal')) closeModal();
  });
  document.getElementById('budget-modal').addEventListener('click', e => {
    if (e.target === document.getElementById('budget-modal')) closeBudgetModal();
  });
});
