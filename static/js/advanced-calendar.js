document.addEventListener('DOMContentLoaded', function() {
    const calendarEl = document.getElementById('calendar');
    const taskModal = document.getElementById('taskModal');
    const taskForm = document.getElementById('taskForm');
    const openTaskModalBtn = document.getElementById('openTaskModalBtn');
    const closeTaskModalBtn = document.getElementById('closeTaskModalBtn');
    const deleteTaskBtn = document.getElementById('deleteTaskBtn');

    let calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        height: '100%',
        editable: true,
        selectable: true,
        selectMirror: true,
        dayMaxEvents: true,
        events: async function(info, successCallback, failureCallback) {
            try {
                const response = await fetch('/api/tasks');
                const tasks = await response.json();
                
                const events = tasks.map(t => {
                    let start = t.date;
                    if (t.start_time) {
                        start = `${t.date}T${t.start_time}`;
                    }
                    let end = null;
                    if (t.end_time) {
                        end = `${t.date}T${t.end_time}`;
                    }

                    return {
                        id: t.id,
                        title: t.title,
                        start: start,
                        end: end,
                        backgroundColor: t.color,
                        borderColor: t.color,
                        classNames: t.status === 'Completed' ? ['task-completed'] : [],
                        extendedProps: { ...t }
                    };
                });
                
                successCallback(events);
                updateSidebar(tasks);
            } catch (err) {
                console.error("Error fetching tasks", err);
                failureCallback(err);
            }
        },
        select: function(info) {
            openModal({ date: info.startStr.split('T')[0] });
        },
        eventClick: function(info) {
            openModal(info.event.extendedProps);
        },
        eventDrop: async function(info) {
            await updateTaskDates(info.event);
        },
        eventResize: async function(info) {
            await updateTaskDates(info.event);
        }
    });

    calendar.render();

    function openModal(task = {}) {
        document.getElementById('taskId').value = task.id || '';
        document.getElementById('taskTitleInput').value = task.title || '';
        document.getElementById('taskDescInput').value = task.description || '';
        
        let initialDate = task.date || '';
        document.getElementById('taskDateInput').value = initialDate;
        
        document.getElementById('taskStartTimeInput').value = task.start_time || '';
        document.getElementById('taskEndTimeInput').value = task.end_time || '';
        document.getElementById('taskPriorityInput').value = task.priority || 'Medium';
        document.getElementById('taskCategoryInput').value = task.category || 'Study';
        document.getElementById('taskColorInput').value = task.color || '#4F46E5';
        document.getElementById('taskCompleteInput').checked = task.status === 'Completed';

        document.getElementById('modalTitle').innerText = task.id ? 'Edit Task' : 'New Task';
        deleteTaskBtn.style.display = task.id ? 'block' : 'none';
        
        // Soft animated entrance
        taskModal.style.display = 'flex';
        setTimeout(() => taskModal.classList.add('show'), 10);
    }

    function closeModal() {
        taskModal.classList.remove('show');
        setTimeout(() => {
            taskModal.style.display = 'none';
            taskForm.reset();
        }, 300); // match transition
    }

    // Modal Events
    openTaskModalBtn.addEventListener('click', () => openModal());
    closeTaskModalBtn.addEventListener('click', closeModal);
    
    taskModal.addEventListener('click', (e) => {
        if (e.target === taskModal) closeModal();
    });

    taskForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('taskId').value;
        const payload = {
            title: document.getElementById('taskTitleInput').value,
            description: document.getElementById('taskDescInput').value,
            date: document.getElementById('taskDateInput').value,
            start_time: document.getElementById('taskStartTimeInput').value,
            end_time: document.getElementById('taskEndTimeInput').value,
            priority: document.getElementById('taskPriorityInput').value,
            category: document.getElementById('taskCategoryInput').value,
            color: document.getElementById('taskColorInput').value,
            status: document.getElementById('taskCompleteInput').checked ? 'Completed' : 'Pending'
        };

        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/tasks/${id}` : '/api/tasks';

        try {
            await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            closeModal();
            calendar.refetchEvents();
        } catch(e) {
            console.error(e);
        }
    });

    deleteTaskBtn.addEventListener('click', async () => {
        const id = document.getElementById('taskId').value;
        if (!id) return;
        if (confirm('Are you sure you want to delete this task?')) {
            await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
            closeModal();
            calendar.refetchEvents();
        }
    });

    async function updateTaskDates(event) {
        const id = event.extendedProps.id;
        // Parse dates from FullCalendar event object
        const newDate = event.startStr.split('T')[0];
        
        let newStartTime = '';
        if (event.startStr.includes('T')) {
            newStartTime = event.startStr.split('T')[1].substring(0, 5); 
        }
        
        let newEndTime = '';
        if (event.endStr && event.endStr.includes('T')) {
            newEndTime = event.endStr.split('T')[1].substring(0, 5);
        }

        const payload = {
            ...event.extendedProps,
            date: newDate,
            start_time: newStartTime || event.extendedProps.start_time,
            end_time: newEndTime || event.extendedProps.end_time
        };

        await fetch(`/api/tasks/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        calendar.refetchEvents();
    }

    function updateSidebar(tasks) {
        // Adjust strings logically to LocalTime ISO
        const today = new Date();
        const y = today.getFullYear();
        const m = String(today.getMonth() + 1).padStart(2, '0');
        const d = String(today.getDate()).padStart(2, '0');
        const todayStr = `${y}-${m}-${d}`;
        
        const todayTasks = tasks.filter(t => t.date === todayStr);
        const upcomingTasks = tasks.filter(t => t.date > todayStr).sort((a,b) => a.date.localeCompare(b.date)).slice(0, 5);
        
        const todayList = document.getElementById('sidebar-today-list');
        todayList.innerHTML = '';
        if(todayTasks.length === 0) {
            todayList.innerHTML = '<li class="empty-list">No tasks for today</li>';
        } else {
            todayTasks.forEach(t => {
                const checked = t.status === 'Completed' ? 'checked' : '';
                todayList.innerHTML += `
                    <li class="sidebar-task-item" style="border-left-color: ${t.color}" onclick="document.querySelector('.fc-event').click()"><!-- Note: simplified click handler via full refetch approach could act globally --> 
                        <div class="task-info">
                            <strong>${t.title}</strong>
                            ${t.start_time ? `<span class="time-badge">${t.start_time}</span>` : ''}
                        </div>
                        ${checked ? '<span class="status-icon">✓</span>' : ''}
                    </li>`;
            });
        }
        
        const upcomingList = document.getElementById('sidebar-upcoming-list');
        upcomingList.innerHTML = '';
        if(upcomingTasks.length === 0) {
            upcomingList.innerHTML = '<li class="empty-list">No upcoming tasks</li>';
        } else {
            upcomingTasks.forEach(t => {
                upcomingList.innerHTML += `
                    <li class="sidebar-task-item" style="border-left-color: ${t.color}">
                        <div class="task-info">
                            <strong>${t.title}</strong>
                            <small>${t.date}</small>
                        </div>
                    </li>`;
            });
        }
    }
});
