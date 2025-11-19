const API_BASE = window.__API_BASE__ || '/api';

function normalizeDateString(value) {
  if (!value) return null;
  const text = String(value).trim();
  if (!text) return null;
  if (text.length >= 10) {
    return text.slice(0, 10);
  }
  return text;
}

async function fetchJSON(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

const datePicker = document.getElementById('date-picker');
const prevButton = document.getElementById('prev-day');
const nextButton = document.getElementById('next-day');
const todayButton = document.getElementById('today');
const openPickerButton = document.getElementById('date-open');
const selectedDateDisplay = document.getElementById('selected-date-display');
const customCalendar = document.getElementById('custom-calendar');
const calendarGrid = document.getElementById('calendar-grid');
const calendarMonthYear = document.getElementById('calendar-month-year');
const calendarPrevMonth = document.getElementById('calendar-prev-month');
const calendarNextMonth = document.getElementById('calendar-next-month');

let currentDate = null; // YYYY-MM-DD
let availableDates = [];
let calendarVisible = false;
let calendarYear = new Date().getFullYear();
let calendarMonth = new Date().getMonth(); // 0-11

function toISODate(date) {
  return date.toISOString().slice(0, 10);
}

function getTodayISO() {
  const now = new Date();
  return toISODate(now);
}

function buildPaperQuery({ limit = 12, breakthroughOnly = false, targetDate }) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (breakthroughOnly) params.set('breakthrough_only', 'true');
  if (targetDate) params.set('target_date', normalizeDateString(targetDate));
  return `/papers?${params.toString()}`;
}

function renderPaper(paper) {
  const card = document.createElement('article');
  card.className = 'card';

  const title = document.createElement('h3');
  title.textContent = paper.title;
  card.appendChild(title);

  const meta = document.createElement('p');
  meta.className = 'meta';
  meta.textContent = `${paper.authors.slice(0, 3).join(', ')}${paper.authors.length > 3 ? ' et al.' : ''}`;
  card.appendChild(meta);

  if (paper.breakthrough_label) {
    const badge = document.createElement('span');
    badge.className = 'badge';
    badge.textContent = `Breakthrough • ${(paper.breakthrough_score * 100).toFixed(0)}%`;
    card.appendChild(badge);
  }

  if (paper.breakthrough_reason) {
    const reason = document.createElement('p');
    reason.className = 'meta';
    reason.textContent = `理由：${paper.breakthrough_reason}`;
    card.appendChild(reason);
  }

  const problem = document.createElement('p');
  problem.className = 'summary';
  problem.innerHTML = `<strong class="label">Problem</strong><br>${paper.problem_summary || 'Pending analysis.'}`;
  card.appendChild(problem);

  const solution = document.createElement('p');
  solution.className = 'summary';
  solution.innerHTML = `<strong class="label">Solution</strong><br>${paper.solution_summary || 'Pending analysis.'}`;
  card.appendChild(solution);

  const effect = document.createElement('p');
  effect.className = 'summary';
  effect.innerHTML = `<strong class="label">Effect</strong><br>${paper.effect_summary || 'Pending analysis.'}`;
  card.appendChild(effect);

  const links = document.createElement('p');
  links.className = 'meta';
  links.innerHTML = `<a href="https://arxiv.org/abs/${paper.arxiv_id}" target="_blank" rel="noopener">arXiv</a> · <a href="https://huggingface.co/papers/${paper.arxiv_id}" target="_blank" rel="noopener">HF daily</a>`;
  card.appendChild(links);

  return card;
}

function populatePaperLists(papers, breakthroughs) {
  const paperContainer = document.getElementById('papers-list');
  const breakthroughContainer = document.getElementById('breakthrough-list');
  paperContainer.textContent = '';
  breakthroughContainer.textContent = '';

  if (papers.length === 0) {
    const empty = document.createElement('p');
    empty.className = 'meta';
    empty.textContent = '该日期暂无论文摘要。';
    paperContainer.appendChild(empty);
  } else {
    papers.forEach((paper) => {
      paperContainer.appendChild(renderPaper(paper));
    });
  }

  if (breakthroughs.length === 0) {
    const empty = document.createElement('p');
    empty.className = 'meta';
    empty.textContent = 'No breakthrough papers flagged today.';
    breakthroughContainer.appendChild(empty);
  } else {
    breakthroughs.forEach((paper) => {
      breakthroughContainer.appendChild(renderPaper(paper));
    });
  }
}

function renderKeywordStats(stats) {
  const table = document.getElementById('keyword-table');
  table.textContent = '';
  stats.slice(0, 12).forEach((item) => {
    const li = document.createElement('li');
    li.innerHTML = `<span>${item.keyword}</span><span>${item.paper_count}</span>`;
    table.appendChild(li);
  });

  const ctx = document.getElementById('keyword-chart').getContext('2d');
  if (window.keywordChart) {
    window.keywordChart.destroy();
  }
  window.keywordChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: stats.slice(0, 10).map((item) => item.keyword),
      datasets: [
        {
          label: 'Mentions',
          data: stats.slice(0, 10).map((item) => item.paper_count),
          backgroundColor: 'rgba(56, 189, 248, 0.6)',
        },
      ],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#cbd5f5' } },
        y: { ticks: { color: '#cbd5f5' }, beginAtZero: true },
      },
    },
  });
}

async function loadDashboard() {
  try {
    const [papers, breakthroughs, keywordStats] = await Promise.all([
      fetchJSON(buildPaperQuery({ limit: 12, targetDate: currentDate || undefined })),
      fetchJSON(buildPaperQuery({ limit: 6, breakthroughOnly: true, targetDate: currentDate || undefined })),
      fetchJSON('/keywords/stats'),
    ]);
    populatePaperLists(papers, breakthroughs);
    renderKeywordStats(keywordStats);
    updateNavigationState();
  } catch (error) {
    console.error('Failed to load dashboard', error);
  }
}

function initSubscriptionForm() {
  const form = document.getElementById('subscribe-form');
  const feedback = document.getElementById('subscribe-feedback');
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    feedback.textContent = 'Submitting...';
    const formData = new FormData(form);
    try {
      const response = await fetch(`${API_BASE}/subscribers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: formData.get('email') }),
      });
      if (!response.ok) {
        const error = await response.json();
        feedback.textContent = error.detail || 'Subscription failed.';
        feedback.style.color = 'rgba(248, 113, 113, 0.9)';
        return;
      }
      feedback.textContent = 'Check your inbox to confirm subscription.';
      feedback.style.color = 'rgba(94, 234, 212, 0.9)';
      form.reset();
    } catch (error) {
      feedback.textContent = 'Network error. Try again later.';
      feedback.style.color = 'rgba(248, 113, 113, 0.9)';
    }
  });
}

function updateNavigationState() {
  if (!prevButton || !nextButton) return;
  if (!availableDates.length) {
    prevButton.disabled = true;
    nextButton.disabled = true;
    return;
  }
  const index = currentDate ? availableDates.indexOf(currentDate) : -1;
  prevButton.disabled = index === -1 ? false : index === availableDates.length - 1;
  nextButton.disabled = index === -1 ? false : index === 0;
}

function setCurrentDate(date, triggerLoad = true) {
  currentDate = date ? normalizeDateString(date) : null;
  if (datePicker) {
    datePicker.value = date || '';
  }
  
  // 更新显示的日期
  if (selectedDateDisplay) {
    selectedDateDisplay.textContent = currentDate || '选择日期';
  }

  updateNavigationState();
  hideCalendar();
  if (triggerLoad) {
    loadDashboard();
  }
}

function shiftDate(step) {
  if (!availableDates.length) return;
  if (!currentDate) {
    const startIndex = step > 0 ? availableDates.length - 1 : 0;
    setCurrentDate(availableDates[startIndex]);
    return;
  }
  const index = availableDates.indexOf(currentDate);
  if (index === -1) {
    const startIndex = step > 0 ? availableDates.length - 1 : 0;
    setCurrentDate(availableDates[startIndex]);
    return;
  }
  const nextIndex = index + step; // availableDates sorted descending
  if (nextIndex >= 0 && nextIndex < availableDates.length) {
    setCurrentDate(availableDates[nextIndex]);
  }
}

async function loadAvailability() {
  try {
    const dates = await fetchJSON('/papers/calendar');
    availableDates = Array.isArray(dates)
      ? [...new Set(dates.map(normalizeDateString))].filter(Boolean)
      : [];
    availableDates.sort((a, b) => (a > b ? -1 : 1));
    if (datePicker && availableDates.length) {
      datePicker.min = availableDates[availableDates.length - 1];
      datePicker.max = availableDates[0];
    }
    if (!currentDate && availableDates.length) {
      setCurrentDate(availableDates[0], false);
    } else {
      updateNavigationState();
    }
    loadDashboard();
  } catch (error) {
    console.error('Failed to load available dates', error);
    loadDashboard();
  }
}

// 自定义日历功能
function getMonthName(month) {
  const names = ['January', 'February', 'March', 'April', 'May', 'June', 
                 'July', 'August', 'September', 'October', 'November', 'December'];
  return names[month];
}

function renderCalendar() {
  if (!calendarGrid) return;

  // 更新月份年份显示
  calendarMonthYear.textContent = `${getMonthName(calendarMonth)} ${calendarYear}`;

  // 清空日历网格
  calendarGrid.innerHTML = '';

  // 添加星期标题
  const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  weekdays.forEach(day => {
    const header = document.createElement('div');
    header.className = 'calendar-weekday';
    header.textContent = day;
    calendarGrid.appendChild(header);
  });

  // 计算当月第一天是星期几
  const firstDay = new Date(calendarYear, calendarMonth, 1);
  const lastDay = new Date(calendarYear, calendarMonth + 1, 0);
  const firstDayOfWeek = firstDay.getDay();
  const daysInMonth = lastDay.getDate();
  
  // 添加空白格子
  for (let i = 0; i < firstDayOfWeek; i++) {
    const empty = document.createElement('div');
    empty.className = 'calendar-day empty';
    calendarGrid.appendChild(empty);
  }
  
  // 添加日期
  for (let day = 1; day <= daysInMonth; day++) {
    const dateStr = `${calendarYear}-${String(calendarMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    const dayCell = document.createElement('button');
    dayCell.type = 'button';
    dayCell.className = 'calendar-day';
    dayCell.textContent = day;
    
    // 检查是否有数据
    const hasData = availableDates.includes(dateStr);
    if (hasData) {
      dayCell.classList.add('has-data');
    }
    
    // 检查是否是当前选中的日期
    if (currentDate === dateStr) {
      dayCell.classList.add('selected');
    }
    
    // 检查是否是今天
    const today = getTodayISO();
    if (dateStr === today) {
      dayCell.classList.add('today');
    }
    
    // 点击事件
    dayCell.addEventListener('click', () => {
      if (hasData) {
        setCurrentDate(dateStr);
      }
    });
    
    // 如果没有数据，禁用按钮
    if (!hasData) {
      dayCell.disabled = true;
    }
    
    calendarGrid.appendChild(dayCell);
  }
}

function showCalendar() {
  if (!customCalendar) return;
  
  // 如果有当前日期，显示该日期所在的月份
  if (currentDate) {
    const date = new Date(currentDate);
    calendarYear = date.getFullYear();
    calendarMonth = date.getMonth();
  } else {
    // 否则显示当前月份
    const now = new Date();
    calendarYear = now.getFullYear();
    calendarMonth = now.getMonth();
  }
  
  renderCalendar();
  customCalendar.classList.add('visible');
  calendarVisible = true;
}

function hideCalendar() {
  if (!customCalendar) return;
  customCalendar.classList.remove('visible');
  calendarVisible = false;
}

function toggleCalendar() {
  if (calendarVisible) {
    hideCalendar();
  } else {
    showCalendar();
  }
}

function changeMonth(delta) {
  calendarMonth += delta;
  if (calendarMonth < 0) {
    calendarMonth = 11;
    calendarYear--;
  } else if (calendarMonth > 11) {
    calendarMonth = 0;
    calendarYear++;
  }
  renderCalendar();
}

function initControls() {
  if (datePicker) {
    datePicker.addEventListener('change', (event) => {
      const value = event.target.value;
      if (!value) {
        currentDate = null;
        updateNavigationState();
        loadDashboard();
        return;
      }
      if (!availableDates.includes(value)) {
        availableDates.push(value);
        availableDates.sort((a, b) => (a > b ? -1 : 1));
      }
      setCurrentDate(value);
    });
  }
  
  // 自定义日历按钮
  if (openPickerButton) {
    openPickerButton.addEventListener('click', toggleCalendar);
  }
  
  // 月份切换按钮
  if (calendarPrevMonth) {
    calendarPrevMonth.addEventListener('click', () => changeMonth(-1));
  }
  if (calendarNextMonth) {
    calendarNextMonth.addEventListener('click', () => changeMonth(1));
  }
  
  // 点击日历外部关闭
  if (customCalendar) {
    document.addEventListener('click', (e) => {
      if (calendarVisible &&
          !customCalendar.contains(e.target) &&
          !openPickerButton.contains(e.target)) {
        hideCalendar();
      }
    });
  }
  
  if (prevButton) {
    prevButton.addEventListener('click', () => shiftDate(1));
  }
  if (nextButton) {
    nextButton.addEventListener('click', () => {
      shiftDate(-1);
    });
  }
  if (todayButton) {
    todayButton.addEventListener('click', () => {
      if (availableDates.length) {
        setCurrentDate(availableDates[0]);
      } else {
        currentDate = null;
        loadDashboard();
      }
    });
  }
  updateNavigationState();
}

initControls();
loadAvailability();
initSubscriptionForm();