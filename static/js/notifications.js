/**
 * Sistema centralizado de manejo de notificaciones para Tincar
 * Funciona en todos los perfiles (conductor, arrendador, dashboard general)
 */

// Variable global para almacenar notificaciones
window.notifications = window.notifications || [];

/**
 * Actualiza el contador de notificaciones no leídas en el badge del cono
 */
function updateNotificationCount() {
  const unreadCount = window.notifications.filter(n => n.status === 'unread').length;
  const countBadge = document.getElementById('notificationCount');
  if (countBadge) {
    countBadge.textContent = unreadCount;
    countBadge.style.display = unreadCount > 0 ? 'block' : 'none';
  }
}

/**
 * Carga las notificaciones desde el servidor
 */
function loadNotifications() {
  fetch('/api/notifications')
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        window.notifications = data.notifications || [];
        updateNotificationCount();
        console.log(`Notificaciones cargadas: ${window.notifications.length} total, ${window.notifications.filter(n => n.status === 'unread').length} no leídas`);
        
        // Si el modal está abierto, re-renderizar las notificaciones
        const modal = document.getElementById('notificationsModal');
        if (modal && modal.classList.contains('open')) {
          renderNotifications();
        }
      } else {
        console.error('Error cargando notificaciones:', data.error);
      }
    })
    .catch(error => {
      console.error('Error al cargar notificaciones:', error);
    });
}

/**
 * Abre el modal de notificaciones
 */
function openNotificationsModal() {
  const modal = document.getElementById('notificationsModal');
  if (modal) {
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    renderNotifications();
    // Marcar todas las no leídas como leídas
    markAllNotificationsAsRead();
  }
}

/**
 * Cierra el modal de notificaciones
 */
function closeNotificationsModal() {
  const modal = document.getElementById('notificationsModal');
  if (modal) {
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
  }
}

/**
 * Renderiza las notificaciones en el modal
 */
function renderNotifications() {
  const notificationsList = document.getElementById('notificationsList');
  if (!notificationsList) return;

  if (window.notifications.length === 0) {
    notificationsList.innerHTML = '<div class="text-center text-muted py-4">Buzón vacío</div>';
    return;
  }

  // Determinar el perfil del usuario (driver o landlord)
  const userProfile = window.userProfile || 'driver';
  console.log('=== RENDERIZANDO NOTIFICACIONES ===');
  console.log('Perfil de usuario:', userProfile);
  console.log('Total notificaciones:', window.notifications.length);
  
  // Notificaciones exclusivas de cada perfil
  const driverNotifications = ['driver_reservation_created', 'vehicle_parked', 'extra_time_approved', 'extra_time_rejected', 'eta_expired'];
  const landlordNotifications = ['new_reservation', 'reservation_expired', 'driver_arrived', 'at_vehicle', 'extra_time_request'];
  const sharedNotifications = ['reservation_completed', 'reservation_cancelled', 'verification_approved', 'verification_rejected'];

  let html = '';
  window.notifications.forEach(notification => {
    const notifType = notification.type;
    
    console.log('Procesando notificación:', {
      type: notifType,
      id: notification.id,
      userProfile: userProfile
    });
    
    // Filtrar notificaciones según el perfil
    if (userProfile === 'driver' && landlordNotifications.includes(notifType)) {
      console.log('Notificación filtrada (es del arrendador):', notifType);
      return; // No mostrar notificaciones del arrendador al conductor
    }
    if (userProfile === 'landlord' && driverNotifications.includes(notifType)) {
      console.log('Notificación filtrada (es del conductor):', notifType);
      return; // No mostrar notificaciones del conductor al arrendador
    }
    
    const unreadClass = notification.status === 'unread' ? 'unread' : '';
    let extraData = {};
    try {
      extraData = JSON.parse(notification.extra_data || '{}');
    } catch(e) {
      console.error('Error parsing extra_data:', e);
    }
    
    const resId = notification.reservation_id || extraData.reservation_id || 0;
    
    // ==================== INTERFAZ 1: PENDIENTE DE RESERVA ====================
    // CONDUCTOR: Esperando llegada al parqueadero
    if (notification.type === 'driver_reservation_created') {
      const parkingName = extraData.parking_name || 'el garaje';
      const ownerName = extraData.owner_name || 'el propietario';
      const etaMinutes = extraData.eta_minutes || notification.eta || 0;
      
      html += `
        <div class="notification-item notification-driver interface-primera ${unreadClass}" data-id="${notification.id}">
          <div class="notification-header-driver">⏱ RESERVA CONFIRMADA</div>
          <p>Hiciste reserva en garaje <strong>${parkingName}</strong> de <strong>${ownerName}</strong>. Llegar antes de <strong>${etaMinutes} minutos</strong>.</p>
          <hr>
          <button class="btn btn-success me-2" onclick="markDriverArrived(${resId})">Ya llegué</button>
          <button class="btn btn-outline-light" onclick="cancelDriverReservation(${resId})">Cancelar</button>
        </div>
      `;
    }
    
    // ARRENDADOR: Nueva reserva creada
    else if (notification.type === 'new_reservation') {
      const parkingName = extraData.parking_name || 'el garaje';
      const driverName = extraData.driver_name || 'un conductor';
      const driverId = extraData.driver_id || 0;
      const etaMinutes = notification.eta || 0;
      
      html += `
        <div class="notification-item interface-primera ${unreadClass}" data-id="${notification.id}">
          <div class="interface-header">INTERFAZ 1 - NUEVA RESERVA</div>
          <p><strong>${driverName}</strong> reservó tu garaje <strong>${parkingName}</strong>, llegará en <strong>${etaMinutes} min</strong>.</p>
          <hr>
          <button class="btn btn-orange me-2" onclick="showDriverInfo(${driverId})">Ver conductor</button>
          <button class="btn btn-outline-light" onclick="cancelReservation(${resId})">Cancelar</button>
        </div>
      `;
    }
    
    else if (notification.type === 'reservation_expired') {
      const driverId = extraData.driver_id || 0;
      html += `
        <div class="notification-item interface-primera ${unreadClass}" data-id="${notification.id}">
          <div class="interface-header interface-header-warning">NO LLEGÓ A TIEMPO</div>
          <p>El conductor no llegó al garaje en el tiempo estimado.</p>
          <hr>
          <button class="btn btn-orange me-2" onclick="showDriverInfo(${driverId})">Ver conductor</button>
          <button class="btn btn-outline-light" onclick="cancelReservation(${resId})">Cancelar</button>
        </div>
      `;
    }
    
    // ==================== INTERFAZ 2: RESERVA ACTIVA ====================
    // ARRENDADOR notif 1: Conductor llegó, vehículo guardado
    else if (notification.type === 'driver_arrived') {
      const driverName = extraData.driver_name || 'El conductor';
      const parkingName = extraData.parking_name || 'tu garaje';
      const driverId = extraData.driver_id || 0;
      const durationMinutes = extraData.duration_minutes || notification.duration_minutes || 0;
      const occupiedSince = extraData.occupied_since || notification.occupied_since || '';
      
      html += `
        <div class="notification-item interface-segunda ${unreadClass}" data-id="${notification.id}">
          <div class="interface-header">INTERFAZ 2 - VEHÍCULO GUARDADO</div>
          <p><strong>${driverName}</strong> está en <strong>${parkingName}</strong>, volverá en: <span id="timer-${resId}" class="time-remaining" data-duration="${durationMinutes}" data-occupied="${occupiedSince}">--:--:--</span></p>
          <hr>
          <button class="btn btn-orange" onclick="showDriverInfo(${driverId})">Ver conductor</button>
        </div>
      `;
      // Iniciar contador de tiempo
      setTimeout(() => startReservationTimer(occupiedSince, durationMinutes, `timer-${resId}`), 100);
    }
    
    // ARRENDADOR notif 2: Confirmar si conductor llegó a su vehículo
    else if (notification.type === 'at_vehicle') {
      html += `
        <div class="notification-item interface-segunda at-vehicle-confirmation ${unreadClass}" data-id="${notification.id}">
          <div class="interface-header">INTERFAZ 2 - CONFIRMACIÓN</div>
          <p>¿El conductor está en su vehículo?</p>
          <hr>
          <button class="btn btn-success me-2" onclick="confirmVehicleArrival(${resId})">Si llegó</button>
          <button class="btn btn-outline-light" onclick="vehicleNotArrived(${resId})">No llegó</button>
        </div>
      `;
    }
    
    // CONDUCTOR notif 1: Vehículo guardado, mostrar tiempo
    else if (notification.type === 'vehicle_parked') {
      const ownerName = extraData.owner_name || 'el arrendador';
      const ownerId = extraData.owner_id || 0;
      const durationMinutes = extraData.duration_minutes || notification.duration_minutes || 0;
      const occupiedSince = extraData.occupied_since || notification.occupied_since || '';
      const ownerNameEscaped = ownerName.replace(/'/g, "\\'");
      
      html += `
        <div class="notification-item notification-driver interface-segunda ${unreadClass}" data-id="${notification.id}">
          <div class="notification-header-driver notification-header-active">VEHÍCULO GUARDADO</div>
          <p>Tu vehículo guardado en garaje de <strong>${ownerName}</strong>. Tiempo: <span id="timer-driver-${resId}" class="time-remaining" data-duration="${durationMinutes}" data-occupied="${occupiedSince}">--:--:--</span></p>
          <hr>
          <button class="btn btn-warning me-2" onclick="openLandlordContactMenu(${ownerId}, '${ownerNameEscaped}')">Contacto</button>
          <button class="btn btn-success" onclick="notifyVehicleArrival(${resId})">Llegué a mi vehículo</button>
        </div>
      `;
      // Iniciar contador de tiempo
      setTimeout(() => startReservationTimer(occupiedSince, durationMinutes, `timer-driver-${resId}`), 100);
    }
    
    // CONDUCTOR: Tiempo extra aprobado/rechazado
    else if (notification.type === 'extra_time_approved' || notification.type === 'extra_time_rejected') {
      const isApproved = notification.type === 'extra_time_approved';
      const headerClass = isApproved ? 'notification-header-active' : 'notification-header-warning';
      html += `
        <div class="notification-item notification-driver interface-segunda ${unreadClass}" data-id="${notification.id}">
          <div class="notification-header-driver ${headerClass}">
            ${isApproved ? '✓ TIEMPO EXTRA APROBADO' : '⚠ TIEMPO EXTRA RECHAZADO'}
          </div>
          <p>${notification.message}</p>
        </div>
      `;
    }
    
    // CONDUCTOR: ETA expirado
    else if (notification.type === 'eta_expired') {
      html += `
        <div class="notification-item notification-driver interface-primera ${unreadClass}" data-id="${notification.id}">
          <div class="notification-header-driver notification-header-warning">⚠ TIEMPO DE LLEGADA EXPIRADO</div>
          <p>${notification.message || 'El tiempo estimado de llegada ha expirado.'}</p>
          <hr>
          <button class="btn btn-outline-light" onclick="cancelDriverReservation(${resId})">Cancelar reserva</button>
        </div>
      `;
    }
    
    // ARRENDADOR: Solicitud de tiempo extra
    else if (notification.type === 'extra_time_request') {
      const extraMin = extraData.extra_minutes || 0;
      html += `
        <div class="notification-item interface-segunda ${unreadClass}" data-id="${notification.id}">
          <div class="interface-header">SOLICITUD TIEMPO EXTRA</div>
          <p>El conductor quiere agregar <strong>${extraMin} minutos</strong> de reserva.</p>
          <hr>
          <button class="btn btn-danger me-2" onclick="rejectExtraTime(${resId}, ${notification.id})">Rechazar</button>
          <button class="btn btn-success" onclick="approveExtraTime(${resId}, ${extraMin}, ${notification.id})">Aceptar</button>
        </div>
      `;
    }
    
    // ==================== INTERFAZ 3: FINALIZACIÓN ====================
    // ARRENDADOR: Reserva completada
    else if (notification.type === 'reservation_completed' && userProfile === 'landlord') {
      const driverName = extraData.driver_name || 'El conductor';
      const totalAmount = extraData.amount || 0;
      const driverId = extraData.driver_id || 0;
      const driverNameEscaped = driverName.replace(/'/g, "\\'");
      
      console.log('INTERFAZ 3 ARRENDADOR:', {
        driverName,
        totalAmount,
        driverId
      });
      
      html += `
        <div class="notification-item interface-tercera ${unreadClass}" data-id="${notification.id}">
          <div class="interface-header interface-header-success">✓ RESERVA FINALIZADA</div>
          <p class="mb-2">Reserva de <strong>${driverName}</strong> finalizada exitosamente.</p>
          <p class="total-amount mb-3">Total cobrado: $${totalAmount.toLocaleString('es-CO')}</p>
          <hr>
          <button class="btn btn-warning" onclick="openRatingModal(${resId}, ${driverId}, '${driverNameEscaped}', 'driver')">
            <i class="fas fa-star"></i> Calificar conductor (1-5)
          </button>
          <p class="text-muted small mt-2 mb-0">Tu calificación ayuda a mejorar la comunidad</p>
        </div>
      `;
    }
    
    // CONDUCTOR: Reserva completada
    else if (notification.type === 'reservation_completed' && userProfile === 'driver') {
      const parkingName = extraData.parking_name || 'el garaje';
      const totalAmount = extraData.amount || 0;
      const ownerId = extraData.owner_id || 0;
      const ownerName = extraData.owner_name || 'el arrendador';
      const ownerNameEscaped = ownerName.replace(/'/g, "\\'");
      
      console.log('INTERFAZ 3 CONDUCTOR:', {
        parkingName,
        totalAmount,
        ownerId,
        ownerName
      });
      
      html += `
        <div class="notification-item notification-driver interface-tercera ${unreadClass}" data-id="${notification.id}">
          <div class="notification-header-driver notification-header-success">✓ RESERVA FINALIZADA</div>
          <p class="mb-2">Tu reserva en garaje <strong>${parkingName}</strong> finalizó exitosamente.</p>
          <p class="total-amount mb-3">Total pagado: $${totalAmount.toLocaleString('es-CO')}</p>
          <hr>
          <button class="btn btn-warning" onclick="openRatingModal(${resId}, ${ownerId}, '${ownerNameEscaped}', 'landlord')">
            <i class="fas fa-star"></i> Calificar arrendador (1-5)
          </button>
          <p class="text-muted small mt-2 mb-0">Tu calificación ayuda a mejorar la comunidad</p>
        </div>
      `;
    }
    
    // NOTIFICACIONES DE CANCELACIÓN (ambos perfiles)
    else if (notification.type === 'reservation_cancelled') {
      html += `
        <div class="notification-item ${unreadClass}" data-id="${notification.id}">
          <div class="notification-header">
            <strong>Reserva Cancelada</strong>
            <small class="text-muted">${formatDate(notification.created_at)}</small>
          </div>
          <p>${notification.message}</p>
        </div>
      `;
    }
    
    // NOTIFICACIONES GENÉRICAS (verificación de documentos, etc.)
    else if (notification.type === 'verification_approved' || notification.type === 'verification_rejected') {
      html += `
        <div class="notification-item ${unreadClass}" data-id="${notification.id}">
          <div class="notification-header">
            <strong>${notification.type === 'verification_approved' ? '✓ Verificación Aprobada' : '✗ Verificación Rechazada'}</strong>
            <small class="text-muted">${formatDate(notification.created_at)}</small>
          </div>
          <p>${notification.message}</p>
        </div>
      `;
    }
    
    // Si no coincide con ningún tipo específico, no renderizar (filtrar notificaciones incorrectas)
    else {
      console.log('Notificación filtrada (tipo no reconocido):', notification.type);
      return; // No agregar nada al HTML
    }
  });

  notificationsList.innerHTML = html;
}

/**
 * Formatea una fecha para mostrarla de forma legible
 */
function formatDate(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  
  if (diffMins < 1) return 'Ahora';
  if (diffMins < 60) return `Hace ${diffMins} min`;
  
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `Hace ${diffHours} h`;
  
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `Hace ${diffDays} días`;
  
  return date.toLocaleDateString('es-CO', { month: 'short', day: 'numeric' });
}

/**
 * Inicia un contador de tiempo en tiempo real para una reserva
 * @param {string} occupiedSince - Timestamp ISO cuando comenzó la reserva
 * @param {number} durationMinutes - Duración total de la reserva en minutos
 * @param {string} elementId - ID del elemento donde mostrar el contador
 */
function startReservationTimer(occupiedSince, durationMinutes, elementId) {
  const element = document.getElementById(elementId);
  if (!element) {
    console.error('Elemento contador no encontrado:', elementId);
    return;
  }
  
  function updateTimer() {
    try {
      const start = new Date(occupiedSince);
      const now = new Date();
      const elapsedMs = now - start;
      const elapsedMinutes = Math.floor(elapsedMs / 60000);
      const remainingMinutes = durationMinutes - elapsedMinutes;
      
      let hours, minutes, seconds;
      
      if (remainingMinutes > 0) {
        // Tiempo restante (positivo)
        const remainingSeconds = Math.max(0, Math.floor((durationMinutes * 60) - (elapsedMs / 1000)));
        hours = Math.floor(remainingSeconds / 3600);
        minutes = Math.floor((remainingSeconds % 3600) / 60);
        seconds = remainingSeconds % 60;
        element.style.color = '#FFB300'; // Dorado
      } else {
        // Tiempo de multa (negativo)
        const overtimeSeconds = Math.floor((elapsedMs / 1000) - (durationMinutes * 60));
        hours = Math.floor(overtimeSeconds / 3600);
        minutes = Math.floor((overtimeSeconds % 3600) / 60);
        seconds = overtimeSeconds % 60;
        element.style.color = '#E88E2E'; // Naranja/rojo
        element.textContent = `-${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        return; // Siguiente iteración
      }
      
      element.textContent = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    } catch (error) {
      console.error('Error actualizando timer:', error);
      element.textContent = '--:--:--';
    }
  }
  
  // Actualizar inmediatamente y luego cada segundo
  updateTimer();
  const intervalId = setInterval(updateTimer, 1000);
  
  // Guardar el intervalId en el elemento para poder detenerlo después
  element.dataset.intervalId = intervalId;
}

/**
 * Notifica que el conductor llegó a su vehículo (INTERFAZ 2 -> confirmación arrendador)
 */
function notifyVehicleArrival(reservationId) {
  if (!confirm('¿Confirmas que llegaste a tu vehículo?')) return;
  
  fetch(`/api/reservations/${reservationId}/at-vehicle`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      alert('El arrendador ha sido notificado de que llegaste a tu vehículo.');
      loadNotifications();
    } else {
      alert('Error: ' + (data.error || 'No se pudo enviar la notificación'));
    }
  })
  .catch(error => {
    console.error('Error notificando llegada al vehículo:', error);
    alert('Error de conexión. Intenta de nuevo.');
  });
}

/**
 * Marca todas las notificaciones como leídas
 */
function markAllNotificationsAsRead() {
  const unreadIds = window.notifications
    .filter(n => n.status === 'unread')
    .map(n => n.id);
  
  if (unreadIds.length === 0) return;

  fetch('/api/notifications/mark-read', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ notification_ids: unreadIds })
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      // Actualizar el estado local
      window.notifications.forEach(n => {
        if (unreadIds.includes(n.id)) {
          n.status = 'read';
        }
      });
      updateNotificationCount();
      renderNotifications();
    }
  })
  .catch(error => console.error('Error marcando notificaciones:', error));
}

/**
 * Limpia el buzón de notificaciones
 */
function clearNotificationsMailbox() {
  if (!confirm('¿Eliminar todas las notificaciones?')) return;

  fetch('/api/notifications/clear', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      window.notifications = [];
      updateNotificationCount();
      renderNotifications();
      console.log('Buzón de notificaciones limpiado');
    }
  })
  .catch(error => console.error('Error limpiando notificaciones:', error));
}

/**
 * Marca que el conductor ya llegó al parqueadero
 */
function markDriverArrived(reservationId) {
  if (!confirm('¿Confirmas que ya llegaste al parqueadero?')) return;
  
  fetch(`/api/reservations/${reservationId}/arrived`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      alert('¡Perfecto! El arrendador ha sido notificado de tu llegada.');
      loadNotifications();
      closeNotificationsModal();
    } else {
      alert('Error: ' + (data.error || 'No se pudo registrar tu llegada'));
    }
  })
  .catch(error => {
    console.error('Error marcando llegada:', error);
    alert('Error de conexión. Intenta de nuevo.');
  });
}

/**
 * Cancela la reserva del conductor
 */
function cancelDriverReservation(reservationId) {
  if (!confirm('¿Estás seguro de que quieres cancelar esta reserva?')) return;
  
  fetch(`/api/reservations/${reservationId}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      alert('Reserva cancelada correctamente.');
      loadNotifications();
      closeNotificationsModal();
    } else {
      alert('Error: ' + (data.error || 'No se pudo cancelar la reserva'));
    }
  })
  .catch(error => {
    console.error('Error cancelando reserva:', error);
    alert('Error de conexión. Intenta de nuevo.');
  });
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
  // Cargar notificaciones inicialmente
  loadNotifications();
  
  // Recargar notificaciones cada 5 segundos
  setInterval(loadNotifications, 5000);
  
  // Configurar el botón de cerrar modal
  const closeModalBtn = document.getElementById('closeModalBtn');
  if (closeModalBtn) {
    closeModalBtn.addEventListener('click', closeNotificationsModal);
  }
  
  // Cerrar modal al hacer clic fuera de él
  const modal = document.getElementById('notificationsModal');
  if (modal) {
    modal.addEventListener('click', function(e) {
      if (e.target === modal) {
        closeNotificationsModal();
      }
    });
  }
  
  console.log('Sistema de notificaciones inicializado');
});
