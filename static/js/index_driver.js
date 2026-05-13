// Control del menú lateral de cuenta y lógica de conductor (extraído de template)
document.addEventListener('DOMContentLoaded', () => {
  const openBtn = document.getElementById('openAccountMenu');
  const closeBtn = document.getElementById('closeAccountMenu');
  const sideMenu = document.getElementById('accountSideMenu');
  const overlay = document.getElementById('accountMenuOverlay');
  const notificationCone = document.getElementById('notificationIcon');

  function openAccountMenu() {
    sideMenu.classList.add('active');
    overlay.classList.add('active');
    notificationCone.classList.add('menu-active');
  }

  function closeAccountMenu() {
    sideMenu.classList.remove('active');
    overlay.classList.remove('active');
    notificationCone.classList.remove('menu-active');
  }

  if (openBtn) openBtn.addEventListener('click', openAccountMenu);
  if (closeBtn) closeBtn.addEventListener('click', closeAccountMenu);
  if (overlay) overlay.addEventListener('click', closeAccountMenu);
  
  // Configurar botón de selección de vehículo
  const selectVehicleBtn = document.getElementById('selectVehicleBtn');
  console.log('=== Botón de vehículo encontrado:', selectVehicleBtn);
  
  if (selectVehicleBtn) {
    selectVehicleBtn.addEventListener('click', function() {
      console.log('=== CLICK EN BOTÓN DETECTADO ===');
      openVehicleModal();
    });
  } else {
    console.error('Botón selectVehicleBtn no encontrado');
  }
});

// Abrir modal de vehículos
function openVehicleModal() {
  console.log('=== Abriendo modal de vehículos ===');
  const modal = document.getElementById('vehicleSelectionModal');
  if (modal) {
    modal.classList.add('open');
    modal.style.display = 'flex';
    modal.setAttribute('aria-hidden', 'false');
    console.log('Modal abierto, clases:', modal.className);
    loadUserVehicles();
  } else {
    console.error('ERROR: Modal no encontrado');
    alert('Error: No se pudo abrir el modal');
  }
}

// Cerrar modal de vehículos
function closeVehicleModal() {
  console.log('=== Cerrando modal de vehículos ===');
  const modal = document.getElementById('vehicleSelectionModal');
  if (modal) {
    modal.classList.remove('open');
    modal.style.display = 'none';
    modal.setAttribute('aria-hidden', 'true');
    console.log('Modal cerrado');
  }
}

// Cerrar modal al hacer clic en el overlay
document.addEventListener('DOMContentLoaded', function() {
  const modal = document.getElementById('vehicleSelectionModal');
  if (modal) {
    modal.addEventListener('click', function(event) {
      if (event.target === modal) {
        closeVehicleModal();
      }
    });
  }
});

// Cargar vehículos del usuario
function loadUserVehicles() {
  console.log('Cargando vehículos del usuario...');
  const vehiclesList = document.getElementById('vehiclesList');
  
  if (!vehiclesList) {
    console.error('Elemento vehiclesList no encontrado');
    return;
  }
  
  vehiclesList.innerHTML = '<div class="text-center text-secondary py-4"><p>Cargando vehículos...</p></div>';
  
  fetch('/api/driver/vehicles')
    .then(response => {
      console.log('Respuesta recibida:', response.status);
      return response.json();
    })
    .then(data => {
      console.log('Datos recibidos:', data);
      
      if (data.error) {
        vehiclesList.innerHTML = `<div class="text-center text-danger py-4"><p>${data.error}</p></div>`;
        return;
      }
      
      if (!data.vehicles || data.vehicles.length === 0) {
        vehiclesList.innerHTML = `
          <div class="text-center text-light py-4">
            <p class="mb-3">No tienes vehículos registrados</p>
            <a href="/driver/profile" class="btn btn-orange">Agregar vehículo</a>
          </div>
        `;
        return;
      }
      
      const currentVehicle = data.current_vehicle;
      let html = '';
      
      data.vehicles.forEach(vehicle => {
        const isSelected = currentVehicle && currentVehicle.plate === vehicle.plate;
        html += `
          <div class="vehicle-card ${isSelected ? 'selected' : ''}" onclick="selectVehicle('${vehicle.plate}')">
            <div class="vehicle-info">
              <div class="d-flex justify-content-between align-items-start">
                <div style="flex: 1;">
                  <h5 class="mb-2" style="color: #FFB300; font-weight: 600;">${vehicle.brand || 'N/A'} ${vehicle.model || ''}</h5>
                  <p class="mb-1 text-light"><strong>Placa:</strong> ${vehicle.plate}</p>
                  <p class="mb-1" style="color: #939393;">${vehicle.color || 'N/A'} • ${vehicle.year || 'N/A'}</p>
                  ${vehicle.dimensions ? `<p class="mb-0" style="color: #939393; font-size: 0.9em;">📐 ${vehicle.dimensions}</p>` : ''}
                </div>
                ${isSelected ? '<div class="selected-badge"><i class="fas fa-check-circle"></i> En uso</div>' : ''}
              </div>
            </div>
          </div>
        `;
      });
      
      vehiclesList.innerHTML = html;
    })
    .catch(error => {
      console.error('Error al cargar vehículos:', error);
      vehiclesList.innerHTML = '<div class="text-center text-danger py-4"><p>Error al cargar los vehículos</p></div>';
    });
}

// Seleccionar vehículo
function selectVehicle(plate) {
  console.log('Seleccionando vehículo:', plate);
  
  fetch('/api/driver/select-vehicle', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ plate: plate })
  })
  .then(response => response.json())
  .then(data => {
    console.log('Respuesta de selección:', data);
    
    if (data.success) {
      // Recargar la lista de vehículos para actualizar el estado
      loadUserVehicles();
      // Mostrar mensaje de éxito
      setTimeout(() => {
        alert(`Vehículo ${plate} seleccionado correctamente ✓`);
      }, 300);
    } else {
      alert('Error al seleccionar el vehículo: ' + (data.error || 'desconocido'));
    }
  })
  .catch(error => {
    console.error('Error al seleccionar vehículo:', error);
    alert('Error al seleccionar el vehículo');
  });
}

// Animación de burbuja en navegación
document.addEventListener('DOMContentLoaded', () => {
  const nav = document.querySelector('.nav');
  if (nav) {
    const bubble = document.querySelector('.nav-bubble');
    const links = nav.querySelectorAll('a.nav-link');
    
    links.forEach(link => {
      link.addEventListener('mouseenter', () => {
        const rect = link.getBoundingClientRect();
        const navRect = nav.getBoundingClientRect();
        
        bubble.style.left = (rect.left - navRect.left) + 'px';
        bubble.style.width = rect.width + 'px';
        bubble.style.height = rect.height + 'px';
      });
    });
    
    nav.addEventListener('mouseleave', () => {
      bubble.style.width = '0';
    });
  }
});

// ... (rest of notification functions and modal handling) — extracted in full
