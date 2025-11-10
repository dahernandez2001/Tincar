/**
 * Sistema de Calificación para Tincar
 * Maneja la creación de modales de rating y envío de calificaciones
 */

/**
 * Abre el modal de calificación
 * @param {number} reservationId - ID de la reserva
 * @param {number} targetUserId - ID del usuario a calificar
 * @param {string} targetUserName - Nombre del usuario a calificar
 * @param {string} userType - 'driver' o 'landlord'
 */
function openRatingModal(reservationId, targetUserId, targetUserName, userType) {
    // Validar parámetros
    console.log('🎯 Abriendo modal de calificación:', {
        reservationId,
        targetUserId,
        targetUserName,
        userType
    });
    
    if (!reservationId || reservationId === 0) {
        alert('Error: ID de reserva inválido');
        console.error('❌ reservationId inválido:', reservationId);
        return;
    }
    
    if (!targetUserId || targetUserId === 0) {
        alert('Error: ID de usuario inválido');
        console.error('❌ targetUserId inválido:', targetUserId);
        return;
    }
    
    // Crear el modal dinámicamente
    const modalHTML = `
        <div id="ratingModal" class="modal-overlay open" style="z-index: 10002;">
            <div class="modal-card rating-modal" style="max-width: 400px;">
                <button class="modal-close" onclick="closeRatingModal()">×</button>
                <div class="modal-header text-center">
                    <h5 class="text-warning mb-0">Califica tu experiencia</h5>
                </div>
                <div class="modal-body text-center py-4">
                    <p class="mb-3 text-light">¿Cómo fue tu experiencia con <strong>${targetUserName}</strong>?</p>
                    
                    <div class="rating-stars mb-4" id="ratingStars">
                        ${[1, 2, 3, 4, 5].map(star => `
                            <span class="star" data-rating="${star}" onclick="selectRating(${star})">
                                <i class="fas fa-star"></i>
                            </span>
                        `).join('')}
                    </div>
                    
                    <textarea 
                        id="ratingComment" 
                        class="form-control mb-3" 
                        rows="3" 
                        placeholder="Comentario opcional..."
                        style="background: #1A1919; border: 1px solid #FFB300; color: #FFEFCA;"
                    ></textarea>
                    
                    <button 
                        id="submitRatingBtn" 
                        class="btn btn-orange w-100" 
                        onclick="submitRating(${reservationId}, ${targetUserId}, '${userType}')"
                        disabled
                    >
                        Enviar Calificación
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Insertar el modal en el body
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Almacenar el rating seleccionado globalmente
    window.selectedRating = 0;
}

/**
 * Selecciona una calificación (1-5 estrellas)
 */
function selectRating(rating) {
    window.selectedRating = rating;
    
    // Actualizar visualmente las estrellas
    const stars = document.querySelectorAll('#ratingStars .star');
    stars.forEach((star, index) => {
        if (index < rating) {
            star.classList.add('selected');
        } else {
            star.classList.remove('selected');
        }
    });
    
    // Habilitar el botón de enviar
    document.getElementById('submitRatingBtn').disabled = false;
}

/**
 * Envía la calificación al servidor
 */
function submitRating(reservationId, targetUserId, userType) {
    const rating = window.selectedRating;
    const comment = document.getElementById('ratingComment').value.trim();
    
    if (rating === 0) {
        alert('Por favor selecciona una calificación');
        return;
    }
    
    console.log('📤 Enviando calificación:', {
        reservation_id: reservationId,
        target_user_id: targetUserId,
        rating: rating,
        comment: comment,
        userType: userType
    });
    
    // Deshabilitar botón para evitar doble envío
    const btn = document.getElementById('submitRatingBtn');
    btn.disabled = true;
    btn.textContent = 'Enviando...';
    
    const payload = {
        reservation_id: reservationId,
        target_user_id: targetUserId,
        rating: rating,
        comment: comment
    };
    
    fetch('/api/reviews/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('¡Gracias por tu calificación!');
            closeRatingModal();
            // Recargar notificaciones para eliminar la notificación de calificación
            if (typeof loadNotifications === 'function') {
                loadNotifications();
            }
        } else {
            alert('Error: ' + (data.error || 'No se pudo enviar la calificación'));
            btn.disabled = false;
            btn.textContent = 'Enviar Calificación';
        }
    })
    .catch(error => {
        console.error('Error enviando calificación:', error);
        alert('Error de conexión. Intenta de nuevo.');
        btn.disabled = false;
        btn.textContent = 'Enviar Calificación';
    });
}

/**
 * Cierra el modal de calificación
 */
function closeRatingModal() {
    const modal = document.getElementById('ratingModal');
    if (modal) {
        modal.remove();
    }
    window.selectedRating = 0;
}
