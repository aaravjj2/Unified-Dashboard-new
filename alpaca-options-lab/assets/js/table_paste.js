// DataTable Paste Functionality
// Enables pasting Excel/CSV data directly into the Market Trends DataTable

(function() {
  let pasteListenerAttached = false;

  function attachPasteListener() {
    if (pasteListenerAttached) return;

    const container = document.getElementById('results-table-client') 
                    || document.querySelector('.dash-table-container');
    
    if (!container) {
      console.debug('[Paste] DataTable not found yet, will retry...');
      return;
    }

    // Attach paste listener to the container
    container.addEventListener('paste', handlePaste);
    pasteListenerAttached = true;
    console.debug('[Paste] Paste listener attached to DataTable');
  }

  function handlePaste(e) {
    try {
      // Get clipboard data
      const clipboardData = e.clipboardData || window.clipboardData;
      if (!clipboardData) return;

      const pastedData = clipboardData.getData('text');
      if (!pastedData || !pastedData.trim()) return;

      console.debug('[Paste] Detected paste event, processing data...');
      
      // Parse the pasted data
      const parsedData = parseClipboardData(pastedData);
      
      if (parsedData && parsedData.length > 0) {
        e.preventDefault(); // Prevent default paste behavior
        
        // Show notification to user
        showPasteNotification(`Pasted ${parsedData.length} row(s) of data`);
        
        // Update the DataTable
        updateDataTable(parsedData);
      }
    } catch (error) {
      console.error('[Paste] Error handling paste:', error);
      showPasteNotification('Error processing pasted data', 'error');
    }
  }

  function parseClipboardData(text) {
    // Split by newlines
    const lines = text.split(/\r?\n/).filter(line => line.trim());
    if (lines.length === 0) return null;

    // Determine delimiter (tab for Excel, comma for CSV)
    const firstLine = lines[0];
    const delimiter = firstLine.includes('\t') ? '\t' : ',';
    
    const parsedRows = [];
    
    for (const line of lines) {
      // Split by delimiter and clean up
      const cells = line.split(delimiter).map(cell => cell.trim());
      
      // Skip empty rows
      if (cells.every(cell => !cell)) continue;
      
      parsedRows.push(cells);
    }
    
    return parsedRows;
  }

  function updateDataTable(parsedData) {
    try {
      // Get the DataTable component
      const tableElement = document.getElementById('results-table-client');
      if (!tableElement) {
        console.error('[Paste] DataTable element not found');
        return;
      }

      // Get current table data from Dash
      const dashTable = window.dash_clientside?.no_update;
      
      // For now, log the parsed data (Dash DataTable requires server-side update for data changes)
      console.debug('[Paste] Parsed data:', parsedData);
      console.debug('[Paste] Note: Full data update requires server-side callback implementation');
      
      // Display the data in a temporary overlay for user review
      showDataPreview(parsedData);
      
    } catch (error) {
      console.error('[Paste] Error updating DataTable:', error);
    }
  }

  function showDataPreview(data) {
    // Remove existing preview if any
    const existing = document.getElementById('paste-preview-overlay');
    if (existing) existing.remove();

    // Create overlay
    const overlay = document.createElement('div');
    overlay.id = 'paste-preview-overlay';
    overlay.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: white;
      border: 2px solid #2c3e50;
      border-radius: 8px;
      padding: 20px;
      max-width: 80%;
      max-height: 80%;
      overflow: auto;
      z-index: 10000;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    `;

    // Create preview content
    const title = document.createElement('h3');
    title.textContent = `Pasted Data Preview (${data.length} rows)`;
    title.style.cssText = 'margin: 0 0 15px 0; color: #2c3e50;';
    
    const table = document.createElement('table');
    table.style.cssText = 'border-collapse: collapse; width: 100%; margin-bottom: 15px;';
    
    // Create table rows
    data.slice(0, 10).forEach((row, idx) => {
      const tr = document.createElement('tr');
      row.forEach(cell => {
        const td = document.createElement('td');
        td.textContent = cell;
        td.style.cssText = 'border: 1px solid #ddd; padding: 8px; font-size: 13px;';
        tr.appendChild(td);
      });
      table.appendChild(tr);
    });
    
    if (data.length > 10) {
      const note = document.createElement('p');
      note.textContent = `... and ${data.length - 10} more rows`;
      note.style.cssText = 'color: #666; font-style: italic; margin: 10px 0;';
      overlay.appendChild(note);
    }

    const closeBtn = document.createElement('button');
    closeBtn.textContent = 'Close';
    closeBtn.style.cssText = `
      padding: 8px 20px;
      background: #2c3e50;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
    `;
    closeBtn.onclick = () => overlay.remove();

    overlay.appendChild(title);
    overlay.appendChild(table);
    overlay.appendChild(closeBtn);
    document.body.appendChild(overlay);
  }

  function showPasteNotification(message, type = 'success') {
    // Create notification element
    const notification = document.createElement('div');
    notification.textContent = message;
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      padding: 12px 20px;
      background: ${type === 'error' ? '#e74c3c' : '#27ae60'};
      color: white;
      border-radius: 4px;
      z-index: 10001;
      font-size: 14px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.2);
      animation: slideIn 0.3s ease-out;
    `;

    // Add animation
    const style = document.createElement('style');
    style.textContent = `
      @keyframes slideIn {
        from { transform: translateX(400px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
    `;
    document.head.appendChild(style);

    document.body.appendChild(notification);

    // Auto-remove after 3 seconds
    setTimeout(() => {
      notification.style.animation = 'slideIn 0.3s ease-out reverse';
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }

  // Try to attach listener immediately
  attachPasteListener();

  // Also try after DOM loads
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      setTimeout(attachPasteListener, 500);
    });
  } else {
    setTimeout(attachPasteListener, 500);
  }

  // Retry every 2 seconds if not attached (handles dynamic table loading)
  const retryInterval = setInterval(() => {
    if (!pasteListenerAttached) {
      attachPasteListener();
    } else {
      clearInterval(retryInterval);
    }
  }, 2000);

  console.debug('[Paste] DataTable paste module loaded');
})();
