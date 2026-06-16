(function(){
  function isMobile(){
    return window.innerWidth < 768;
  }

  function renderMobile(container, tasks){
    container.innerHTML = '';
    tasks.forEach(t => {
      const row = document.createElement('div');
      row.style.padding = '0.75rem';
      row.style.marginBottom = '0.5rem';
      row.style.border = '1px solid #1f2937';
      row.style.borderRadius = '0.75rem';
      row.style.background = '#0f172a';
      row.style.display = 'flex';
      row.style.justifyContent = 'space-between';
      row.style.alignItems = 'center';

      const label = document.createElement('div');
      label.textContent = t.label;
      row.appendChild(label);

      const btn = document.createElement('button');
      btn.className = 'btn btn-outline';
      btn.textContent = t.completed ? '✓' : '○';
      btn.addEventListener('click', () => toggleTask(t.id));
      row.appendChild(btn);

      container.appendChild(row);
    });
  }

  function renderDesktop(container, tasks){
    container.innerHTML = 
      <table style="width:100%;font-size:0.85rem;border-collapse:collapse;">
        <thead>
          <tr style="border-bottom:1px solid #1f2937;">
            <th style="text-align:left;padding:0.5rem;">Task</th>
            <th style="text-align:left;padding:0.5rem;">Completed</th>
            <th style="text-align:left;padding:0.5rem;">User</th>
            <th style="text-align:left;padding:0.5rem;">Timestamp</th>
          </tr>
        </thead>
        <tbody id="task-body"></tbody>
      </table>
    ;

    const body = container.querySelector('#task-body');

    tasks.forEach(t => {
      const tr = document.createElement('tr');
      tr.innerHTML = 
        <td style="padding:0.5rem;"></td>
        <td style="padding:0.5rem;">
          <button class="btn btn-outline" onclick="toggleTask()"></button>
        </td>
        <td style="padding:0.5rem;"></td>
        <td style="padding:0.5rem;"></td>
      ;
      body.appendChild(tr);
    });
  }

  function toggleTask(id){
    console.log('Toggle task', id);
    // Backend wiring goes here later
  }

  document.addEventListener('DOMContentLoaded', function(){
    const container = document.getElementById('checklist-container');
    if(!container) return;

    const tasks = JSON.parse(container.dataset.tasks || '[]');

    if(isMobile()) renderMobile(container, tasks);
    else renderDesktop(container, tasks);
  });
})();
